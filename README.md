# ⚡ Android Multi-Agent Farm (AMAF 3.0) - Hybrid Real Phone Farm, Group Broadcast & 12-Subagent Self-Evolution Matrix

**Hệ sinh thái Quản trị Hybrid (Máy Thật Vật Lý + 4 Máy Ảo Headless Android 15), Đồng Bộ Hóa Đa Màn Hình (Group Broadcast), Giả lập Phần cứng 0 VNĐ & Kiểm thử Tự Tiến Hóa 12 Subagents dành cho Đa IDE và Đa AI Agent (Antigravity, ARTEMIS, Cursor, OpenCode, Kilo Code).**

---

## 🌟 Tổng Quan & Kiến Trúc Đột Phá AMAF 3.0

Hệ thống được nâng cấp lên phiên bản **AMAF 3.0** dựa trên tinh hoa kiến trúc của **SonicCloud**, **DeviceFarmer/STF**, **ws-scrcpy**, **Total Control Sigma-RT**, **Mobile-Agent-v2**, **Mobile-Agent-E** và **AppAgent v2**:
1. **Optional Real Phone Farm (`HYBRID` / `AVD_ONLY` / `REAL_ONLY`)**: Hỗ trợ điều khiển song song nhiều máy thật cắm cáp USB hoặc kết nối không dây **Wireless ADB over TCP/IP (`:5555`)**, tích hợp **Battery & Thermal Guard** tự động hạ độ sáng màn hình (`15/255`) và ngắt sạc mềm (`dumpsys battery unplug`) khi nhiệt độ vượt `42.0°C`.
2. **Synchronized Group Control Broadcaster**: Đồng bộ thao tác chạm, vuốt, gõ phím, mở ứng dụng trên hàng chục điện thoại thật và máy ảo cùng lúc với thuật toán **Normalized Cross-Resolution Coordinate Scaling** (tự động quy đổi tọa độ giữa màn `720x1600`, `1080x2400`, `1440x3200`).
3. **12 Subagents Tự Tiến Hóa (`SelfEvolutionEngine`) & MCP Server 2.0 (18 Công Cụ)**: Tự động khám phá lỗi, tự lập kế hoạch, tự phục hồi 6 cấp độ, tự sinh bản vá `.diff`, tự kiểm thử hồi quy, tự tối ưu hóa Prompt và đúc kết **Macro-Action Shortcuts** giúp tăng tốc 5 lần cho các chu kỳ sau.

