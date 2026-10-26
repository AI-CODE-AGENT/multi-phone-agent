# Real Device E2E Verification & Benchmark Report (`10CF5L0TYL00312`)

- **Status**: `E2E_BENCHMARK_COMPLETED`
- **Target Device Serial**: `10CF5L0TYL00312`
- **Target Package**: `com.android.chrome`
- **Stages Passed**: `8 / 8`
- **Total Benchmark Score**: `99.94 / 100`
- **Final Grade**: **`S+`**
- **Total Duration**: `2489.46 ms`
- **Timestamp**: `2026-10-26 07:03:30`

## 8-Stage Verification Summary

| # | Stage Name | Status | Score | Duration (ms) |
|---|------------|--------|-------|---------------|
| 1 | `STAGE_1_HARDWARE_AND_OEM_GUARD` | **PASS** | `100.0` | `802.52` |
| 2 | `STAGE_2_SOM_VISUAL_PERCEPTION` | **PASS** | `100.0` | `720.84` |
| 3 | `STAGE_3_CONCENTRIC_ROTATION_CAPTCHA_CV` | **PASS** | `100.0` | `478.77` |
| 4 | `STAGE_4_MULTI_IMAGE_GRID_CAPTCHA_CV` | **PASS** | `100.0` | `418.79` |
| 5 | `STAGE_5_UNIVERSAL_7MODE_2FA` | **PASS** | `100.0` | `16.73` |
| 6 | `STAGE_6_WCAG_CONTRAST_AND_TALKBACK` | **PASS** | `100.0` | `21.78` |
| 7 | `STAGE_7_CRASH_TOMBSTONE_ANR_HEALTH` | **PASS** | `100.0` | `0.91` |
| 8 | `STAGE_8_NETWORK_API_AND_FPS_PROFILING` | **PASS** | `99.5` | `28.88` |

## Stage-by-Stage Telemetry Details

### 1. `STAGE_1_HARDWARE_AND_OEM_GUARD`
- **serial**: `10CF5L0TYL00312`
- **manufacturer**: `vivo`
- **model**: `V2417A`
- **resolution**: `1260x2800`
- **width**: `1260`
- **height**: `2800`
- **density_dpi**: `560`
- **oem_guard_status**: `NO_POPUP_DETECTED`

### 2. `STAGE_2_SOM_VISUAL_PERCEPTION`
- **status**: `SCREENSHOT_CAPTURED`
- **marks_count**: `17`
- **screenshot_path**: `D:\Project\multi-phone-agent\reports\screenshots\screen_10CF5L0TYL00312_e2e_stage2_som_1792973008752.png`
- **annotated_screenshot_path**: `D:\Project\multi-phone-agent\reports\screenshots\som_10CF5L0TYL00312_1792973009387.png`
- **mean_brightness**: `71.515`

### 3. `STAGE_3_CONCENTRIC_ROTATION_CAPTCHA_CV`
- **target_angle_deg**: `125`
- **best_angle_deg**: `125`
- **angle_error_deg**: `0`
- **drag_distance_px**: `181`
- **min_seam_error**: `18.181`
- **touch_verification**: `HUMAN_SLIDER_DRAG_OK`

### 4. `STAGE_4_MULTI_IMAGE_GRID_CAPTCHA_CV`
- **grid_3x3_selected**: `[0, 2, 4, 7]`
- **grid_3x3_expected**: `[0, 2, 4, 7]`
- **grid_4x4_selected**: `[1, 5, 10, 14]`
- **grid_4x4_expected**: `[1, 5, 10, 14]`
- **tiles_tapped**: `2`

### 5. `STAGE_5_UNIVERSAL_7MODE_2FA`
- **serial**: `10CF5L0TYL00312`
- **rfc4226_hotp_counter0**: `755224`
- **rfc4226_hotp_counter1**: `287082`
- **rfc6238_totp_59s**: `94287082`
- **totp_window_verified**: `True`
- **otpauth_account_id**: `AMAFBenchmark:vivo_user`
- **otpauth_current_code**: `948262`
- **consumed_backup_code**: `8821-4490`

### 6. `STAGE_6_WCAG_CONTRAST_AND_TALKBACK`
- **wcag_score**: `100.0`
- **wcag_level**: `AAA`
- **nodes_audited**: `2`
- **violations_count**: `0`

### 7. `STAGE_7_CRASH_TOMBSTONE_ANR_HEALTH`
- **status**: `CRASH_ANALYSIS_COMPLETED`
- **total_faults**: `0`
- **unique_signatures**: `0`
- **has_critical_fault**: `False`

### 8. `STAGE_8_NETWORK_API_AND_FPS_PROFILING`
- **api_health_score**: `100.0`
- **performance_score**: `99.0`
- **performance_grade**: `A+`
- **estimated_fps**: `59.7`
- **total_pss_mb**: `66.8`
- **rx_mb**: `8.0`
- **tx_mb**: `3.0`
