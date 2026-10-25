# Cross-App Notetaker Subagent (Subagent #13)

**Branch:** `feat/cross-app-notetaker`  
**Module:** `agents/cross_app_notetaker_subagent.py`  
**Persistence Store:** `config/cross_app_notes.json`  
**Inspiration:** Mobile-Agent-E & Google DeepMind AndroidWorld

---

## Overview

`CrossAppNotetakerSubagent` (Subagent #13) provides a persistent, thread-safe cross-application state ledger for multi-app and multi-device Android automation workflows. When executing end-to-end tasks that span multiple apps (e.g., requesting an OTP in a banking app, reading SMS/notification or email, copying an order reference ID, and pasting it into a support form), `CrossAppNotetakerSubagent` automatically extracts, persists, and resolves dynamic values.

## Key Capabilities

1. **Structured Ledger & Atomic Persistence (`record_note`, `get_note`, `get_all_notes`)**
   - Maintains an in-memory `notes_ledger` dictionary synchronized with `config/cross_app_notes.json` and `MemoryManager`.
   - Tracks `key`, `value`, `source_app`, `serial`, `timestamp`, and `metadata`.

2. **Automatic Screen UI Hierarchy Extraction (`extract_notes_from_screen`)**
   - Dumps the live UIAutomator XML via `ADBWrapper.dump_ui_hierarchy(serial)` and inspects `text` and `content-desc` attributes across all nodes.
   - Automatically recognizes and records:
     - **6-digit OTP codes** (`\b\d{6}\b`) $\rightarrow$ `otp_code`
     - **Order / Transaction IDs** (`(?:ORD|TXN|INV|ID)[-_#]?[A-Z0-9]{4,12}`) $\rightarrow$ `order_id`
     - **Deep links / URLs** (`https?://[^\s"<>]+|[a-z0-9_]+://[^\s"<>]+`) $\rightarrow$ `extracted_url`
     - **Currency / Price totals** (`(?:\$|₫|VND|USD)\s?[\d,.]+|[\d,.]+\s?(?:VND|₫|USD)`) $\rightarrow$ `price_amount`

3. **System Notification & Clipboard Bridging (`extract_from_notifications_and_clipboard`)**
   - Queries `cmd clipboard get-text` and `dumpsys notification --noredact` via ADB shell to capture background OTP codes and verification URLs without leaving the active foreground application.

4. **Dynamic Template Resolution (`resolve_template`)**
   - Substitutes `$NOTE:<key>` and `${NOTE:<key>}` tokens in operator action payloads or input strings with live values from `notes_ledger`.

## Usage Example

```python
from agents.cross_app_notetaker_subagent import CrossAppNotetakerSubagent

notetaker = CrossAppNotetakerSubagent()

# Extract OTP or Order ID from current screen
result = notetaker.extract_notes_from_screen("emulator-5554", source_app="com.google.android.apps.messaging")

# Or extract directly from Android notifications & clipboard
notetaker.extract_from_notifications_and_clipboard("emulator-5554")

# Resolve placeholders in action templates
resolved_text = notetaker.resolve_template("Verify code $NOTE:otp_code for order ${NOTE:order_id}")
```
