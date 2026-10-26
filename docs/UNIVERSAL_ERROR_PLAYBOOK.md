# Sổ Tay Lỗi Kỹ Thuật & Quy Tắc Phòng Ngừa Đa Dự Án (Universal Engineering Error Playbook)

> **Mục đích**: Lưu trữ tập trung toàn bộ các lỗi kỹ thuật thực tế (Symptom → Root Cause → Golden Rule → Fix Pattern → Verification Hook) để **tái sử dụng cho bất kỳ dự án nào** (Python, Node.js/TypeScript, MCP Server, Windows Automation, Desktop GUI, Android ADB, PyTorch/GPU, AI Multi-Agent).
> **Cách dùng cho dự án mới**: Sao chép tệp này (hoặc `universal_error_ledger.jsonl`) vào thư mục gốc / `.ai/` của dự án mới, hoặc đính kèm vào System Prompt / `CLAUDE.md` / `AGENTS.md` để AI Agent không bao giờ lặp lại các lỗi đã từng gặp.

---

## Danh Mục 12 Lỗi Thực Tế & Quy Tắc Bất Biến (Golden Rules)

### `ERR-001` — Tiến trình MCP Server (`npx tsx` / `stdio`) treo ở trạng thái `RUNNING` với `No log output recorded yet`
- **Bối cảnh / Công nghệ**: Node.js, TypeScript (`npx tsx`), Python MCP Server (`stdio`), PowerShell Background Task.
- **Triệu chứng (Symptom)**: Chạy lệnh kiểm thử MCP server (ví dụ `npx tsx src/index.ts` hoặc `python mcp_server.py`) khiến task chạy ngầm bị treo vô hạn ở trạng thái `Status: RUNNING` và hiển thị `No log output recorded yet`.
- **Nguyên nhân gốc (Root Cause)**:
  1. Giao thức MCP `stdio` thiết kế để lắng nghe luồng `stdin` vô hạn chờ gói tin JSON-RPC (`initialize`). Khi gọi trực tiếp từ shell mà không đóng `stdin` hoặc không truyền EOF, tiến trình đứng chờ `stdin` mãi mãi.
  2. Luồng `stdout`/`stderr` trong môi trường pipe không phải TTY bị hệ điều hành gom bộ đệm (buffered 4KB–8KB), nên các dòng log nhỏ không được đẩy ra ngay.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **KHÔNG BAO GIỜ** chạy trực tiếp một `stdio` MCP server từ dòng lệnh mà không truyền gói tin JSON-RPC kèm đóng luồng `stdin` (hoặc cờ `--healthcheck` / `--oneshot`).
  - **LUÔN LUÔN** bật chế độ unbuffered (`PYTHONUNBUFFERED=1`, `python -u`, `flush=True`) và in ngay một dòng `[START-HEARTBEAT]` ra `stderr`/`stdout` trong 50ms đầu tiên của mọi công cụ CLI/daemon.
- **Mẫu code chuẩn (Fix Pattern)**:
  ```powershell
  # Kiểm thử MCP stdio server an toàn trong <2s (tự đóng stdin sau khi gửi initialize):
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}' | npx tsx src/index.ts
  ```
  ```python
  # Trong Python CLI / MCP Runner: luôn cấu hình line-buffering ngay đầu file
  import sys
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
  if hasattr(sys.stderr, "reconfigure"):
      sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
  ```

---

### `ERR-002` — Hỏng phông chữ UTF-8 / Tiếng Việt biến thành dấu `?` khi pipe code qua PowerShell
- **Bối cảnh / Công nghệ**: Windows PowerShell, Python, Node.js, xử lý chuỗi đa ngôn ngữ (Tiếng Việt, ký tự Unicode `●`, `▸`, `°`, `·`).
- **Triệu chứng (Symptom)**: Truyền script Python qua pipe `@' ... '@ | python -` trong PowerShell làm toàn bộ dấu Tiếng Việt và icon Unicode trong tệp nguồn bị biến thành ký tự `?` hoặc Mojibake.
- **Nguyên nhân gốc (Root Cause)**: PowerShell mặc định mã hóa luồng pipe `stdin` sang tiến trình ngoài (native command) theo bảng mã OEM/CP1252 của Windows thay vì UTF-8.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **KHÔNG BAO GIỜ** dùng `@' ... '@ | python -` trong PowerShell để ghi tệp chứa tiếng Việt hoặc ký tự Unicode.
  - **LUÔN LUÔN** tạo tệp script tạm bằng công cụ ghi file chuẩn UTF-8 (`write_file`) hoặc dùng chuỗi escape `\uXXXX` và mở tệp với `encoding="utf-8"`.
