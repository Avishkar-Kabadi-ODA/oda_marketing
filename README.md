# ODA Marketing

**ODA Marketing Operations Platform** is an enterprise-grade agentic marketing workflow and AI evaluation system built on **Frappe Framework v16**.

---

## Key Features

- **Content Delivery Pipeline**: Lifecycle management for Blogs, Polls, Flowcharts, Carousels, and custom content formats.
- **Dynamic Option Management (`Content Item Option`)**: Decoupled dropdown options for Format (`content_type`) and Practice Area (`practice_area`) into a dedicated setup DocType with soft-disable (`is_active`) and custom sorting (`sort_order`).
- **Streamlined Workflow State Machine**: Simplified workflow transitions (`Planned` → `Briefed` → `In Progress` → `In Review` → `Approved` → `Published`), featuring an optional `Marketing Copilot Review` state.
- **Informational AI Copilot Engine**:
  - Optional AI evaluation with dynamic prompt generation subagent.
  - Non-blocking quality scoring: AI score is purely informational and no longer blocks workflow state transitions.
  - Reviewer-triggered Copilot reviews with custom instruction inputs.
  - Server-side usage limits enforced via `max_copilot_reviews_per_item` setting in **Marketing Settings**.
- **Flexible Due Date & SLA Reminder Engine**:
  - Manually entered `sla_due_date` (**Due Date**), editable by both Marketing Leads and Content Writers.
  - Configurable SLA reminder alerts (`sla_reminder_enabled`, `sla_reminder_days_before`) sent prior to due dates.
- **Role-Based Access Control & Safeguards**:
  - Strict permissions for `Marketing Lead`, `Content Writer`, `Technical Reviewer`, and `System Manager`.
  - Read-only protection for Content Writers on draft attachments and notes prior to `Briefed` state.
  - Mandatory validation safeguards for primary draft attachment (`content_file_1`), assigned Reviewer, revision feedback notes, and live published URL.
- **Targeted Notification Engine**:
  - HTML email notifications with direct Desk action buttons ("View Content Item in Desk").
  - Frappe In-App Bell 🔔 notifications delivered directly to assigned users.
- **Clean Desk UI & Action Segregation**:
  - Disambiguated action menus: calendar navigation grouped under `Navigate` to avoid duplication with Frappe workflow `Actions`.

---

## Installation Guide

### 1. Install App on Bench

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Avishkar-Kabadi-ODA/oda_marketing.git --branch main
bench --site your.site.name install-app oda_marketing
```

### 2. Run Production Setup

Run the setup fixture to initialize roles, default options, email templates, workflow state machine, kanban pipeline, workspace sidebar, and desktop icons:

```bash
bench --site your.site.name execute oda_marketing.setup_fixtures.run_setup
```

*(Note: Production setup initializes all master switches to `0` (disabled) and creates zero dummy content items.)*

---

## Configuration & Operational Defaults

### Marketing Settings

Navigate to **Desk → ODA Marketing → Marketing Settings**:

1. **Master Switches & Operational Defaults**:
   - **Enable Email Notifications**: Master toggle for email delivery (default: `0`).
   - **Enable Automatic Overdue Risk Flagging**: Toggles automatic SLA due date tracking (default: `0`).
   - **Default SLA Lead Time (Days)**: Lead time reference setting in days (default: `14`).
   - **Default Publisher**: Default Marketing Lead / Publisher user.

2. **Due Date Reminder Configuration**:
   - **Enable Due Date Reminder Notifications**: Enable upcoming SLA due date alerts.
   - **Reminder Days Before Due Date**: Days prior to due date to send reminder alerts (default: `3`).

3. **AI Copilot Configuration** *(visible & configurable when Enable AI Copilot is checked)*:
   - **Enable AI Copilot Automated Review**: Toggles the AI evaluation engine (default: `0`).
   - **Minimum Passing Score (%)**: Quality benchmark reference score (default: `80`).
   - **Max Copilot Reviews per Item**: Maximum allowed AI evaluation runs per Content Item (default: `3`).
   - **AI LLM Provider / Architecture**: Provider architecture (`APIM Gateway`, `OpenAI`, `Google Gemini`, `Anthropic`, `Custom`).
   - **API Key / Subscription Key (Env Variable)**: Select stored key from **Env Variable** DocType.
   - **APIM / Endpoint URL (Env Variable)**: Select stored endpoint from **Env Variable** DocType.
   - **Model Name**: Target model (e.g. `gpt-4o`, `gemini-1.5-pro`).
   - **Prompt Templates**: Customizable subagent meta-prompt and evaluator rubric templates.

---

## Workflow & State Machine

```
                              Planned
                                 │
                                 ▼ (Issue Brief)
                              Briefed
                                 │
                                 ▼ (Start Work) [stamps brief_accepted_on]
                            In Progress
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼ (Run Copilot Review)                      ▼ (Submit for Review)
Marketing Copilot Review                               │
           │                                           │
           └─────────────────────┬─────────────────────┘
                                 │
                                 ▼
                             In Review
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼ (Request Changes)                         ▼ (Approve)
      In Revision                                  Approved
           │                                           │
           ▼ (Resubmit Draft)                          ▼ (Publish)
      In Progress                                  Published
```

---

## Running Unit Tests

Run the automated test suite on your bench site:

```bash
bench --site marketing.localhost run-tests --app oda_marketing
```

---

## Architecture & Documentation

- [System Architecture & Operational Flow](file:///home/user/frappe-bench/apps/oda_marketing/app-architecture-and-flow.md)
- [Development Guide](file:///home/user/frappe-bench/apps/oda_marketing/development-guide.md)

---

## License

MIT License - Optimum Data Analytics (ODA)
