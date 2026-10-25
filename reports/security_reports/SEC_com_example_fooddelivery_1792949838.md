# Báo Cáo Kiểm Tra An Ninh Mobile (OWASP Mobile Security Report)

- **Gói ứng dụng (Package):** `com.example.fooddelivery`
- **Thiết bị kiểm thử:** `emulator-5554`
- **Thời gian thực hiện:** `2026-10-26 00:37:17`
- **Số lượng lỗ hổng phát hiện:** `2`

---

## 1. Bảng Tổng Hợp Lỗ Hổng

| Mã OWASP | Mức độ | Tiêu đề lỗ hổng | Giải pháp khắc phục |
| :--- | :--- | :--- | :--- |
| **M7: Client Code Quality** | `HIGH` | Application has DEBUGGABLE flag enabled | Set android:debuggable='false' in release AndroidManifest.xml and ProGuard rules. |
| **M2: Insecure Data Storage** | `MEDIUM` | Application allows ADB Backup (android:allowBackup='true') | Set android:allowBackup='false' in AndroidManifest.xml unless specifically required. |

---

## 2. Chi Tiết Khuyến Nghị Kỹ Thuật

### 1. Application has DEBUGGABLE flag enabled (HIGH)
- **Phân loại:** M7: Client Code Quality
- **Nguy cơ:** The app was compiled in debug mode. Attackers can attach a JDWP debugger, extract memory strings, and bypass runtime security controls.
- **Khắc phục:** `Set android:debuggable='false' in release AndroidManifest.xml and ProGuard rules.`

### 2. Application allows ADB Backup (android:allowBackup='true') (MEDIUM)
- **Phân loại:** M2: Insecure Data Storage
- **Nguy cơ:** App data can be backed up via 'adb backup', allowing local access to SharedPreferences, SQLite databases, and user tokens.
- **Khắc phục:** `Set android:allowBackup='false' in AndroidManifest.xml unless specifically required.`