- **Kiểm chứng (Verification Hook)**:
  ```python
  # Kiểm tra không có ký tự lỗi replacement trong mã nguồn:
  assert "\ufffd" not in open("file.py", encoding="utf-8").read()
  ```

---

### `ERR-003` — Lỗi `The filename or extension is too long` (WinError 206) khi chạy lệnh inline trên Windows
- **Bối cảnh / Công nghệ**: Windows Command Prompt / PowerShell, `subprocess.Popen`, `python -c "..."`.
- **Triệu chứng (Symptom)**: Lệnh `python -c "<script dài>"` thất bại với lỗi `The filename or extension is too long`.
- **Nguyên nhân gốc (Root Cause)**: Giới hạn cứng `32,767` ký tự của hàm Win32 `CreateProcessW` cho chuỗi `lpCommandLine`.
- **Quy tắc bắt buộc (Golden Rule)**:
  - Mọi script tự động hóa dài quá `2,000` ký tự phải được ghi ra tệp `.py` trong thư mục `scratch/` rồi gọi `python scratch/script.py`.

---

### `ERR-004` — Lỗi `OSError: screen grab failed` khi chụp ảnh màn hình tự động trên Windows
- **Bối cảnh / Công nghệ**: Python `PIL.ImageGrab.grab()`, `pyautogui.screenshot()`, kiểm thử giao diện tự động trên Windows.
- **Triệu chứng (Symptom)**: Gọi `ImageGrab.grab()` từ tiến trình nền hoặc phiên terminal không gắn trực tiếp với Desktop tương tác báo lỗi `OSError: screen grab failed` hoặc chụp ra ảnh đen.
- **Nguyên nhân gốc (Root Cause)**: `BitBlt` từ Desktop DC bị chặn khi tiến trình chạy trong ngữ cảnh background session hoặc cửa sổ bị che khuất.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **LUÔN LUÔN** sử dụng API Win32 `PrintWindow(hwnd, memDC, PW_RENDERFULLCONTENT=2)` kết hợp `GetDIBits` trực tiếp trên `HWND` của cửa sổ ứng dụng — chụp chính xác 100% nội dung cửa sổ trong `<0.3s` kể cả khi chạy ngầm.

---

### `ERR-005` — Đơ cứng giao diện (UI Freeze 5s–60s) do gọi `subprocess` (`adb`, `git`, `netstat`) trên Main UI Thread
- **Bối cảnh / Công nghệ**: Tkinter, PyQt, Electron, React Native, Flutter, mọi ứng dụng GUI có kết nối CLI/ADB.
- **Triệu chứng (Symptom)**: Ứng dụng mất phản hồi (`Not Responding`) khi mở cửa sổ, chuyển tab hoặc khi thiết bị ngoại vi / mạng phản hồi chậm.
- **Nguyên nhân gốc (Root Cause)**: Gọi đồng bộ `subprocess.run(["adb", "devices"])` hoặc `psutil.process_iter()` trực tiếp trong hàm khởi tạo `__init__` hoặc callback sự kiện giao diện.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **TUYỆT ĐỐI KHÔNG** gọi `subprocess.run` trên luồng giao diện chính (Main UI Thread).
  - Mọi hàm đọc dữ liệu trên UI Thread phải lấy từ bộ nhớ đệm (`_cached_state`, thời gian đọc `0ms`), còn việc cập nhật dữ liệu phải chạy trên luồng nền (`threading.Thread(daemon=True)`) có `timeout` ngắn (`2s–4s`) và đẩy kết quả về UI qua `root.after(0, callback)`.

---

