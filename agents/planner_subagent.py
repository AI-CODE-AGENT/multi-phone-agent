"""
Planner Subagent
Autonomous test planning, dynamic prompt synthesis, and boundary edge-case generation.
"""

import sys
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class PlannerSubagent:
    """Plans test trajectories, synthesizes prompts, and generates input variations."""

    def __init__(self, agent_id: str = "Planner_Subagent"):
        self.agent_id = agent_id

    def create_plan_from_goal(self, goal: str, target_package: str, current_elements: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Deconstruct a high-level goal into an ordered sequence of executable action milestones.
        """
        plan = []
        goal_lower = goal.lower()

        # Check for OTP / Phone Login intent
        if "otp" in goal_lower or "login" in goal_lower or "đăng nhập" in goal_lower:
            phone_match = re.search(r"(\d{10,11})", goal)
            phone_number = phone_match.group(1) if phone_match else "0941189263"

            plan.append({
                "milestone": "Launch_App",
                "action": "launch",
                "package": target_package,
                "description": f"Launch target app {target_package}"
            })
            plan.append({
                "milestone": "Enter_Phone_Number",
                "action": "input",
                "locator": "phone",
                "text": phone_number,
                "description": f"Enter phone number {phone_number}"
            })
            plan.append({
                "milestone": "Request_OTP",
                "action": "tap",
                "locator": "gửi mã|tiếp tục|login|sign in|xác nhận",
                "description": "Tap request OTP / submit phone"
            })
            plan.append({
                "milestone": "Auto_Deliver_Mock_OTP",
                "action": "mock_otp_flow",
                "phone": phone_number,
                "description": "Intercept and autofill OTP locally with 0 VND carrier cost"
            })
            plan.append({
                "milestone": "Submit_Verification",
                "action": "tap",
                "locator": "xác thực|hoàn tất|verify|submit",
                "description": "Submit verification and verify dashboard entry"
            })
        else:
            # General exploratory navigation plan
            plan.append({
                "milestone": "Launch_App",
                "action": "launch",
                "package": target_package,
                "description": f"Launch app {target_package}"
            })
            plan.append({
                "milestone": "Dismiss_Dialogs",
                "action": "dismiss_dialogs",
                "description": "Handle system permission and greeting modals"
            })
            plan.append({
                "milestone": "Explore_Core_Flows",
                "action": "explore",
                "max_steps": 15,
                "description": f"Autonomously navigate UI buttons and forms according to goal: {goal}"
            })

        return plan

    def generate_edge_case_inputs(self, input_category: str) -> List[str]:
        """
        Generate diverse inputs for boundary, fuzzing, and stress testing.
        """
        cat = input_category.lower()
        if "phone" in cat:
            return [
                "0941189263",               # Valid Vietnam phone
                "0000000000",               # Boundary invalid
                "0941189",                  # Too short
                "094118926312345",          # Too long
                "094118926a",               # Alpha characters
                "+84 94 118 9263"           # Formatted with spaces
            ]
        elif "email" in cat:
            return [
                "test.user@example.com",
                "user+alias@sub.domain.org",
                "plainaddress",
                "@missingusername.com",
                "user@.com.my",
                "<script>alert(1)</script>@test.com"  # XSS test
            ]
        elif "password" in cat:
            return [
                "P@ssw0rd2026!",            # Strong standard
                "123456",                   # Weak
                "a" * 128,                  # Boundary long
                "'; DROP TABLE users; --",  # SQL injection test
                " mật khẩu có dấu "          # Unicode Vietnamese with spaces
            ]
        elif "name" in cat or "text" in cat:
            return [
                "Nguyễn Văn A",
                "Trần Thị Bích Ngọc 🎉",
                "A" * 255,
                "Robert'); DROP TABLE Students;--",
                "  Leading and Trailing Spaces  "
            ]
        return ["sample_input_1", "sample_input_2"]


if __name__ == "__main__":
    planner = PlannerSubagent()
    p = planner.create_plan_from_goal("Dang nhap bang so dien thoai 0941189263 va nhap OTP", "com.example.app")
    print("Generated Plan:")
    for step in p:
        print(f" - [{step['milestone']}] {step['action']}: {step['description']}")
