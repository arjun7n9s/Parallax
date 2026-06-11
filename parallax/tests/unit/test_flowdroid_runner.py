"""
Unit tests for flowdroid_runner.

Tests:
- Constructor validates JAR path
- Source/sink file writer produces valid format
- XML parser correctly extracts TaintFlow records
- Risk classification is correct
- Missing APK raises FileNotFoundError
- Missing JAR raises FileNotFoundError
"""

import pytest

from parallax.analysis.static.flowdroid_runner import (
    FlowDroidRunner,
    TaintFlow,
)


class TestFlowDroidRunnerInit:
    def test_jar_path_must_exist(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="FlowDroid JAR not found"):
            FlowDroidRunner(jar_path=tmp_path / "nonexistent.jar")

    def test_valid_jar_path(self, tmp_path):
        jar = tmp_path / "fake.jar"
        jar.write_bytes(b"fake")
        runner = FlowDroidRunner(jar_path=jar)
        assert runner.jar_path == jar


class TestSourcesSinksWriter:
    def test_writes_sources_and_sinks(self, tmp_path):
        jar = tmp_path / "fake.jar"
        jar.write_bytes(b"fake")
        runner = FlowDroidRunner(jar_path=jar)

        ss_file = tmp_path / "sinks.txt"
        runner._write_sources_sinks(
            ss_file,
            sources=[("android.telephony.SmsMessage", "getMessageBody", "Read SMS body")],
            sinks=[("android.telephony.SmsManager", "sendTextMessage", "Send SMS")],
        )

        content = ss_file.read_text()
        assert "Source: android.telephony.SmsMessage->getMessageBody" in content
        assert "Sink: android.telephony.SmsManager->sendTextMessage" in content


class TestXmlParser:
    def _make_runner(self, tmp_path) -> FlowDroidRunner:
        jar = tmp_path / "fake.jar"
        jar.write_bytes(b"fake")
        return FlowDroidRunner(jar_path=jar)

    def test_parses_single_flow(self, tmp_path):
        runner = self._make_runner(tmp_path)
        xml_path = tmp_path / "out.xml"
        xml_path.write_text("""<?xml version="1.0"?>
<Results>
  <Result Source="android.telephony.SmsMessage.getMessageBody"
          Sink="android.telephony.SmsManager.sendTextMessage">
    <Path>
      <Method Class="com.bad.app.Stealer" Method="onReceive"/>
      <Method Class="com.bad.app.MainActivity" Method="doBad"/>
    </Path>
  </Result>
</Results>""")

        flows = runner._parse_xml_output(xml_path)

        assert len(flows) == 1
        f = flows[0]
        assert f.source_class == "android.telephony.SmsMessage"
        assert f.source_method == "getMessageBody"
        assert f.sink_class == "android.telephony.SmsManager"
        assert f.sink_method == "sendTextMessage"
        assert len(f.path) == 2
        assert f.risk == "CRITICAL"  # sendTextMessage is in HIGH_RISK_SINKS
        assert f.attck_technique == "T1485.001"

    def test_parses_multiple_flows(self, tmp_path):
        runner = self._make_runner(tmp_path)
        xml_path = tmp_path / "out.xml"
        xml_path.write_text("""<?xml version="1.0"?>
<Results>
  <Result Source="android.telephony.SmsMessage.getMessageBody" Sink="java.net.URL.openConnection">
    <Path><Method Class="com.bad.E" Method="x"/></Path>
  </Result>
  <Result Source="android.location.Location.getLatitude" Sink="java.net.HttpURLConnection.connect">
    <Path><Method Class="com.bad.E" Method="y"/></Path>
  </Result>
</Results>""")

        flows = runner._parse_xml_output(xml_path)
        assert len(flows) == 2

    def test_handles_empty_results(self, tmp_path):
        runner = self._make_runner(tmp_path)
        xml_path = tmp_path / "empty.xml"
        xml_path.write_text("""<?xml version="1.0"?>
<Results></Results>""")

        flows = runner._parse_xml_output(xml_path)
        assert flows == []

    def test_handles_malformed_xml(self, tmp_path):
        runner = self._make_runner(tmp_path)
        xml_path = tmp_path / "bad.xml"
        xml_path.write_text("not valid xml <<<")

        # Should not raise — just return empty list
        flows = runner._parse_xml_output(xml_path)
        assert flows == []

    def test_risk_classification(self, tmp_path):
        runner = self._make_runner(tmp_path)
        xml_path = tmp_path / "out.xml"
        xml_path.write_text("""<?xml version="1.0"?>
<Results>
  <Result Source="android.provider.ContactsContract.query" Sink="java.io.FileWriter.write">
    <Path/>
  </Result>
</Results>""")

        flows = runner._parse_xml_output(xml_path)
        assert flows[0].risk == "MEDIUM"  # FileWriter not in HIGH_RISK_SINKS

    def test_attck_mapping(self, tmp_path):
        runner = self._make_runner(tmp_path)
        xml_path = tmp_path / "out.xml"
        xml_path.write_text("""<?xml version="1.0"?>
<Results>
  <Result Source="android.telephony.SmsMessage.getMessageBody" Sink="okhttp3.OkHttpClient.newCall">
    <Path/>
  </Result>
</Results>""")

        flows = runner._parse_xml_output(xml_path)
        assert flows[0].attck_technique == "T1437.001"


class TestTaintFlow:
    def test_sink_key(self):
        f = TaintFlow(
            source_class="a.b.C",
            source_method="m1",
            sink_class="d.e.F",
            sink_method="m2",
        )
        assert f.sink_key == "d.e.F.m2"
        assert f.source_key == "a.b.C.m1"

    def test_default_risk_is_medium(self):
        f = TaintFlow(
            source_class="a",
            source_method="b",
            sink_class="c",
            sink_method="d",
        )
        assert f.risk == "MEDIUM"
        assert f.attck_technique is None
        assert f.path == []


class TestRun:
    def test_missing_apk_raises(self, tmp_path):
        jar = tmp_path / "fake.jar"
        jar.write_bytes(b"fake")
        runner = FlowDroidRunner(jar_path=jar)

        with pytest.raises(FileNotFoundError, match="APK not found"):
            runner.run(apk_path=tmp_path / "nonexistent.apk")
