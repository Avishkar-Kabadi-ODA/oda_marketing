# ODA Marketing

**ODA Marketing Operations Platform** is an enterprise-grade agentic marketing workflow and AI evaluation system built on **Frappe Framework v15**.

---

## Key Features

- **Content Delivery Pipeline**: Complete lifecycle management for Blogs, Polls, Flowcharts, and Carousels.
- **Workflow State Machine**: Streamlined status transitions (`Planned` → `Briefed` → `In Progress` → `Marketing Copilot Review` → `In Review - Technical` → `In Revision` → `Approved` → `Published`).
- **AI Copilot Gatekeeper & Subagent**:
  - Configurable AI Copilot Review with dynamic prompt generation subagent.
  - Gatekeeper score thresholding (e.g. 80%) enforcing quality sign-off before technical review.
  - Conditionally enabled/disabled under **Marketing Settings**.
- **Role-Based Access Control**: Strict permissions for `Marketing Lead`, `Content Writer`, `Technical Reviewer`, and `System Manager`.
- **Targeted Notification Engine**:
  - HTML email notifications with direct Desk action buttons ("View Content Item in Desk").
  - Frappe In-App Bell 🔔 notifications sent to assigned users.
- **Frappe Desk & Docker Integration**: Standard `desktop.py` module registration and `frappe_docker` compatibility.

---

## Installation Guide

### 1. Install App on Bench

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Avishkar-Kabadi-ODA/oda_marketing.git --branch main
bench --site your.site.name install-app oda_marketing
```

### 2. Run Production Setup

Run the setup fixture to initialize roles, email templates, workflow state machine, kanban pipeline, and desktop icons:

```bash
bench --site your.site.name execute oda_marketing.setup_fixtures.run_setup
```

*(Note: Production setup initializes all master switches to `0` (disabled) and creates zero dummy content items.)*

---

## Configuration & Production Setup

### Marketing Settings

Navigate to **Desk → ODA Marketing → Marketing Settings**:

1. **Master Switches**:
   - **Enable Email Notifications**: Master toggle for email delivery.
   - **Enable Automatic Overdue Risk Flagging**: Toggles automatic SLA due date tracking.
   - **Enable AI Copilot Automated Review & Gatekeeper**: Enables the AI evaluation engine and quality gatekeeper.

2. **AI Copilot Configuration** *(visible & mandatory when Enable AI Copilot is checked)*:
   - **Minimum Passing Score (%)**: Threshold (e.g. `80`) required to advance to Technical Review.
   - **AI LLM Provider / Architecture**: Provider (e.g. APIM Gateway, OpenAI, Google Gemini).
   - **API Key / Subscription Key (Env Variable)**: Select stored key from **Env Variable** DocType.
   - **APIM / Endpoint URL (Env Variable)**: Select stored endpoint from **Env Variable** DocType.
   - **Model Name**: Target model (e.g. `gpt-4o`, `gemini-1.5-pro`).
   - **Prompt Templates**: Customizable Jinja2 subagent meta-prompt and evaluator rubric templates.

---

## Workflow & State Machine

```
Planned → Issue Brief → Briefed → Accept Brief → In Progress
                                                       ↓
                                             Submit for Copilot Review
                                                       ↓
                                            Marketing Copilot Review
                                              ↙                 ↘
                           Score ≥ 80% (Pass)                 Score < 80% (Fail)
                                 ↓                                   ↓
                       In Review - Technical                    In Revision
                                 ↓                                   ↓
                          Approve Technical                   Resubmit Draft
                                 ↓                                   ↓
                              Approved                     Marketing Copilot Review
                                 ↓
                              Publish
                                 ↓
                             Published
```

*Note: If **Enable AI Copilot** is disabled in Marketing Settings, the AI evaluation section is hidden, and items advance directly to Technical Review.*

---

## Running Unit Tests

Run the automated test suite on your bench site:

```bash
bench --site marketing.localhost run-tests --app oda_marketing
```

---

## Architecture Documentation

- [System Architecture & Operational Flow](file:///home/user/frappe-bench/apps/oda_marketing/app-architecture-and-flow.md)
- [Development Guide](file:///home/user/frappe-bench/apps/oda_marketing/development-guide.md)

---

## License

MIT License - Optimum Data Analytics (ODA)
