# ODA Marketing — Suggestions & Findings

A comprehensive audit of inconsistencies, potential bugs, dead code, and improvement opportunities across the codebase.

---

## 🔴 Bugs & Issues

### 1. `enable_auto_overdue_flag` Setting Exists But Does Nothing
- **Where**: `marketing_settings.json` (L49-54), `content_item.py` (L163-166)
- **Issue**: The `Enable Automatic Overdue Risk Flagging` checkbox exists in Marketing Settings, but `check_overdue_sla()` in `content_item.py` **unconditionally** sets `risk_flag = "Late"` without checking this setting.
- **Impact**: The toggle is misleading — it suggests the behavior can be disabled, but it cannot.
- **Fix**: Either check `settings.enable_auto_overdue_flag` before setting `risk_flag = "Late"`, or remove the setting entirely.

---

### 2. `business_hours_end` Field Exists But Is No Longer Used
- **Where**: `marketing_settings.json` (L96-101), `content_item.py` (L396-401)
- **Issue**: `business_hours_end` field exists in the schema and settings UI, but `send_overdue_sla_notifications()` only checks `current_hour != start_hour`. The end hour is never referenced in code.
- **Impact**: Users see and can configure an "end hour" that has no effect. Misleading UI.
- **Fix**: Either remove `business_hours_end` from the schema, or update the scheduled job to check the full range.

---

### 3. Overdue Emails Send Repeatedly Every Day (No Deduplication)
- **Where**: `content_item.py` (L409-440)
- **Issue**: Overdue items with `risk_flag = "Late"` get a new email **every single day** at 9 AM because there is no tracking of "already notified." If an item stays overdue for 30 days, the writer/reviewer gets 30 identical emails.
- **Impact**: Email spam for long-overdue items.
- **Fix**: Add a `last_overdue_notified_on` Date field to Content Item. Only send if `last_overdue_notified_on != today`. Alternatively, send overdue alerts only once, or make the frequency configurable (e.g., weekly).

---

### 4. `runner.py` Writes AI Fields Twice (Redundant)
- **Where**: `runner.py` (L63-66) and (L85-90)
- **Issue**: Lines 63–66 set `doc.ai_score`, `doc.ai_review_status`, etc. on the Python object. Lines 85–90 then call `doc.db_set()` with the same values. Then line 95 calls `doc.save()`. The `db_set` is redundant since `save()` will persist the in-memory values anyway.
- **Impact**: Extra unnecessary database writes.
- **Fix**: Remove the `doc.db_set({...})` block (lines 85–90) — `doc.save()` on line 95 already persists everything.

---

### 5. Anthropic Provider Configured in `key_manager.py` But Not Implemented in `evaluator_agent.py`
- **Where**: `key_manager.py` (L88-95), `evaluator_agent.py` (L56)
- **Issue**: `key_manager.py` returns Anthropic config, and `marketing_settings.json` lists "Anthropic" as a provider option, but `evaluator_agent.py` only handles `APIM Gateway`, `OpenAI`, and `Google Gemini`. If a user selects Anthropic, it silently falls through to the heuristic mock evaluator.
- **Impact**: Users expect Anthropic to work but get mock results instead with no error message.
- **Fix**: Either implement Anthropic's Messages API in `evaluator_agent.py` and `prompt_subagent.py`, or remove "Anthropic" from the provider Select options.

---

## 🟡 Schema & Field Name Refinements (Align DB Columns to UI Labels)

### 6. Rename DB Column `practice_area` → `industry_domain`
- **Where**: `content_item.json` (L86-92), `content_item.py`, `content_item.js`, AI engine prompts
- **Issue**: The UI label displays "Industry Domain", but the internal fieldname/table column is still `practice_area`.
- **Fix**: Perform a schema migration to update the fieldname from `practice_area` to `industry_domain` so Python, JS, API payloads, and database columns match the UI label.

---

### 7. Rename DB Column `topic` → `description`
- **Where**: `content_item.json` (L78-84), `content_item.py`, `content_item.js`, AI engine prompts
- **Issue**: The UI label displays "Description", but the internal fieldname/table column is still `topic`.
- **Fix**: Perform a schema migration to update the fieldname from `topic` to `description` so fieldnames match the UI label.

---

### 8. Rename DB Column `sla_due_date` → `due_date`
- **Where**: `content_item.json` (L155-161), `content_item.py`, `content_item.js`
- **Issue**: The UI label displays "Due Date", but the internal fieldname/table column is still `sla_due_date` (legacy prefix).
- **Fix**: Rename the fieldname to `due_date` to remove the legacy `sla_` prefix and match the UI label.

---

### 9. Rename Field `overdue_sla_email_template` → `overdue_email_template`
- **Where**: `marketing_settings.json` (L136), `setup_fixtures.py` (L195)
- **Issue**: The fieldname still contains `sla` (`overdue_sla_email_template`) but the template name and label are "Marketing Overdue Alert" / "Overdue Alert Template".
- **Fix**: Rename the fieldname to `overdue_email_template`.

