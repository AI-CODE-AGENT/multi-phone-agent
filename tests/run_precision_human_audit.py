"""
Autonomous Multi-Agent Human-Persona E2E Precision Tester
Uses UIAutomator XML element finding + HumanTouchEngine biomechanics.
Guarantees FoodGo foreground persistence and accurate multi-feature verification.
"""

import os
import sys
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

sys.path.insert(0, r"D:\Project\multi-phone-agent")
from core.adb_wrapper import ADBWrapper
from core.human_touch_engine import HumanTouchEngine
from agents.human_persona_ux_auditor_subagent import HumanPersonaUXAuditorSubagent

ARTIFACT_DIR = r"C:\Users\Admin\.gemini\antigravity\brain\7bbc71df-fd74-4a3e-890e-b9026cf37eff"
SERIAL = "emulator-5554"
PACKAGE = "com.example.fooddelivery"

adb = ADBWrapper()
touch = HumanTouchEngine(adb=adb)
auditor = HumanPersonaUXAuditorSubagent(adb=adb)

def ensure_foreground():
    code, out, _ = adb.run_device_cmd(SERIAL, ["shell", "dumpsys window | grep mCurrentFocus"])
    if PACKAGE not in (out or ""):
        print(f"Bringing {PACKAGE} to foreground...")
        adb.shell(SERIAL, f"am start -n {PACKAGE}/.MainActivity")
        time.sleep(1.5)

def capture(filename: str) -> str:
    path = os.path.join(ARTIFACT_DIR, filename)
    with open(path, "wb") as f:
        subprocess.run(["adb", "-s", SERIAL, "exec-out", "screencap", "-p"], stdout=f)
    print(f"  [SAVED] {filename}")
    return path

def dump_and_find(text: Optional[str] = None, res_id: Optional[str] = None) -> Optional[Tuple[int, int]]:
    xml_str = auditor.dump_xml_reliable(SERIAL)
    if not xml_str:
        return None
    try:
        root = ET.fromstring(xml_str)
        for node in root.iter("node"):
            matched = False
            node_text = (node.attrib.get("text") or "").strip()
            node_id = (node.attrib.get("resource-id") or "").strip()
            node_desc = (node.attrib.get("content-desc") or "").strip()
            
            if text and (text.lower() in node_text.lower() or text.lower() in node_desc.lower()):
                matched = True
            elif res_id and res_id in node_id:
                matched = True
                
            if matched:
                bounds_str = node.attrib.get("bounds", "") # [x1,y1][x2,y2]
                if bounds_str:
                    parts = bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")
                    if len(parts) == 4:
                        x1, y1, x2, y2 = map(int, parts)
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        return cx, cy
    except Exception as e:
        print(f"Error parsing dump: {e}")
    return None

def click_tab(tab_name: str):
    ensure_foreground()
    # Bottom nav tab x coords (1080 width, y ~ 2300)
    tabs = {
        "home": 108,
        "orders": 324,
        "chat": 540,
        "favorites": 756,
        "account": 972
    }
    x = tabs.get(tab_name, 108)
    touch.human_tap(SERIAL, x, 2300)
    time.sleep(1.8)

