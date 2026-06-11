"""
FlowDroid taint analysis wrapper.

Runs FlowDroid on an APK and parses the output into structured
TaintFlow records for downstream consumption by the Cortex.
"""

import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from parallax.analysis.static.taint_sink_definitions import (
    TAINT_SOURCES,
    TAINT_SINKS,
    HIGH_RISK_SINKS,
    SINK_TO_ATTCK,
)

@dataclass
class TaintFlow:
    """A single data flow from a source to a sink."""
    source_class: str
    source_method: str
    sink_class: str
    sink_method: str
    path: list[str] = field(default_factory=list)  # Intermediate methods
    risk: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    attck_technique: str | None = None

    @property
    def sink_key(self) -> str:
        return f"{self.sink_class}.{self.sink_method}"

    @property
    def source_key(self) -> str:
        return f"{self.source_class}.{self.source_method}"

class FlowDroidError(Exception):
    """Raised when FlowDroid execution fails."""
    pass

class FlowDroidRunner:
    """Wrapper around the FlowDroid JAR for taint analysis."""

    def __init__(self, jar_path: str | Path, java_path: str = "java"):
        self.jar_path = Path(jar_path)
        if not self.jar_path.exists():
            raise FileNotFoundError(f"FlowDroid JAR not found: {jar_path}")
        self.java_path = java_path

    def run(
        self,
        apk_path: str | Path,
        sources: list[tuple[str, str]] | None = None,
        sinks: list[tuple[str, str]] | None = None,
        timeout: int = 300,
    ) -> list[TaintFlow]:
        """
        Run FlowDroid on the given APK.

        Args:
            apk_path: Path to the APK file.
            sources: Override default TAINT_SOURCES. List of (class, method) tuples.
            sinks: Override default TAINT_SINKS. List of (class, method) tuples.
            timeout: Max seconds to wait for FlowDroid.

        Returns:
            List of TaintFlow records.

        Raises:
            FlowDroidError: If FlowDroid exits non-zero or times out.
        """
        apk_path = Path(apk_path)
        if not apk_path.exists():
            raise FileNotFoundError(f"APK not found: {apk_path}")

        sources = sources or TAINT_SOURCES
        sinks = sinks or TAINT_SINKS

        # Build FlowDroid command
        # --apkfile: input APK
        # --output: output format (we use XML for parsing)
        # --sources/sinks: custom source/sink definitions
        # Note: FlowDroid's CLI accepts sources/sinks in a specific XML format
        with tempfile.TemporaryDirectory() as tmpdir:
            sources_sinks_file = Path(tmpdir) / "sourcesthreadsinks.txt"
            self._write_sources_sinks(sources_sinks_file, sources, sinks)

            output_xml = Path(tmpdir) / "flowdroid_output.xml"

            cmd = [
                self.java_path,
                "-jar",
                str(self.jar_path),
                "-a", str(apk_path),
                "-p", str(Path(tmpdir) / "platforms"),  # Android platform jars
                "-s", str(sources_sinks_file),
                "-o", str(output_xml),
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as e:
                raise FlowDroidError(f"FlowDroid timed out after {timeout}s") from e

            if result.returncode != 0 and not output_xml.exists():
                raise FlowDroidError(
                    f"FlowDroid failed (exit {result.returncode}):\n"
                    f"stdout: {result.stdout[:500]}\n"
                    f"stderr: {result.stderr[:500]}"
                )

            if not output_xml.exists():
                # FlowDroid ran but found no flows — return empty list
                return []

            return self._parse_xml_output(output_xml)

    def _write_sources_sinks(
        self,
        path: Path,
        sources: list[tuple[str, str]],
        sinks: list[tuple[str, str]],
    ) -> None:
        """
        Write FlowDroid's source/sink definition file.

        Format: One method per line, with category prefix.
        FlowDroid's "EasyTaintWrapperSource" format:
            <category> <class>-><method>(<params>)
        """
        lines = []
        for cls, method in sources:
            lines.append(f"Source: {cls}->{method}")
        for cls, method in sinks:
            lines.append(f"Sink: {cls}->{method}")
        path.write_text("\n".join(lines))

    def _parse_xml_output(self, xml_path: Path) -> list[TaintFlow]:
        """
        Parse FlowDroid's XML output into TaintFlow records.

        FlowDroid XML format (simplified):
        <Results>
          <Result Source="..." Sink="...">
            <Path>
              <Method Class="..." Method="..." />
              ...
            </Path>
          </Result>
        </Results>
        """
        flows = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError:
            return []

        for result in root.findall(".//Result"):
            source_attr = result.get("Source", "")
            sink_attr = result.get("Sink", "")

            # Parse "class.method" format
            source_class, _, source_method = source_attr.rpartition(".")
            sink_class, _, sink_method = sink_attr.rpartition(".")

            # Extract path
            path = []
            for method in result.findall(".//Path/Method"):
                cls = method.get("Class", "")
                m = method.get("Method", "")
                if cls and m:
                    path.append(f"{cls}.{m}")

            sink_key = f"{sink_class}.{sink_method}"
            risk = "CRITICAL" if sink_key in HIGH_RISK_SINKS else "MEDIUM"
            attck = SINK_TO_ATTCK.get(sink_key)

            flows.append(TaintFlow(
                source_class=source_class,
                source_method=source_method,
                sink_class=sink_class,
                sink_method=sink_method,
                path=path,
                risk=risk,
                attck_technique=attck,
            ))

        return flows