---

### 10. Hardcoded Default `3` for Max Review Limits in Python, But Schema Default is `2`
- **Where**: `marketing_settings.json` (L161: default `"2"`), `runner.py` (L27-30: fallback `3`), `content_item.py` (L531: fallback `3`)
- **Issue**: The JSON schema default is `2`, but all Python fallback values use `3`. If the setting is somehow blank, Python defaults differ from the UI.
- **Fix**: Align all Python `or 3` fallbacks to `or 2` to match the schema.

---

## 🟢 Improvements & Suggestions

### 11. `setup_fixtures.py` Runs on Every Migration (`after_migrate`)
- **Where**: `hooks.py` (L43)
- **Issue**: `run_setup()` executes on every `bench migrate`, which deletes and recreates the Workflow, Kanban Board, and Workspace Sidebar on every migration. This also resets Marketing Settings defaults.
- **Impact**: Any manual customizations to the workflow, kanban board, or sidebar are lost on every migration. Settings like `enable_ai_copilot`, `ai_provider` etc. may be overwritten.
- **Fix**: Use idempotent checks (only create if not exists, never delete+recreate). Or move the `after_migrate` hook to only handle schema updates and leave fixtures to `after_install` only.

### 12. No Validation on `business_hours_start` Range
- **Where**: `marketing_settings.py` (L11-14)
- **Issue**: A user could set `business_hours_start = 25` or a negative number. No range validation (0–23) exists.
- **Fix**: Add `if not (0 <= self.business_hours_start <= 23): frappe.throw(...)`.

### 13. `run_ai_review` Runs Synchronously (Not Enqueued)
- **Where**: `runner.py` (L10), `content_item.py` (L540)
- **Issue**: The docstring says "Background job orchestrator (frappe.enqueue)" but `run_ai_review()` is called directly without `frappe.enqueue()`. The HTTP request to the LLM blocks the user's request for 10–60 seconds.
- **Impact**: User sees a spinner until the LLM responds. With a 60-second timeout, this can cause Gunicorn worker timeouts in production.
- **Fix**: Use `frappe.enqueue("oda_marketing.oda_marketing.ai_engine.runner.run_ai_review", ...)` for true background execution. The realtime streaming socket events are already set up to push updates.

### 14. Debug Print Statements Left in Production Code
- **Where**: `runner.py` (L100-101), `evaluator_agent.py` (L85-88)
- **Issue**: `print("="*40)` and `print("DEBUG OpenAI JSON Response:")` statements are left in production code.
- **Fix**: Remove all debug `print()` statements. Use `frappe.logger().debug()` instead (which is already done on line 84).

### 15. No `frappe.db.commit()` After `send_overdue_sla_notifications` Completes
- **Where**: `content_item.py` (L390-503)
- **Issue**: The scheduled job sends emails via `frappe.sendmail(now=True)` but never calls `frappe.db.commit()` at the end. If the Frappe scheduler auto-commits, this is fine, but explicit commit is safer.
- **Fix**: Add `frappe.db.commit()` at the end of the function.

### 16. `content_file_1` in `column_break_2` Section — Layout Oddity
- **Where**: `content_item.json` field_order (L7-40)
- **Issue**: The field order places `content_file_1`, `content_file_2`, `content_file_3` under "Content Drafts & Attachments" section, then `column_break_2`, then `sla_due_date`, reminders, `risk_flag`, etc. This means the right column of "Content Drafts" contains the due date and risk status, which are logically unrelated.
- **Fix**: Move due date, reminders, and risk flag fields to the main metadata section (top half) instead of nesting them inside the "Content Drafts & Attachments" section.

### 17. Missing `"Custom"` Provider Handler
- **Where**: `marketing_settings.json` (L183)
- **Issue**: "Custom" is listed as a provider option but there's no handler for it in `evaluator_agent.py` or `prompt_subagent.py`. Selecting it falls through to the heuristic mock evaluator.
- **Fix**: Either remove "Custom" from options, or add documentation explaining that "Custom" expects a specific endpoint format.

### 18. Dedicated Reminder Email Template
- **Where**: `content_item.py` (L491-494)
- **Issue**: Due date reminder emails reuse the Overdue Alert template body (`tmpl.response`) but override the subject with a custom `[REMINDER]` prefix. The template body says "URGENT ESCALATION ALERT" and "has passed its Due Date" which is misleading for a pre-due-date reminder.
- **Fix**: Create a separate "Marketing Due Date Reminder" template with appropriate reminder wording.

---

## Summary

| Category | Count |
|----------|:-----:|
| 🔴 Bugs & Issues | 5 |
| 🟡 Schema & Field Name Refinements | 5 |
| 🟢 Improvements | 8 |
| **Total** | **18** |
