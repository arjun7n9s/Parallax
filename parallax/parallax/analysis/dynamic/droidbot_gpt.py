"""
DroidBot-GPT UI Automation Loop.

Uses a vision-capable LLM to decide on actions (taps, swipes, text input, etc.)
based on the current UI state dump and screenshot, facilitating automated application exploration.
"""

import base64
import hashlib
import io
import json
import logging
import re
import time
import xml.etree.ElementTree as ET  # type: ignore # nosec B314
from typing import Any, Dict, List

from parallax.ai.llm import llm
from parallax.analysis.dynamic.avd_manager import AVDManager
from parallax.core.storage import SCREENSHOTS_BUCKET, get_minio_client

logger = logging.getLogger(__name__)


class DroidBotGPT:
    """
    Automated UI exploration loop for Android applications using a Vision-capable LLM.
    Dumps UI state, captures screen screenshots, queries LLM for actions, and executes them.
    """

    def __init__(self, avd_manager: AVDManager, package_name: str, session_id: str):
        self.avd_manager = avd_manager
        self.package_name = package_name
        self.session_id = session_id
        self.minio_client = get_minio_client()
        self.history: List[Dict[str, Any]] = []

    def ensure_unlocked(self) -> None:
        """Wake up the device and unlock the screen."""
        try:
            self.avd_manager.shell("input keyevent KEYCODE_WAKEUP")
            self.avd_manager.shell("input keyevent 82")  # Unlock keyevent
        except Exception as e:
            logger.warning(f"Failed to ensure device is unlocked: {e}")

    def dump_ui_state(self) -> List[Dict[str, Any]]:
        """Dump the current UI state using uiautomator and return a list of parsed elements."""
        self.ensure_unlocked()

        # Run uiautomator dump
        try:
            dump_res = self.avd_manager.shell("uiautomator dump /sdcard/window_dump.xml")
            if "dumped to" not in dump_res.lower() and "dump" not in dump_res.lower():
                # On some devices, uiautomator dump might write to stdout or fail.
                # Let's try /data/local/tmp as fallback.
                self.avd_manager.shell("uiautomator dump /data/local/tmp/window_dump.xml")
                xml_content = self.avd_manager.shell("cat /data/local/tmp/window_dump.xml")
            else:
                xml_content = self.avd_manager.shell("cat /sdcard/window_dump.xml")
        except Exception as e:
            logger.error(f"Failed to dump UI layout XML: {e}")
            return []

        if not xml_content or not xml_content.strip():
            logger.warning("Empty UI dump XML content.")
            return []

        return self.parse_ui_xml(xml_content)

    def parse_ui_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse UI hierarchy XML and extract clickable/visible/interactive nodes."""
        try:
            # Parse XML safely using standard library elementtree
            try:
                import defusedxml.ElementTree as DET

                root = DET.fromstring(xml_content.encode("utf-8"))
            except ImportError:
                root = ET.fromstring(xml_content.encode("utf-8"))  # nosec B314
        except Exception as e:
            logger.error(f"Failed to parse XML string: {e}")
            return []

        elements = []
        element_id = 0

        def traverse(node):
            nonlocal element_id
            attrib = node.attrib
            bounds_str = attrib.get("bounds", "")

            # Check if this node has bounds and is visible/interactive
            if bounds_str:
                text = attrib.get("text", "").strip()
                resource_id = attrib.get("resource-id", "").strip()
                class_name = attrib.get("class", "").strip()
                content_desc = attrib.get("content-desc", "").strip()
                clickable = attrib.get("clickable", "false").lower() == "true"
                scrollable = attrib.get("scrollable", "false").lower() == "true"
                focused = attrib.get("focused", "false").lower() == "true"
                enabled = attrib.get("enabled", "true").lower() == "true"

                # Check for other interactive properties
                long_clickable = attrib.get("long-clickable", "false").lower() == "true"
                checkable = attrib.get("checkable", "false").lower() == "true"
                checked = attrib.get("checked", "false").lower() == "true"
                password = attrib.get("password", "false").lower() == "true"

                # Parse bounds [x1,y1][x2,y2]
                pattern = r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]"
                match = re.match(pattern, bounds_str)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                else:
                    x1, y1, x2, y2 = 0, 0, 0, 0
                    center_x, center_y = 0, 0

                is_interactive = (
                    clickable
                    or long_clickable
                    or checkable
                    or scrollable
                    or "edit" in class_name.lower()
                )

                # Add to elements if it has readable text/desc, or is interactive
                if enabled and (is_interactive or text or content_desc):
                    elements.append(
                        {
                            "id": element_id,
                            "text": text,
                            "resource_id": resource_id,
                            "class": class_name,
                            "content_desc": content_desc,
                            "clickable": clickable,
                            "long_clickable": long_clickable,
                            "checkable": checkable,
                            "checked": checked,
                            "scrollable": scrollable,
                            "focused": focused,
                            "password": password,
                            "bounds": bounds_str,
                            "center": (center_x, center_y),
                        }
                    )
                    element_id += 1

            for child in node:
                traverse(child)

        traverse(root)
        return elements

    def take_screenshot(self) -> bytes:
        """Capture device screenshot as raw bytes (PNG)."""
        try:
            # Temporary file on device
            device_path = f"/data/local/tmp/screen_{self.session_id}_{int(time.time())}.png"
            self.avd_manager.shell(f"screencap -p {device_path}")

            # Read image data from device stdout or pull
            # Using base64 encoding to transfer binary safely over shell
            b64_data = self.avd_manager.shell(f"base64 {device_path}")
            # Clean temp file on device
            self.avd_manager.shell(f"rm -f {device_path}")

            if b64_data:
                # Remove any whitespace/newlines from base64
                b64_clean = "".join(b64_data.strip().split())
                return base64.b64decode(b64_clean)
        except Exception as e:
            logger.warning(f"Failed to capture screen via base64 shell fallback: {e}")

        # Basic fallback using host-side screenshot if available or run adb exec-out
        try:
            # Run adb exec-out screencap -p
            cmd = [
                self.avd_manager.adb_bin,
                "-s",
                self.avd_manager.device_id,
                "exec-out",
                "screencap",
                "-p",
            ]
            import subprocess

            res = subprocess.run(cmd, capture_output=True, check=True)  # nosec B603
            if res.stdout:
                return res.stdout
        except Exception as e:
            logger.error(f"Failed to capture screenshot via adb exec-out: {e}")

        return b"mock_png_bytes"

    async def select_action(
        self, elements: List[Dict[str, Any]], screenshot_bytes: bytes
    ) -> Dict[str, Any]:
        """Query LLM to decide on the next action based on UI state and screenshot."""
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Format elements list for LLM context
        simplified_elements = []
        for el in elements:
            simplified_elements.append(
                {
                    "id": el["id"],
                    "text": el["text"],
                    "resource_id": el["resource_id"],
                    "class": el["class"].split(".")[-1],  # Short class name
                    "content_desc": el["content_desc"],
                    "clickable": el["clickable"],
                    "bounds": el["bounds"],
                }
            )

        history_summary = []
        for idx, step in enumerate(self.history):
            history_summary.append(f"Step {idx + 1}: {step.get('action')}")

        prompt = f"""
