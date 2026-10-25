"""
Multi-App Crawler Subagent (Subagent #15)
Inspired by DroidBot & ByteDance Fastbot model-based UI state-graph explorer.
Autonomously explores one or multiple Android applications, builds a UI state transition graph,
avoids destructive actions, optionally injects Fastbot/Monkey event bursts, and monitors for
FATAL EXCEPTION / ANR crashes.
"""

import hashlib
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


DESTRUCTIVE_KEYWORDS: Tuple[str, ...] = (
    "delete",
    "reset",
    "sign out",
    "log out",
    "logout",
    "power off",
    "factory reset",
    "erase",
    "uninstall",
    "clear data",
    "format",
)


class MultiAppCrawlerSubagent:
    """
    Subagent #15: Model-based UI state-graph explorer inspired by DroidBot & ByteDance Fastbot.
    """

    def __init__(self, adb: Optional[ADBWrapper] = None, memory: Optional[MemoryManager] = None):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.state_graphs: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Tuple[Optional[Dict[str, int]], int, int]:
        """Parse UIAutomator bounds '[x1,y1][x2,y2]' into dict and center (cx, cy)."""
        if not bounds_str:
            return None, 0, 0
        match = re.findall(r"\d+", bounds_str)
        if len(match) == 4:
            x1, y1, x2, y2 = (int(v) for v in match)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            return {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": cx,
                "center_y": cy,
            }, cx, cy
        return None, 0, 0

    @staticmethod
    def _is_destructive(node: Dict[str, Any]) -> bool:
        """Return True if a node's text or content-desc matches destructive keywords."""
        combined = f"{node.get('text', '')} {node.get('content_desc', '')}".lower().strip()
        if not combined:
            return False
        return any(kw in combined for kw in DESTRUCTIVE_KEYWORDS)

    def extract_interactive_nodes(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Parse UI XML hierarchy and return clickable/interactive nodes with their
        text, content_desc, resource_id, class_name, bounds, and center (cx, cy) coordinates.
        """
        if not xml_content or not xml_content.strip():
            return []

        try:
            root = ET.fromstring(xml_content)
        except Exception:
            return []

        interactive_nodes: List[Dict[str, Any]] = []
        for elem in root.iter("node"):
            attrib = elem.attrib
            clickable = attrib.get("clickable", "false").lower() == "true"
            scrollable = attrib.get("scrollable", "false").lower() == "true"
            checkable = attrib.get("checkable", "false").lower() == "true"
            long_clickable = attrib.get("long-clickable", "false").lower() == "true"
            enabled = attrib.get("enabled", "true").lower() == "true"

            if not enabled:
                continue

            text = attrib.get("text", "").strip()
            content_desc = attrib.get("content-desc", "").strip()
            resource_id = attrib.get("resource-id", "").strip()
            class_name = attrib.get("class", "").strip()
            bounds_str = attrib.get("bounds", "").strip()

            is_interactive = clickable or scrollable or checkable or long_clickable or bool(text or content_desc)
            if not is_interactive:
                continue

            bounds_dict, cx, cy = self._parse_bounds(bounds_str)
            interactive_nodes.append({
                "text": text,
                "content_desc": content_desc,
                "resource_id": resource_id,
                "class_name": class_name,
                "clickable": clickable,
                "scrollable": scrollable,
                "bounds": bounds_dict or bounds_str,
                "cx": cx,
                "cy": cy,
                "center": (cx, cy),
            })

        return interactive_nodes

    def _compute_state_hash(self, package: str, xml_content: str, step: int, nodes: List[Dict[str, Any]]) -> str:
        """Compute a deterministic SHA-256 state hash for the UI hierarchy."""
        if xml_content and xml_content.strip():
            structural_sig = "|".join(
                f"{n.get('class_name', '')}:{n.get('resource_id', '')}:{n.get('text', '')}:{n.get('content_desc', '')}"
                for n in nodes
            )
            payload = structural_sig if structural_sig else xml_content.strip()
        else:
            payload = f"{package}::synthetic_state::{step}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def crawl_application(
        self,
        serial: str,
        package: str,
        max_steps: int = 5,
        run_monkey_burst: bool = False,
        monkey_events: int = 15,
    ) -> Dict[str, Any]:
        """
        Crawl an Android application on `serial` up to `max_steps`, building a UI state-transition
        graph, optionally triggering a Fastbot/Monkey burst, and checking logcat for crashes/ANRs.
        """
        max_steps = max(1, int(max_steps))
        graph: Dict[str, Any] = {
            "serial": serial,
            "package": package,
            "states": {},
            "edges": [],
        }

        # Launch target package
        self.adb.shell(serial, f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

        visited_elements: Set[str] = set()
        prev_state_hash: Optional[str] = None
        last_action_desc: Optional[str] = None

        for step_idx in range(max_steps):
            xml_content = self.adb.dump_ui_hierarchy(serial)
            nodes = self.extract_interactive_nodes(xml_content)
            state_hash = self._compute_state_hash(package, xml_content, step_idx, nodes)

            if state_hash not in graph["states"]:
                graph["states"][state_hash] = {
                    "state_hash": state_hash,
                    "step_discovered": step_idx,
                    "interactive_count": len(nodes),
                    "sample_labels": [
                        n.get("text") or n.get("content_desc") or n.get("resource_id")
                        for n in nodes[:5]
                        if n.get("text") or n.get("content_desc") or n.get("resource_id")
                    ],
                }

            if prev_state_hash is not None and last_action_desc is not None:
                graph["edges"].append({
                    "step": step_idx,
                    "from_state": prev_state_hash,
                    "to_state": state_hash,
                    "action": last_action_desc,
                })

            # Pick an unvisited, non-destructive interactive element
            chosen_node: Optional[Dict[str, Any]] = None
            chosen_sig: Optional[str] = None
            for node in nodes:
                if self._is_destructive(node):
                    continue
                sig = (
                    f"{node.get('resource_id', '')}|"
                    f"{node.get('text', '')}|"
                    f"{node.get('content_desc', '')}|"
                    f"{node.get('cx', 0)},{node.get('cy', 0)}"
                )
                if sig not in visited_elements:
                    chosen_node = node
                    chosen_sig = sig
                    break

            if chosen_node is not None and chosen_sig is not None:
                visited_elements.add(chosen_sig)
                cx, cy = int(chosen_node.get("cx", 0)), int(chosen_node.get("cy", 0))
                label = (
                    chosen_node.get("text")
                    or chosen_node.get("content_desc")
                    or chosen_node.get("resource_id")
                    or chosen_node.get("class_name")
                    or "node"
                )
                if cx > 0 or cy > 0:
                    self.adb.tap(serial, cx, cy)
                else:
                    self.adb.shell(serial, f"input tap {cx} {cy}")
                last_action_desc = f"tap({cx}, {cy})[{label}]"
            else:
                # Synthetic exploration transition for offline/dry-run or exhausted UI trees
                synthetic_next_hash = self._compute_state_hash(package, "", step_idx + 1, [])
                if synthetic_next_hash not in graph["states"]:
                    graph["states"][synthetic_next_hash] = {
                        "state_hash": synthetic_next_hash,
                        "step_discovered": step_idx + 1,
                        "interactive_count": 0,
                        "sample_labels": [f"synthetic_node_{step_idx + 1}"],
                    }
                last_action_desc = f"synthetic_explore(step={step_idx})"
                graph["edges"].append({
                    "step": step_idx,
                    "from_state": state_hash,
                    "to_state": synthetic_next_hash,
                    "action": last_action_desc,
                })
                prev_state_hash = None
                last_action_desc = None
                continue

            prev_state_hash = state_hash

        # Record final transition if last step performed a real tap action
        if prev_state_hash is not None and last_action_desc is not None:
            final_xml = self.adb.dump_ui_hierarchy(serial)
            final_nodes = self.extract_interactive_nodes(final_xml)
            final_hash = self._compute_state_hash(package, final_xml, max_steps, final_nodes)
            if final_hash not in graph["states"]:
                graph["states"][final_hash] = {
                    "state_hash": final_hash,
                    "step_discovered": max_steps,
                    "interactive_count": len(final_nodes),
                    "sample_labels": [
                        n.get("text") or n.get("content_desc") or n.get("resource_id")
                        for n in final_nodes[:5]
                        if n.get("text") or n.get("content_desc") or n.get("resource_id")
                    ],
                }
            graph["edges"].append({
                "step": max_steps,
                "from_state": prev_state_hash,
                "to_state": final_hash,
                "action": last_action_desc,
            })

        if run_monkey_burst:
            self.adb.shell(serial, f"monkey -p {package} --throttle 100 -v {monkey_events}")

        logcat_out = self.adb.shell(serial, "logcat -d -t 80")
        crashes: List[str] = []
        if logcat_out:
            for line in logcat_out.splitlines():
                if "FATAL EXCEPTION" in line or f"ANR in {package}" in line:
                    crashes.append(line.strip())

        graph_key = f"{serial}::{package}"
        self.state_graphs[graph_key] = graph

        self.memory.remember(
            key=f"crawl_{serial}_{package}",
            value={
                "serial": serial,
                "package": package,
                "unique_states_discovered": len(graph["states"]),
                "transitions_recorded": len(graph["edges"]),
                "crashes_detected": len(crashes),
            },
            tags=["crawler", "state_graph", serial, package],
            category="crawler",
        )

        return {
            "status": "CRAWL_COMPLETED",
            "serial": serial,
            "package": package,
            "steps_executed": max_steps,
            "unique_states_discovered": len(graph["states"]),
            "transitions_recorded": len(graph["edges"]),
            "crashes_detected": crashes,
            "state_graph": graph,
        }

    def crawl_multiple_apps(
        self,
        serial: str,
        packages: List[str],
        steps_per_app: int = 3,
    ) -> Dict[str, Any]:
        """
        Crawl each package in `packages` sequentially on `serial` and return an
        aggregated multi-app exploration summary.
        """
        app_results: List[Dict[str, Any]] = []
        total_states = 0
        total_transitions = 0
        total_crashes: List[str] = []

        for pkg in packages:
            res = self.crawl_application(
                serial=serial,
                package=pkg,
                max_steps=steps_per_app,
            )
            app_results.append(res)
            total_states += res.get("unique_states_discovered", 0)
            total_transitions += res.get("transitions_recorded", 0)
            total_crashes.extend(res.get("crashes_detected", []))

        return {
            "status": "MULTI_CRAWL_COMPLETED",
            "serial": serial,
            "packages_crawled": len(packages),
            "packages": list(packages),
            "steps_per_app": steps_per_app,
            "total_unique_states_discovered": total_states,
            "total_transitions_recorded": total_transitions,
            "total_crashes_detected": len(total_crashes),
            "crashes": total_crashes,
            "results": app_results,
        }


if __name__ == "__main__":
    crawler = MultiAppCrawlerSubagent()
    print("MultiAppCrawlerSubagent ready.")
