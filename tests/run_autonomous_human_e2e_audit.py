"""
Autonomous Multi-Agent Human-Persona E2E Test & Logic Audit
Operates against emulator-5554 using AMAF HumanTouchEngine & ADBWrapper.
Saves all visual artifacts to the Antigravity artifact directory.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, r"D:\Project\multi-phone-agent")
from core.adb_wrapper import ADBWrapper
from core.human_touch_engine import HumanTouchEngine
from agents.human_persona_ux_auditor_subagent import HumanPersonaUXAuditorSubagent

ARTIFACT_DIR = r"C:\Users\Admin\.gemini\antigravity\brain\7bbc71df-fd74-4a3e-890e-b9026cf37eff"
SERIAL = "emulator-5554"

adb = ADBWrapper()
touch = HumanTouchEngine(adb=adb)
auditor = HumanPersonaUXAuditorSubagent(adb=adb)

def take_screenshot(name: str) -> str:
    path = os.path.join(ARTIFACT_DIR, name)
    with open(path, "wb") as f:
        subprocess.run(["adb", "-s", SERIAL, "exec-out", "screencap", "-p"], stdout=f)
    print(f"Captured: {name}")
    return path

def switch_tab(menu_id: str, desc: str):
    print(f"Switching to tab: {desc} ({menu_id})...")
    # Coordinates of bottom nav items on 1080x2400 (5 items):
    # nav_home: ~108, 2300 | nav_ordes: ~324, 2300 | nav_chat: ~540, 2300 | nav_favorites: ~756, 2300 | nav_profile: ~972, 2300
    tab_x = {
        "nav_home": 108,
        "nav_ordes": 324,
        "nav_chat": 540,
        "nav_favorites": 756,
        "nav_profile": 972
    }.get(menu_id, 108)
    touch.human_tap(SERIAL, tab_x, 2300)
    time.sleep(1.8)

def run_e2e_suite():
    print("=" * 60)
    print("STARTING AUTONOMOUS HUMAN-PERSONA E2E TESTING SUITE")
    print(f"Target Device: {SERIAL}")
    print("=" * 60)

    # 1. Launch App Fresh
    print("\n--- [Step 1] Launching FoodGo ---")
    adb.shell(SERIAL, "am force-stop com.example.fooddelivery")
    time.sleep(1)
    adb.shell(SERIAL, "am start -n com.example.fooddelivery/.ui.splash.SplashActivity")
    time.sleep(3.5)

    # 2. Home Screen
    print("\n--- [Step 2] Auditing Home Screen ---")
    take_screenshot("audit_1_home_screen.png")
    # Simulate human reading pause & smooth bezier scroll
    time.sleep(1.2)
    touch.human_bezier_swipe(SERIAL, 540, 1600, 540, 900, duration_ms=450)
    time.sleep(1.5)
    take_screenshot("audit_2_home_scrolled.png")
    
    # Tap the newly updated floating cart FAB (bottom-right: ~960, 2150)
    print("Testing Floating Cart FAB button on Home...")
    touch.human_tap(SERIAL, 960, 2150)
    time.sleep(2.0)
    take_screenshot("audit_3_draft_orders_from_fab.png")

    # 3. Search Flow
    print("\n--- [Step 3] Auditing Search Flow ---")
    switch_tab("nav_home", "Home")
    time.sleep(1.0)
    # Scroll back to top
    touch.human_bezier_swipe(SERIAL, 540, 600, 540, 1800, duration_ms=400)
    time.sleep(1.2)
    # Tap search bar (center ~540, 360)
    touch.human_tap(SERIAL, 540, 360)
    time.sleep(2.0)
    take_screenshot("audit_4_search_idle_trending.png")
    
    # Type search query "Bún bò"
    print("Typing search query with human burst cadence...")
    # Tap search EditText inside search screen
    touch.human_tap(SERIAL, 400, 230)
    time.sleep(0.8)
    touch.human_type_text(SERIAL, "Bun bo")
    time.sleep(2.0)
    take_screenshot("audit_5_search_results.png")

    # 4. Restaurant & Food Detail Flow
    print("\n--- [Step 4] Auditing Restaurant & Food Detail Flow ---")
    # Tap first restaurant result or back to home
    adb.shell(SERIAL, "input keyevent 4") # Back to idle search or home
    time.sleep(1.0)
    switch_tab("nav_home", "Home")
    time.sleep(1.2)
    
    # Scroll to nearby restaurants and tap "Bún Bò Huế Đông Ba"
    touch.human_bezier_swipe(SERIAL, 540, 1400, 540, 800, duration_ms=400)
    time.sleep(1.2)
    # Tap nearby restaurant card
    touch.human_tap(SERIAL, 300, 1100)
    time.sleep(2.2)
    take_screenshot("audit_6_restaurant_detail.png")

    # Tap first food item in menu
    touch.human_bezier_swipe(SERIAL, 540, 1600, 540, 1200, duration_ms=350)
    time.sleep(1.0)
    touch.human_tap(SERIAL, 540, 1400)
    time.sleep(2.0)
    take_screenshot("audit_7_food_detail.png")
    
    # Back to restaurant then back to home
    adb.shell(SERIAL, "input keyevent 4")
    time.sleep(1.0)
    adb.shell(SERIAL, "input keyevent 4")
    time.sleep(1.0)

    # 5. Orders History & Order Detail Flow
    print("\n--- [Step 5] Auditing Orders History & Detail ---")
    switch_tab("nav_ordes", "Orders")
    time.sleep(1.5)
    # Tap "Đã giao" / "Completed" tab (tab ~800, 280)
    touch.human_tap(SERIAL, 800, 280)
    time.sleep(1.5)
    take_screenshot("audit_8_orders_completed_list.png")

    # Tap first completed order card to view Order Details
    touch.human_tap(SERIAL, 540, 500)
    time.sleep(2.0)
    take_screenshot("audit_9_order_detail.png")
    adb.shell(SERIAL, "input keyevent 4")
    time.sleep(1.0)

    # 6. Favorites Flow
    print("\n--- [Step 6] Auditing Favorites Screen ---")
    switch_tab("nav_favorites", "Favorites")
    time.sleep(1.8)
    take_screenshot("audit_10_favorites.png")

    # 7. Account & Addresses Flow
    print("\n--- [Step 7] Auditing Account & Address Book ---")
    switch_tab("nav_profile", "Account")
    time.sleep(1.8)
    take_screenshot("audit_11_account.png")
    
    # Tap "Địa chỉ nhận hàng" / "Addresses" (~540, 720)
    touch.human_tap(SERIAL, 540, 720)
    time.sleep(2.0)
    take_screenshot("audit_12_addresses.png")
    adb.shell(SERIAL, "input keyevent 4")
    time.sleep(1.0)

    # 8. AI Assistant Chatbot Flow
    print("\n--- [Step 8] Auditing AI Assistant Chatbot ---")
    switch_tab("nav_chat", "AI Assistant")
    time.sleep(2.0)
    take_screenshot("audit_13_ai_chat_initial.png")

    # Tap chat input box (~500, 2220) and send question
    touch.human_tap(SERIAL, 500, 2220)
    time.sleep(0.8)
    touch.human_type_text(SERIAL, "Goi y mon bun ngon")
    time.sleep(0.5)
    # Tap Send button (~980, 2220)
    touch.human_tap(SERIAL, 980, 2220)
    time.sleep(3.5)
    take_screenshot("audit_14_ai_chat_replied.png")

    print("\n" + "=" * 60)
    print("ALL 8 FEATURES TESTED LIVE ON EMULATOR-5554 WITH HUMAN TOUCH!")
    print("=" * 60)

if __name__ == "__main__":
    run_e2e_suite()