You are DroidBot-GPT, an intelligent agent exploring an Android app to find malicious behaviors.
Current Package: {self.package_name}

Exploration History:
{chr(10).join(history_summary) if history_summary else "No history yet."}

Interactive UI Elements on screen:
{json.dumps(simplified_elements, indent=2)}

Analyze the layout and the screenshot to decide the next step.
Your objective is to find suspicious or fraudulent app behaviors (like requests for SMS interception, accessibility service permissions, inputting fields, keyloggers, etc.).

Choose the next action. You must respond with a JSON object following this format:
{{
  "action_type": "tap" | "swipe" | "text" | "keyevent" | "wait" | "done",
  "element_id": <int_id_from_elements_list_or_null>,
  "text": "<text_to_input_if_text_action_else_null>",
  "direction": "up" | "down" | "left" | "right" | null,
  "key_code": "<ADB_KEYCODE_name_or_null>",
  "reason": "<brief_reasoning_for_this_action>"
}}
"""
        system_prompt = "You are an automated malware analysis assistant. You analyze UI states and choose the next action to trigger potentially hidden malware components."

        try:
            logger.info("Querying LLM (dynamic_explorer role) for next UI action...")
            # Role "dynamic_explorer" → vision model (gemini-flash on the gateway,
            # llava locally) selected by the unified provider.
            response = await llm.complete_json(
                "dynamic_explorer",
                prompt,
                system=system_prompt,
                images=[screenshot_b64],
            )
            return response
        except Exception as e:
            logger.error(
                f"Failed to query LLM for action selection: {e}. Falling back to heuristic action."
            )

            # Simple heuristic fallback to not block execution
            clickable_elements = [el for el in elements if el["clickable"]]
            if clickable_elements:
                target = clickable_elements[0]
                return {
                    "action_type": "tap",
                    "element_id": target["id"],
                    "reason": "Fallback: first clickable element",
                }
            return {"action_type": "wait", "reason": "Fallback: no clickable elements found"}

    def execute_action(self, action: Dict[str, Any], elements: List[Dict[str, Any]]) -> str:
        """Execute the chosen action on the emulator via ADB."""
        action_type = action.get("action_type", "wait").lower()
        element_id = action.get("element_id")
        reason = action.get("reason", "No reason provided")

        target_el = None
        if element_id is not None:
            for el in elements:
                if el["id"] == element_id:
                    target_el = el
                    break

        action_summary = f"Action: {action_type} - Reason: {reason}"

        if action_type == "tap":
            if target_el:
                cx, cy = target_el["center"]
                logger.info(
                    f"Tapping element {element_id} at ({cx}, {cy}): {target_el.get('text') or target_el.get('resource_id')}"
                )
                self.avd_manager.shell(f"input tap {cx} {cy}")
                action_summary = f"Tap element {element_id} ({target_el.get('text') or target_el.get('resource_id')}) at ({cx},{cy})"
            else:
                logger.warning(f"Tap action requested but element {element_id} not found.")

        elif action_type == "text":
            text_val = action.get("text", "")
            if target_el:
                cx, cy = target_el["center"]
                logger.info(
                    f"Tapping element {element_id} to focus, then inputting text: {text_val}"
                )
                self.avd_manager.shell(f"input tap {cx} {cy}")
                time.sleep(0.5)
                # Escape space as %s for adb input
                escaped_text = text_val.replace(" ", "%s")
                self.avd_manager.shell(f"input text {escaped_text}")
                action_summary = f"Input text '{text_val}' into element {element_id}"
            else:
                logger.warning(f"Text action requested but element {element_id} not found.")

        elif action_type == "swipe":
            direction = action.get("direction", "up").lower()
            logger.info(f"Swiping screen in direction: {direction}")
            if direction == "up":
                self.avd_manager.shell("input swipe 500 1200 500 400 300")
            elif direction == "down":
                self.avd_manager.shell("input swipe 500 400 500 1200 300")
            elif direction == "left":
                self.avd_manager.shell("input swipe 800 800 200 800 300")
            elif direction == "right":
                self.avd_manager.shell("input swipe 200 800 800 800 300")
            action_summary = f"Swipe {direction}"

        elif action_type == "keyevent":
            key_code = action.get("key_code", "KEYCODE_BACK")
            logger.info(f"Sending keyevent: {key_code}")
            self.avd_manager.shell(f"input keyevent {key_code}")
            action_summary = f"Keyevent {key_code}"

        elif action_type == "wait":
            logger.info("Waiting for 3 seconds...")
            time.sleep(3.0)
            action_summary = "Wait"

        elif action_type == "done":
            logger.info("LLM indicated exploration is complete.")
            action_summary = "Exploration Complete (Done)"

        return action_summary

    async def run_exploration(self, max_turns: int = 30) -> None:
        """Run the DroidBot-GPT exploration loop."""
        logger.info(
            f"Starting DroidBot-GPT exploration for package: {self.package_name} (Max turns: {max_turns})"
        )

        # Launch the target app package
        try:
            logger.info(f"Launching application package: {self.package_name}")
            self.avd_manager.shell(
                f"monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1"
            )
            time.sleep(3.0)
        except Exception as e:
            logger.error(f"Failed to launch package: {e}")
            return

        consecutive_no_change = 0
        last_state_signature = ""

        for turn in range(max_turns):
            logger.info(f"=== Exploration Turn {turn + 1}/{max_turns} ===")

            # 1. Capture screen screenshot
            screenshot_bytes = self.take_screenshot()

            # Upload screenshot to MinIO
            screenshot_name = f"{self.session_id}/turn_{turn + 1:02d}.png"
            try:
                self.minio_client.put_object(
                    SCREENSHOTS_BUCKET,
                    screenshot_name,
                    data=io.BytesIO(screenshot_bytes),
                    length=len(screenshot_bytes),
                    content_type="image/png",
                )
                logger.info(f"Saved screenshot to MinIO: {screenshot_name}")
            except Exception as e:
                logger.error(f"Failed to upload screenshot to MinIO: {e}")

            # 2. Extract UI state elements
            elements = self.dump_ui_state()
            logger.info(f"Extracted {len(elements)} visible/interactive UI elements.")

            # Calculate screen state signature to detect if screen is stuck/unchanged
            state_signature = hashlib_md5_signature(elements)
            if state_signature == last_state_signature:
                consecutive_no_change += 1
                logger.info(f"UI state unchanged for {consecutive_no_change} consecutive turns.")
            else:
                consecutive_no_change = 0

            last_state_signature = state_signature

            # Stop if UI remained unchanged for 3 consecutive turns
            if consecutive_no_change >= 3:
                logger.info("Exploration stopped: UI remains unchanged for 3 consecutive turns.")
                break

            # 3. Query LLM for next action
            action = await self.select_action(elements, screenshot_bytes)
            logger.info(f"LLM Decision: {json.dumps(action)}")

            # 4. Execute action
            action_summary = self.execute_action(action, elements)

            # Record history
            self.history.append(
                {
                    "turn": turn + 1,
                    "action": action_summary,
                    "decision": action,
                    "screenshot_path": f"{SCREENSHOTS_BUCKET}/{screenshot_name}",
                }
            )

            if action.get("action_type", "").lower() == "done":
                logger.info("Exploration finished as requested by LLM.")
                break

            # Settle time
            time.sleep(1.5)

        logger.info(
            f"DroidBot-GPT exploration completed for {self.package_name}. Total turns: {len(self.history)}"
        )


def hashlib_md5_signature(elements: List[Dict[str, Any]]) -> str:
    """Helper to calculate a signature/hash for a list of UI elements to detect changes."""
    sig_str = ""
    for el in elements:
        sig_str += f"{el['id']}:{el['resource_id']}:{el['text']}:{el['bounds']}|"
    return hashlib.md5(sig_str.encode("utf-8")).hexdigest()  # nosec B324 B303
