# Báo Cáo Kiểm Tra An Ninh Mobile (OWASP Mobile Security Report)

- **Gói ứng dụng (Package):** `com.android.settings`
- **Thiết bị kiểm thử:** `emulator-5554`
- **Thời gian thực hiện:** `2026-10-24 21:35:25`
- **Số lượng lỗ hổng phát hiện:** `2`

---

## 1. Bảng Tổng Hợp Lỗ Hổng

| Mã OWASP | Mức độ | Tiêu đề lỗ hổng | Giải pháp khắc phục |
| :--- | :--- | :--- | :--- |
| **M2: Insecure Data Storage** | `MEDIUM` | Application allows ADB Backup (android:allowBackup='true') | Set android:allowBackup='false' in AndroidManifest.xml unless specifically required. |
| **M1: Improper Platform Usage** | `HIGH` | Discovered 373 exposed exported Activities/Receivers without explicit permissions | Set android:exported='false' for internal activities, or guard with custom signature-level permissions. |

---

## 2. Chi Tiết Khuyến Nghị Kỹ Thuật

### 1. Application allows ADB Backup (android:allowBackup='true') (MEDIUM)
- **Phân loại:** M2: Insecure Data Storage
- **Nguy cơ:** App data can be backed up via 'adb backup', allowing local access to SharedPreferences, SQLite databases, and user tokens.
- **Khắc phục:** `Set android:allowBackup='false' in AndroidManifest.xml unless specifically required.`

### 2. Discovered 373 exposed exported Activities/Receivers without explicit permissions (HIGH)
- **Phân loại:** M1: Improper Platform Usage
- **Nguy cơ:** Third-party rogue applications can trigger internal activities or send malicious intents directly.
- **Khắc phục:** `Set android:exported='false' for internal activities, or guard with custom signature-level permissions.`

