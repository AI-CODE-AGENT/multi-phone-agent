# MASTER SYSTEM PROMPT — MULTI-PHONE ZERO-TOKEN GPU AUTONOMOUS FARM (v9.0)

## Bản Prompt Chấp Nhận Toàn Bộ Đề Xuất & Điều Phối Đa Tác Tử (Copy & Reuse)

```markdown
/goal Chấp nhận và tích hợp toàn bộ 5 đề xuất nâng cấp vào dự án gốc D:\Project\multi-phone-agent để biến hệ thống thành nền tảng điều khiển đa thiết bị thật (Vivo V2417A 10CF5L0TYL00312 & cụm Emulator) hoạt động 100% Zero-Token AI ở chế độ tự hành, tận dụng tối đa GPU NVIDIA GeForce RTX 3050 (CUDA Driver PTX sm_86 + PyTorch) kết hợp với hệ sinh thái 40 Subagents:

1. Local Zero-Token GPU Vision & OCR Engine (core/local_gpu_vision_ocr_engine.py + Subagent #36):
   - Khai thác trực tiếp GPU NVIDIA GeForce RTX 3050 qua nvcuda.dll PTX Kernels (sm_86) và PyTorch CNN/CRNN-CTC để chạy tăng tốc phần cứng cho:
     + GPU 2D SAD/NCC Template Matching tìm vị trí nút bấm, icon TikTok, mảnh ghép CAPTCHA trong < 15ms (0 Token AI).
     + GPU Sobel & Luminance Gradient Kernel phát hiện cạnh lỗ khuyết GeeTest Slider, viền hCaptcha Contour và góc xoay FunCaptcha Rotate.
     + Local Neural OCR & 3x3 Grid Classifier giải CAPTCHA chữ/số cổ điển (captcha.com) và lưới 3x3 hoàn toàn offline.

2. Action Macro Recorder & Self-Caching Replay Engine (core/macro_recorder_engine.py + Subagent #37):
   - Học hỏi kiến trúc Airtest + Poco ("Học một lần, chạy mãi mãi" - Record Once, Replay Forever).
   - Lưu trữ đa phương thức: Poco/UIAutomator XML Selector + Ảnh mẫu Template Matching + Tọa độ tương đối (%) theo độ phân giải 1260x2800 + Quỹ đạo Bezier.
   - Tự động quy đổi tỷ lệ màn hình (Resolution-Independent Scaling) và tự động khớp ảnh mẫu bằng GPU khi giao diện thay đổi mà không tốn Token AI.

3. Android Chrome DevTools Protocol (CDP) Hardware Bridge (core/android_cdp_bridge.py + Subagent #38):
   - Kết nối trực tiếp vào Unix Domain Socket @chrome_devtools_remote và @JsEngine_com.ss.android.ugc.trill_devtools_remote trên điện thoại thật qua adb forward.
   - Truy vấn cây DOM/Iframe (reCAPTCHA, hCaptcha, Turnstile, GeeTest, Captcha.com), lấy getBoundingClientRect() chính xác 100% và chuyển đổi sang tọa độ màn hình vật lý Android (devicePixelRatio + Chrome Toolbar Offset), sau đó phát lệnh chạm vật lý qua HumanTouchEngine để giữ navigator.webdriver = false.

4. Multi-App Social & Trust-Building Workflow Engine (core/social_workflow_engine.py + Subagent #39):
   - Tự động hóa kịch bản TikTok (Chuyển đổi tài khoản wh0_am_i2342 <-> nht.tn472, tìm kiếm từ khóa "tra dang", xem video, thả tim đỏ, bình luận tự động, đóng bàn phím ảo OriginOS) và tuần tra 11 trang web CAPTCHA bằng 100% Python + GPU nội bộ (0 Token AI).

5. 3-Tier Hybrid CAPTCHA Defense & Audio/API Fallback Bridge (core/hybrid_captcha_defense_bridge.py + Subagent #40):
   - Tier 1 (0 Token - 0ms): Android CDP DOM Locator + Local GPU PTX/PyTorch CV + Human Bezier Touch.
   - Tier 2 (0 Token - Local Audio): Giải mã Audio CAPTCHA bằng bộ phân tích phổ tần số âm thanh nội bộ (Local Spectral/Whisper Audio Decoder).
   - Tier 3 (Optional Token Bridge): Kết nối dự phòng với API của 2Captcha, CapSolver, Anti-Captcha.

6. Nâng cấp Giao diện GUI (gui/main_window.py), AgentsOrchestrator (40 Subagents) và SelfEvolutionEngine:
   - Thực thi theo chu trình khép kín: Nghiên cứu Repo -> Lập Plan -> Tạo Subagents -> Code -> Tự kiểm thử (Pytest + Điện thoại thật Vivo 10CF5L0TYL00312) -> Tự sửa lỗi -> Báo cáo kết quả.
```