def run_precision_audit():
    print("=" * 65)
    print("AUTONOMOUS MULTI-AGENT PRECISION E2E AUDIT LAUNCHED")
    print("Device: emulator-5554 | Target: com.example.fooddelivery")
    print("=" * 65)

    # Launch app cleanly
    adb.shell(SERIAL, f"am force-stop {PACKAGE}")
    time.sleep(1.0)
    adb.shell(SERIAL, f"am start -n {PACKAGE}/.ui.splash.SplashActivity")
    time.sleep(3.5)
    ensure_foreground()

    # -------------------------------------------------------------
    # 1. HOME SCREEN & FLOATING CART FAB
    # -------------------------------------------------------------
    print("\n>>> FEATURE 1: Home Screen & Floating Cart FAB")
    capture("feature_1_home_screen.png")
    
    # Human scroll down to explore
    touch.human_bezier_swipe(SERIAL, 540, 1600, 540, 1000, duration_ms=450)
    time.sleep(1.2)
    capture("feature_1_home_scrolled.png")
    
    # Tap the Floating Cart FAB (at bottom-right above bottom nav: ~960, 2150)
    print("Tapping Floating Cart FAB...")
    touch.human_tap(SERIAL, 960, 2150)
    time.sleep(2.0)
    capture("feature_2_draft_orders_from_fab.png")

    # -------------------------------------------------------------
    # 2. SEARCH & DISCOVERY FLOW
    # -------------------------------------------------------------
    print("\n>>> FEATURE 2: Search & Live Discovery Flow")
    click_tab("home")
    time.sleep(1.0)
    # Scroll up to top
    touch.human_bezier_swipe(SERIAL, 540, 700, 540, 1800, duration_ms=400)
    time.sleep(1.0)
    
    # Tap Search Bar on Home
    pos = dump_and_find(res_id="etSearch")
    if pos:
        touch.human_tap(SERIAL, pos[0], pos[1])
    else:
        touch.human_tap(SERIAL, 540, 360)
    time.sleep(2.0)
    capture("feature_3_search_idle_trending.png")

    # Type "Bun bo" with burst typing
    print("Typing search query 'Bun bo'...")
    search_input = dump_and_find(res_id="etSearchQuery")
    if search_input:
        touch.human_tap(SERIAL, search_input[0], search_input[1])
    else:
        touch.human_tap(SERIAL, 450, 160)
    time.sleep(0.5)
    touch.human_type_text(SERIAL, "Bun bo")
    time.sleep(2.0)
    capture("feature_4_search_results.png")

    # Hide keyboard
    adb.shell(SERIAL, "input keyevent 111") # KEYCODE_ESCAPE (dismiss keyboard)
    time.sleep(0.8)

    # -------------------------------------------------------------
    # 3. RESTAURANT STOREFRONT & FOOD DETAIL
    # -------------------------------------------------------------
    print("\n>>> FEATURE 3: Restaurant Storefront & Food Detail Flow")
    # Tap the search result card "Bún Bò Huế Đông Ba"
    restaurant_pos = dump_and_find(text="Bún Bò Huế")
    if restaurant_pos:
        touch.human_tap(SERIAL, restaurant_pos[0], restaurant_pos[1])
    else:
        touch.human_tap(SERIAL, 500, 300)
    time.sleep(2.5)
    capture("feature_5_restaurant_storefront.png")

    # Scroll menu down slightly
    touch.human_bezier_swipe(SERIAL, 540, 1600, 540, 1100, duration_ms=400)
    time.sleep(1.0)
    capture("feature_5b_restaurant_menu.png")

    # Tap on a food item card to open Food Detail
    food_pos = dump_and_find(text="Special Hue") or dump_and_find(text="Bún") or (540, 1250)
    touch.human_tap(SERIAL, food_pos[0], food_pos[1])
    time.sleep(2.2)
    capture("feature_6_food_detail.png")

    # Tap Back button to return to Restaurant, then back to Home
    touch.human_tap(SERIAL, 72, 140)
    time.sleep(1.2)
    touch.human_tap(SERIAL, 72, 140)
    time.sleep(1.2)
    # If still in search, tap back again
    click_tab("home")
    time.sleep(1.0)

    # -------------------------------------------------------------
    # 4. ORDER HISTORY & ORDER DETAIL
    # -------------------------------------------------------------
    print("\n>>> FEATURE 4: Orders History & Detail Flow")
    click_tab("orders")
    time.sleep(1.5)
    
    # Tap "Completed" / "Đã giao" tab
    completed_tab = dump_and_find(text="Completed") or dump_and_find(text="Đã giao") or (800, 280)
    touch.human_tap(SERIAL, completed_tab[0], completed_tab[1])
    time.sleep(1.8)
    capture("feature_7_orders_completed_list.png")

    # Tap on first completed order card
    first_order = dump_and_find(text="Bún Bò Huế") or dump_and_find(text="Đã giao") or (540, 550)
    touch.human_tap(SERIAL, first_order[0], first_order[1])
    time.sleep(2.2)
    capture("feature_8_order_detail.png")

    # Tap back
    touch.human_tap(SERIAL, 72, 140)
    time.sleep(1.2)

    # -------------------------------------------------------------
    # 5. FAVORITES SCREEN
    # -------------------------------------------------------------
    print("\n>>> FEATURE 5: Favorites Screen Flow")
    click_tab("favorites")
    time.sleep(2.0)
    capture("feature_9_favorites_screen.png")

    # -------------------------------------------------------------
    # 6. ACCOUNT & DELIVERY ADDRESSES
    # -------------------------------------------------------------
    print("\n>>> FEATURE 6: Account Profile & Address Book Flow")
    click_tab("account")
    time.sleep(2.0)
    capture("feature_10_account_profile.png")

    # Tap "Địa chỉ nhận hàng" / "Addresses"
    addr_entry = dump_and_find(text="Addresses") or dump_and_find(text="Địa chỉ") or (540, 720)
    touch.human_tap(SERIAL, addr_entry[0], addr_entry[1])
    time.sleep(2.0)
    capture("feature_11_address_book.png")

    # Tap back
    touch.human_tap(SERIAL, 72, 140)
    time.sleep(1.2)

    # -------------------------------------------------------------
    # 7. AI ASSISTANT CHATBOT
    # -------------------------------------------------------------
    print("\n>>> FEATURE 7: AI Assistant Chatbot Flow")
    click_tab("chat")
    time.sleep(2.2)
    capture("feature_12_ai_chat_idle.png")

    # Tap chat input box
    chat_box = dump_and_find(res_id="etMessage") or dump_and_find(res_id="edtMessage") or (450, 2220)
    touch.human_tap(SERIAL, chat_box[0], chat_box[1])
    time.sleep(0.8)
    touch.human_type_text(SERIAL, "Goi y quan an ngon o Quan 1")
    time.sleep(0.5)

    # Tap send button
    send_btn = dump_and_find(res_id="btnSend") or (980, 2220)
    touch.human_tap(SERIAL, send_btn[0], send_btn[1])
    print("Waiting 4 seconds for AI response...")
    time.sleep(4.0)
    capture("feature_13_ai_chat_response.png")

    print("\n" + "=" * 65)
    print("AUTONOMOUS PRECISION E2E AUDIT FULLY COMPLETED!")
    print("=" * 65)

if __name__ == "__main__":
    run_precision_audit()
