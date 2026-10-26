# ⚡ Android Multi-Agent Farm (AMAF v19.0) — Hybrid Real Phone & 25-OS Responsive QA Studio

**Hệ sinh thái Kiểm thử Tự động Thay thế Hoàn toàn Tester (Zero-Human Autonomous QA), Quản trị Hybrid (Điện thoại thật Vivo OriginOS + 4 Máy ảo Headless Android 15), 25 Hệ điều hành Đa nền tảng, Giao diện 4-Zone IDE Sáng/Tối (`Light` & `Dark Mode`), 8 Bộ Giao diện Mẫu Website/Desktop, Sinh mã Test 7 Frameworks, 125 Subagents Tự tiến hóa & 70 Công cụ MCP On-Demand.**

---

## 🌟 Điểm Nhấn Kiến Trúc AMAF v19.0

1. **100% On-Demand MCP Server (`70 Tools` — Không chạy ngầm 24/7)**:
   - Kết nối trực tiếp với Antigravity, ARTEMIS, Claude Code, Cursor, OpenCode, Kilo Code qua [`mcp_bridge/android_farm_mcp_server.py`](mcp_bridge/android_farm_mcp_server.py).
   - Tự động cài đặt APK trên Vivo OriginOS (`PackageInterceptActivity`), tự tích ô **"Tôi đã hiểu kết quả phát hiện rủi ro của ứng dụng"** (`input tap 629 2449`) và bấm **"Tiếp tục cài đặt"** (`input tap 630 2621`) bằng Scoped Watcher chỉ chạy trong phiên cài đặt rồi tắt ngay.
2. **Kiểm thử Đa màn hình & 25 Hệ điều hành (`CrossPlatformOSMatrixEngine`)**:
   - Bao phủ **Windows 11, macOS Sequoia, ChromeOS, 6 bản Linux (`Ubuntu`, `Mint`, `Fedora`, `Manjaro`, `Elementary`, `Zorin`), iOS 18, iPadOS 18, Android 15, Vivo OriginOS 5/6, HarmonyOS 4.2, HarmonyOS NEXT (`Mate XT Tri-Fold`), GrapheneOS, LineageOS 21, Ubuntu Touch, Sailfish OS, KaiOS 3.1, LG webOS TV, Hisense VIDAA TV**.
   - Tự động sinh bản vá giao diện cho **8 Frameworks** (`Android XML`, `Jetpack Compose`, `SwiftUI`, `HarmonyOS ArkTS`, `Web CSS`, `TV/KaiOS D-Pad`, `Tauri v2 shadcn/ui`, `Electron React`).
3. **Giao diện 4-Zone Desktop Studio (`Light Mode` ☀️ & `Dark Mode` 🌙 + `8 Website UI Presets`)**:
   - Chuyển đổi tức thì giữa **Light Mode** và **Dark Mode** (`Ctrl+T`), đổi nóng qua **8 bộ mẫu giao diện nổi tiếng** (`shadcn/ui`, `Linear`, `Stripe`, `Vercel Geist`, `Supabase`, `macOS Sequoia`, `Windows 11 Fluent 2`, `Tauri Raycast` qua `Ctrl+P`).
   - Hỗ trợ **Perceptual SSIM & Pixel-Diff Inspector** và chuẩn hóa cân đối toàn bộ **12 Workspace Tabs**.
4. **AMAF v19.0 — Sinh mã Test 7 Frameworks, Kiểm toán Bảo mật APK MASVS, HAR OpenAPI & CI/CD Gates**:
   - **7-Framework Codegen (`#116`)**: Biên dịch thao tác thành code test chạy được ngay trên `Playwright TS`, `Appium Python`, `Maestro YAML`, `Espresso Kotlin`, `Jetpack Compose UI Test`, `Apple XCUITest Swift`, và `Cypress JS` theo triết lý *Dynamic-First, Coordinate-Fallback*.
   - **APK Static & Permissions Security (`#117`)**: Kiểm tra chữ ký v2/v3, căn chỉnh trang 16KB cho Android 15 (SDK 35), OWASP MASVS và quyền nhạy cảm.
   - **Live HAR & OpenAPI Contract Validator (`#118`)**, **i18n RTL/CJK/Vietnamese Diacritic Critic (`#119`)**, và **CI/CD JUnit XML + SARIF 2.1.0 + GitHub Actions Exporter (`#120`)**.

---

## 🚀 Cách Mở Nhanh Giao Diện AMAF v19.0 Studio

### Cách 1: Nháy đúp chuột
- Tại thư mục dự án: [`D:\Project\multi-phone-agent\run_farm_gui.bat`](run_farm_gui.bat)
- Hoặc từ thư mục công cụ: `D:\Project\Tools\run_farm_gui.bat`

### Cách 2: Chạy bằng dòng lệnh (PowerShell / Terminal)
```powershell
cd D:\Project\multi-phone-agent
python gui\farm_dashboard.py
```

### Bảng Phím Tắt Điều Khiển Nhanh
| Phím tắt | Chức năng |
| :---: | :--- |
| **`Ctrl + T`** | Chuyển đổi tức thì **Light Mode ☀️ ↔ Dark Mode 🌙** trên toàn bộ 12 tab |
| **`Ctrl + P`** | Đổi nóng qua **8 bộ Website & Desktop UI Presets** (`16` bảng màu chuẩn WCAG AAA) |
| **`Ctrl + D`** | Mở rộng / Thu gọn khay 4 thẻ thiết bị (giải phóng `+45%` chiều cao màn hình) |
| **`Ctrl + K`** | Mở **Command Palette** tìm kiếm nhanh `125 Subagents`, `70 MCP Tools`, `25 OS` |
| **`Ctrl + B` / `Ctrl + I`** | Ẩn / Hiện thanh **Left Sidebar** hoặc **Right Inspector** |

---

## 🧪 Chạy Kiểm Thử Tự Động (Pytest Suite)

```powershell
cd D:\Project\multi-phone-agent
python -m pytest -q
```
**Kết quả:** `228 passed (100% PASS)`
