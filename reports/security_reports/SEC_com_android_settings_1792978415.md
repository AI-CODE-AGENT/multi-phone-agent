# Báo Cáo Kiểm Tra An Ninh Mobile (OWASP Mobile Security Report)

- **Gói ứng dụng (Package):** `com.android.settings`
- **Thiết bị kiểm thử:** `10CF5L0TYL00312`
- **Thời gian thực hiện:** `2026-10-26 08:33:35`
- **Số lượng lỗ hổng phát hiện:** `1`

---

## 1. Bảng Tổng Hợp Lỗ Hổng

| Mã OWASP | Mức độ | Tiêu đề lỗ hổng | Giải pháp khắc phục |
| :--- | :--- | :--- | :--- |
| **M1: Improper Platform Usage** | `HIGH` | Discovered 592 exposed exported Activities/Receivers without explicit permissions | Set android:exported='false' for internal activities, or guard with custom signature-level permissions. |

---

## 2. Chi Tiết Khuyến Nghị Kỹ Thuật

### 1. Discovered 592 exposed exported Activities/Receivers without explicit permissions (HIGH)
- **Phân loại:** M1: Improper Platform Usage
- **Nguy cơ:** Third-party rogue applications can trigger internal activities or send malicious intents directly.
- **Khắc phục:** `Set android:exported='false' for internal activities, or guard with custom signature-level permissions.`