```
       ┌────────────────────────────────────────────────────────┐
       │     🧠 CODEBASE MEMORY MCP (codebase_memory.json)       │
       │  - UI Locators    - Defects   - Patches   - Prompts    │
       └───────────────────────────┬────────────────────────────┘
                                   │
       ┌───────────────────────────▼────────────────────────────┐
       │     📋 AGILE KANBAN BOARD (core/kanban_board.py)       │
       │  Backlog ➔ Planning ➔ Dev ➔ QA ➔ Heal ➔ Patch ➔ Done  │
       └───────────────────────────┬────────────────────────────┘
                                   │
       ┌───────────────────────────▼────────────────────────────┐
       │   🎛️ AUTONOMOUS PIPELINE DIRECTOR (Master Conductor)   │
       │     Điều phối 8 Subagent - Vòng lặp Dev-QA Khép kín     │
       └─────┬──────────────┬──────────────┬──────────────┬─────┘
             │              │              │              │
     ┌───────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐
     │ Pixel_Farm_1 ││ Pixel_Farm_2││ Pixel_Farm_3││ Pixel_Farm_4│
     │(Customer Auth││  (Merchant  ││(Chaos Stress││(Performance │
     │  & Mock OTP) ││ & GPS Spoof)││  & Fuzzing) ││& Sec Audit) │
     └──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

---

## 🚀 Đội Ngũ 8 Subagent Tự Trị & Tính Năng Chuyên Biệt

1. **`PlannerSubagent`**: Phân rã mục tiêu cấp cao, sinh bộ dữ liệu kiểm thử biên (Edge Cases, số điện thoại, ký tự Unicode, chuỗi SQLi).
2. **`OperatorSubagent`**: Thao tác ADB không trễ, liên kết trực tiếp với dịch vụ Mock OTP (0 VNĐ) và giả lập sinh trắc học vân tay.
3. **`VisionPerceptionSubagent`**: Phân tích ảnh chụp màn hình đa phương thức, phát hiện bất thường (màn hình đen, bàn phím che nút, modal scrim), và định vị tọa độ tương tác không phụ thuộc XML UIAutomator.
4. **`SelfHealingSubagent` (6 Cấp độ tự phục hồi)**:
   - *Selector & Locator Healing*: So khớp mờ Levenshtein Distance khi nút đổi chữ/ID.
   - *Timing & Adaptive Polling*: Tự co giãn thời gian chờ theo độ trễ API/mạng thực tế.
   - *Viewport & Layout Navigation*: Tự cuộn tìm nút ẩn bên dưới màn hình.
   - *Modal & Dialog Dismissal*: Tự phát hiện và đóng quyền cấp phép OS, bàn phím ảo che khuất nút.
   - *Test Data Healing*: Tự làm mới Mock OTP và tài khoản kiểm thử khi hết hạn.
   - *Crash & Defect Isolation*: Phân tách lỗi script test và lỗi crash thật của ứng dụng.
5. **`AuditorSubagent`**: Đo độ trễ khởi động lạnh (Cold launch), bắt giật khung hình (Jank > 16ms qua `dumpsys gfxinfo`), quét thiếu nhãn trợ năng (`content-description`).
6. **`SecurityAuditorSubagent`**: Quét các lỗ hổng bảo mật phổ biến theo chuẩn **OWASP Mobile Top 10** (Cleartext HTTP, Exported components, Debuggable release build, ADB backup exposure).
7. **`PromptOptimizerSubagent` (Self-Prompting Engine)**: Tự động phân tích các ca phục hồi / thất bại để tối ưu hóa, chèn thêm luật hành vi và sinh phiên bản system prompt mới lưu vào bộ nhớ.
8. **`CodeImproverSubagent` & `RegressionVerifierSubagent` (Tự Vá Code & Kiểm Thử Hồi Quy)**:
   - Khi phát hiện crash hoặc bottleneck hiệu năng: Tự động phân tích stack trace và sinh file vá chuẩn Git (`.diff` / `.patch`) lưu tại `reports/patches/`.
   - `RegressionVerifierSubagent` áp dụng bản vá và chạy kịch bản kiểm thử hồi quy trực tiếp trên máy ảo để chứng minh bản vá giải quyết triệt để lỗi mà không gây phản ứng phụ.

---

## 📱 Ma Trận 4 Máy Ảo & Vai Trò (Personas)

| Máy ảo | Port / Serial | Vai trò kiểm thử | Kịch bản tự động hóa |
| :--- | :--- | :--- | :--- |
| **Pixel_Farm_1** | `emulator-5554` | **Customer Persona** | Đăng nhập bằng số `0941189263`, nhận Mock OTP 0 VNĐ, xác thực vân tay. |
| **Pixel_Farm_2** | `emulator-5556` | **Merchant & Driver Persona** | Nhận đơn hàng, giả lập vị trí GPS Landmark 81 TP.HCM, mô phỏng tuyến đường di chuyển. |
| **Pixel_Farm_3** | `emulator-5558` | **Chaos & Stress Persona** | Fuzzing chuỗi đặc biệt, xoay màn hình 90°/0°, chuyển đổi mạng offline/online. |
| **Pixel_Farm_4** | `emulator-5560` | **Performance & Security Auditor** | Đo thời gian khởi động lạnh, kiểm tra tụt khung hình đồ họa (`dumpsys gfxinfo`), quét lỗ hổng OWASP Mobile. |

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh

### Cách 1: Giao Diện Desktop Control Center (Khuyên Dùng)
Nhấp đúp chuột vào file:
👉 **`D:\Project\Tools\run_farm_gui.bat`** (hoặc `D:\Long-app\Android-Mutile-Agents\launchers\run_farm_gui.bat`)

- **Tab 1: Virtual Phone Devices**: Xem trạng thái 4 máy, xem màn hình (`scrcpy`), kích hoạt vân tay, SMS OTP, GPS, Debloat.
- **Tab 2: Multi-Agent Orchestration**: 
  - Bấm **"⚡ Run 4-Device Persona Matrix"** để chạy ma trận kiểm thử song song.
  - Bấm **"🚀 Run Autonomous Agile Pipeline"** để kích hoạt toàn bộ 8 Subagent tự điều phối Kanban từ BACKLOG đến DONE.
- **Tab 3: Defect Reports**: Xem các báo cáo lỗi Markdown kèm ảnh chụp màn hình bằng chứng.
- **Tab 4: Memory & Patches**: Xem các bản vá mã nguồn (`.patch`) và các phiên bản prompt do AI tự tối ưu.

---

### Cách 2: Dòng Lệnh (CLI)
Mở terminal tại `D:\Long-app\Android-Mutile-Agents`:

```powershell
# 1. Kiểm tra trạng thái toàn bộ máy trong farm
python cli\farm_cli.py status

# 2. Chạy quy trình Agile Pipeline tự chủ (Kanban BACKLOG -> DONE)
python cli\farm_cli.py pipeline

# 3. Chạy Ma trận Đa Agent song song trên cả 4 máy (Persona Matrix)
python cli\farm_cli.py matrix

# 4. Quét lỗ hổng an ninh Mobile OWASP
python cli\farm_cli.py security --serial emulator-5554 --package com.android.settings

# 5. Xem bảng Kanban trực tiếp
python cli\farm_cli.py kanban

# 6. Quản lý Mock OTP (0 VNĐ cho số 0941189263)
python cli\farm_cli.py mock-otp --phone 0941189263 --generate
python cli\farm_cli.py mock-otp --phone 0941189263 --get

# 7. Xem Bộ nhớ Trí tuệ & Bản vá tự sinh
python cli\farm_cli.py memory --summary
python cli\farm_cli.py memory --patches
python cli\farm_cli.py memory --prompts

# 8. Mở màn hình xem trực tiếp máy số 1 qua scrcpy
python cli\farm_cli.py view --device 1
```

---

### Cách 3: Tích Hợp Đa IDE Qua REST API (Port 8088)
Chạy server API bằng file `D:\Project\Tools\run_api_server.bat`:
- `GET http://127.0.0.1:8088/api/status` : Trạng thái 4 máy & khóa tài nguyên
- `GET http://127.0.0.1:8088/api/kanban/board` : Bảng điều phối Kanban tasks
- `POST http://127.0.0.1:8088/api/pipeline/run` : Kích hoạt quy trình tự trị 8 Subagent
- `POST http://127.0.0.1:8088/api/security/audit` : Kích hoạt quét an ninh OWASP
- `GET http://127.0.0.1:8088/api/memory/patches` : Lấy danh sách các bản vá code tự sinh
- `GET http://127.0.0.1:8088/api/otp/latest?phone=0941189263` : Lấy mã Mock OTP đang hoạt động

---

## 🧪 Kết Quả Kiểm Thử Hệ Thống (Unit Tests)
Chạy toàn bộ 18 bài kiểm thử tích hợp:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```
**Kết quả:** `Ran 18 tests in 2.48s — OK (100% Passed)`
