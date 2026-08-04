# Google Sheet Data Mapping Specification

This document specifies the exact cell coordinates, layout structure, data types, and access permissions (Read/Write) for the Google Sheet configuration and log matrix.

---

## 1. Core Structural Rules & Conventions

* **Global Merged Rows (Rows 1–3, 13):** Data values are stored in and retrieved from **Column B** (the primary cell for the merged horizontal range `B:F`).
* **Platform Column Indexing:**
  * **Column B:** Facebook
  * **Column C:** Instagram
  * **Column D:** YouTube
  * **Column E:** TikTok
  * **Column F:** LinkedIn
* **Cell Fills / Roles:**
  * **Yellow Fill (`Input / Read`):** Configuration settings set by the user. The AI system **MUST ONLY READ** these cells.
  * **White Fill (`Output / Write`):** Dynamic runtime logs and system state. The AI system **WRITES / UPDATES** these cells.

---

## 2. Row Definition Matrix

| Row | Label / Metric (Column A) | Target Cell Coordinates | Role / Action | Data Type & Format | Description & Business Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | System Status | `B1` | **Input (Read)** | String | Global system state (`🔴 Stop` / `🟢 Start`). If `Stop`, halt all executions. |
| **2** | Overall Budget ($) | `B2` | **Input (Read)** | Integer / Float | Maximum daily spending limit across all active platforms combined. |
| **3** | Today's Remaining Overall Budget | `B3` | **Output (Write)** | Float / Number | Calculated remaining global daily budget. Updated after job execution. |
| **4** | Platform Header | `B4:F4` | **Input (Read)** | String | Social media platform names (`Facebook`, `Instagram`, `YouTube`, `TikTok`, `LinkedIn`). |
| **5** | Platform Status | `B5:F5` | **Input (Read)** | String | Individual platform switch (`🔴 Stop` / `🟢 Start`). |
| **6** | Platform Keywords | `B6:F6` | **Input (Read)** | String | Search terms/hashtags (e.g., `เอไอเอ,AIA,#AIA`). |
| **7** | Platform Time Filter | `B7:F7` | **Input (Read)** | Enum / Integer | Time window scope: `1` = Day, `2` = Week, `3` = Month. |
| **8** | Interval (Minutes) | `B8:F8` | **Input (Read)** | Integer | Execution cadence in minutes (e.g., `60`, `120`). |
| **9** | Last Execution | `B9:F9` | **Output (Write)** | Timestamp | Per-platform timestamp of last scrape (`YYYY-MM-DD HH:MM:SS`). Blank = scrape immediately. |
| **10** | Max Results | `B10:F10` | **Input (Read)** | Integer | Max items/posts to fetch per platform search. |
| **11** | Platform Budget / Day | `B11:F11` | **Input (Read)** | Float / Null | Platform-specific daily budget cap. If **Blank/Null**, fallback to `Overall Budget` (`B2`). |
| **12** | Today's Remaining Platform Budget | `B12:F12` | **Output (Write)** | Float / Null | Platform-specific remaining budget. Updated post-run. |
| **13** | Last Reset Date | `B13` | **Output (Write)** | Timestamp | Timestamp when daily budgets were last reset (`YYYY-MM-DD HH:MM:SS`). |

---

## 3. Explicit Cell Index Quick Reference

### Global Coordinates (Merged Rows)
* **System Control:**
  * System Status: `B1`
  * Overall Budget: `B2`
  * Today's Remaining Overall Budget: `B3`
* **System Output Logs:**
  * Last Reset Date: `B13`

### Platform Specific Matrix (`B` to `F`)
* **Facebook (`Column B`):** Status `B5` | Keywords `B6` | Time Filter `B7` | Interval `B8` | Last Exec `B9` | Max Results `B10` | Budget `B11` | Remaining `B12`
* **Instagram (`Column C`):** Status `C5` | Keywords `C6` | Time Filter `C7` | Interval `C8` | Last Exec `C9` | Max Results `C10` | Budget `C11` | Remaining `C12`
* **YouTube (`Column D`):** Status `D5` | Keywords `D6` | Time Filter `D7` | Interval `D8` | Last Exec `D9` | Max Results `D10` | Budget `D11` | Remaining `D12`
* **TikTok (`Column E`):** Status `E5` | Keywords `E6` | Time Filter `E7` | Interval `E8` | Last Exec `E9` | Max Results `E10` | Budget `E11` | Remaining `E12`
* **LinkedIn (`Column F`):** Status `F5` | Keywords `F6` | Time Filter `F7` | Interval `F8` | Last Exec `F9` | Max Results `F10` | Budget `F11` | Remaining `F12`