### `ERR-006` — Khởi tạo lặp lại mô hình AI / PyTorch / Tài nguyên nặng làm chậm 10x thời gian mở ứng dụng
- **Bối cảnh / Công nghệ**: Python, PyTorch, CUDA, OpenCV, PIL, kiến trúc Multi-Agent.
- **Triệu chứng (Symptom)**: Khởi động ứng dụng mất `15s–30s` và ngốn hàng trăm MB RAM/VRAM dù người dùng chưa bấm chạy tính năng AI nào.
- **Nguyên nhân gốc (Root Cause)**:
  1. `import torch` ở cấp độ đầu file (top-level import) trong tệp giao diện chính.
  2. Nhiều Subagent cùng gọi `LocalGPUVisionOCREngine()` trong `__init__`, tạo ra 4–6 bản sao độc lập và chạy vòng lặp khởi tạo tensor/glyph trên CPU/GPU nhiều lần.
- **Quy tắc bắt buộc (Golden Rule)**:
  1. Áp dụng **Singleton Pattern (`__new__`)** cho mọi Engine nặng (GPU, OCR, Database, Model).
  2. Áp dụng **Lazy Initialization (`__getattr__` hoặc `@property`)**: chỉ `import torch` và nạp trọng số vào đúng thời điểm hàm suy luận được gọi lần đầu tiên.

---

### `ERR-007` — Gọi rời rạc hàng chục tiến trình CLI (`N+1 Subprocess Anti-Pattern`)
- **Bối cảnh / Công nghệ**: Android ADB (`adb shell getprop`), Docker CLI, Git CLI, SSH.
- **Triệu chứng (Symptom)**: Quét thông tin 1 thiết bị mất `2s–4s` vì gọi 8 lệnh `adb shell getprop` liên tiếp.
- **Nguyên nhân gốc (Root Cause)**: Chi phí khởi tạo tiến trình (`CreateProcess` trên Windows + bắt tay socket ADB) tốn `150ms–300ms` mỗi lần gọi.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **Gộp lệnh (Command Batching)**: Gộp tất cả các truy vấn đọc thông số vào **1 lệnh shell duy nhất** (ví dụ: `adb shell "getprop ro.product.model; getprop ro.build.version.release; wm size"`) và lưu cache các thuộc tính phần cứng tĩnh theo `serial`.

---

### `ERR-008` — Lỗi `pack(side=LEFT)` chèn ép làm mất nút `pack(side=RIGHT)` trong bố cục giao diện
- **Bối cảnh / Công nghệ**: Tkinter `pack()` geometry manager, Flexbox không có `flex-shrink: 0`.
- **Triệu chứng (Symptom)**: Các nút quan trọng hoặc nhãn `RAM` / `CPU` ở góc phải thanh Header bị cắt cụt chữ khi thanh tìm kiếm ở giữa hoặc bên trái dài ra.
- **Nguyên nhân gốc (Root Cause)**: Trong Tkinter `pack()`, widget nào được `.pack()` trước sẽ được ưu tiên cấp phát không gian trước. Nếu `.pack(side=LEFT, expand=True)` được gọi trước `.pack(side=RIGHT)`, phần tử bên trái sẽ chiếm hết chiều ngang và đẩy phần tử bên phải ra khỏi khung nhìn.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **LUÔN LUÔN** `.pack(side=RIGHT)` các cụm nút điều khiển cố định ở mép phải **TRƯỚC KHI** `.pack(side=LEFT, fill=X, expand=True)` phần tử co giãn ở giữa.

---

### `ERR-009` — Cập nhật lại toàn bộ cây DOM / Widget mỗi chu kỳ тайmer (`Unconditional UI Redraw`)
- **Bối cảnh / Công nghệ**: Dashboard thời gian thực, Tkinter `after()`, React state polling.
- **Triệu chứng (Symptom)**: Giao diện bị nhấp nháy (flicker) và ngốn CPU liên tục mỗi 2 giây, chuyển đổi Theme Sáng/Tối mất `>150ms`.
- **Nguyên nhân gốc (Root Cause)**:
  1. Hàm polling gọi `widget.config()` lại cho mọi thẻ thiết bị mỗi 2 giây dù giá trị `RAM`, `CPU`, `status` không hề thay đổi.
  2. Hàm `apply_theme()` duyệt đệ quy qua cả 12 tab (`~900` widget) dù 11 tab đang ẩn.
- **Quy tắc bắt buộc (Golden Rule)**:
  - **State Diff-Checking**: Lưu chữ ký trạng thái `_ui_state_cache[key] = (status, ram, cpu)` và chỉ gọi `.config()` khi chữ ký mới khác chữ ký cũ.
  - **Active-Tab-Only Rendering**: Chỉ áp dụng style cho khung vỏ (Shell) và tab đang hiển thị; đánh dấu các tab ẩn vào `_dirty_tabs` để áp dụng style ngay khi người dùng chuyển tới tab đó.

---

### `ERR-010` — Lỗi hiển thị ký tự rác (`*`, `+`, `[]`, `?`) khi dùng Emoji phức hợp trên Windows Tkinter / Tcl 8.6
- **Bối cảnh / Công nghệ**: Python Tkinter (Tcl/Tk 8.6), phông chữ `Segoe UI` trên Windows 10/11.
- **Triệu chứng (Symptom)**: Các emoji đa byte có biến thể màu (`🛡️`, `⚙️`, `📱`, `🚀` ngoài mặt phẳng BMP `U+FFFF`) bị hiển thị thành ký tự lỗi `?`, ô vuông `[]`, hoặc bị thay thế tạm bợ bằng dấu `*`, `+` gây rối mắt.
- **Nguyên nhân gốc (Root Cause)**: Bộ dựng phông của Tcl/Tk 8.6 trên Windows chỉ hỗ trợ hoàn hảo các ký tự Unicode nằm trong **Basic Multilingual Plane (BMP, `U+0000` – `U+FFFF`)**.
- **Quy tắc bắt buộc (Golden Rule)**:
  - Chỉ sử dụng các **Geometric BMP Unicode Symbols** thuộc phạm vi `U+2000`–`U+27FF` được hỗ trợ vector 100% trong `Segoe UI`:
    - `●` (`\u25cf` Online) | `○` (`\u25cb` Offline) | `▸` (`\u25b8` Run/Start) | `■` (`\u25a0` Stop)
    - `◐` (`\u25d0` Theme Toggle) | `▾` (`\u25be` Expand) | `▴` (`\u25b4` Collapse) | `→` (`\u2192` Arrow) | `✓` (`\u2713` Check).

---

### `ERR-011` — Thay thế chuỗi hàng loạt (`str.replace`) làm lệch thụt lề (`IndentationError`)
- **Bối cảnh / Công nghệ**: Refactoring tự động bằng Python `str.replace()` hoặc Regex.
- **Triệu chứng (Symptom)**: Lệnh `src.replace("    self.refresh()\n", "")` xóa nhầm lệnh gọi duy nhất bên trong một khối `try:` khiến khối `try:` bị rỗng và gây ra `IndentationError`.
- **Nguyên nhân gốc (Root Cause)**: Thay thế chuỗi diện rộng bằng chuỗi rỗng `""` mà không kiểm tra ngữ cảnh khối lệnh chứa nó.
- **Quy tắc bắt buộc (Golden Rule)**:
  - Khi vô hiệu hóa một lời gọi hàm trên một dòng đơn lẻ bằng script, hãy thay thế bằng `pass` (cùng mức thụt lề) thay vì xóa trắng dòng đó, và luôn chạy `python -m py_compile <file.py>` ngay sau khi sửa.

---

### `ERR-012` — Rác tệp trạng thái (`config/*.json`, `reports/*.md`) bị ghi bẩn khi chạy Unit Test / E2E Test
- **Bối cảnh / Công nghệ**: Pytest, kiểm thử tích hợp có ghi file JSON/Markdown.
- **Triệu chứng (Symptom)**: Sau khi chạy `pytest`, `git status` báo hàng loạt tệp `config/*.json` và `reports/*.md` bị thay đổi (`modified`), làm bẩn nhánh làm việc.
- **Nguyên nhân gốc (Root Cause)**: Các bài test gọi trực tiếp vào `MemoryManager()` hoặc `KanbanBoard()` dùng đường dẫn tệp cấu hình thật thay vì `tmp_path` fixture.
- **Quy tắc bắt buộc (Golden Rule)**:
  - Trong bài test, truyền `tmp_path` vào constructor hoặc dùng fixture khôi phục trạng thái, và luôn kiểm tra `git status -s` sạch sẽ trước khi đóng gói commit.
