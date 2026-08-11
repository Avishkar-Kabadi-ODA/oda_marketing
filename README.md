# ODA Marketing

**ODA Marketing Operations Platform** is an enterprise-grade agentic marketing workflow and AI evaluation system built on **Frappe Framework v16**.

---

## Key Features

- **Content Delivery Pipeline**: Lifecycle management for Blogs, Polls, Flowcharts, Carousels, and custom content formats.
- **Dynamic Option Management (`Content Item Option`)**: Decoupled dropdown options for Format (`content_type`) and Practice Area (`practice_area`) into a dedicated setup DocType with soft-disable (`is_active`) and custom sorting (`sort_order`).
- **Streamlined 7-Stage Workflow State Machine**: Pure operational workflow transitions (`Planned` → `Briefed` → `In Progress` → `In Review` → `In Revision` → `Approved` → `Published`).
- **Informational AI Copilot Engine**:
  - Optional AI evaluation with dynamic prompt generation subagent.
  - **Toolbar Action Menu (`Copilot`)**: Triggered directly on-demand without mutating the workflow state.
  - **Prerequisites for Copilot Actions**:
    1. **Primary Content Draft (`content_file_1`)** must be attached.
    2. **AI Copilot** must be enabled in **Marketing Settings**.
    3. The role's review limit must not be exhausted.
  - **Separate AI review limits** for Content Writer (`max_writer_copilot_reviews_per_item`) and Technical Reviewer (`max_reviewer_copilot_reviews_per_item`) roles.
  - Non-blocking quality scoring: AI score is purely informational.
  - Real-time client UI rendering: Updates score and evaluation history immediately without requiring manual page refresh.
  - Reviewer-triggered Copilot reviews with custom instruction inputs.
- **Flexible Due Date & SLA Reminder Engine**:
  - Manually entered `sla_due_date` (**Due Date**), editable by both Marketing Leads and Content Writers.
  - Configurable SLA reminder alerts (`sla_reminder_enabled`, `sla_reminder_days_before`) sent prior to due dates.
- **Role-Based Access Control & Safeguards**:
  - Strict permissions for `Marketing Lead`, `Content Writer`, `Technical Reviewer`, and `System Manager`.
  - Blocked creation (`create: 0`) and deletion (`delete: 0`) rights for Content Writers and Technical Reviewers.
  - Read-only protection for Content Writers on draft attachments and notes prior to `Briefed` state.
  - Server-side validation preventing Technical Reviewers from editing metadata or draft attachments (only `revision_feedback_notes` and `reviewer_copilot_instructions` are editable).
  - Mandatory validation safeguards for primary draft attachment (`content_file_1`), assigned Reviewer, revision feedback notes, and live published URL.
- **Targeted Notification Engine**:
  - HTML email notifications with direct Desk action buttons ("View Content Item in Desk").
  - Frappe In-App Bell 🔔 notifications delivered directly to assigned users.
- **Clean Desk UI & Action Segregation**:
  - Disambiguated action menus: calendar navigation grouped under `Navigate` to avoid duplication with Frappe workflow `Actions`.
  - Role-specific Copilot action buttons: Writer sees "Run AI Copilot Review", Reviewer sees "Run Copilot Review (Reviewer)".
  - Role-isolated AI review history: Writers see only Writer reviews, Reviewers see only Reviewer reviews, Leads see all.

---

## Role-Based Operational Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ODA MARKETING CONTENT PIPELINE                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  MARKETING LEAD  │     │ CONTENT WRITER   │     │ TECHNICAL REVIEWER│
│                  │     │                  │     │                  │
│ • Create Item    │────▶│ • Accept Brief   │────▶│ • Review Draft   │
│ • Assign Writer  │     │ (Start Work)     │     │ • Optional AI    │
│ • Assign Reviewer│     │ • Attach Draft   │     │   Review (Copilot│
│ • Issue Brief    │     │ • Optional AI    │     │   Menu)          │
│ • Publish Final  │     │   Review (Copilot│     │ • Approve /      │
│                  │     │   Menu)          │     │   Request Changes│
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
   Planned ──(Issue Brief)──▶ Briefed ──(Start Work)──▶ In Progress
                                                        │
                                                        ▼
                                               (Submit for Review)
                                                        │
                                                        ▼
                                                   In Review
                                                        │
                                              ┌─────────┴─────────┐
                                              ▼                   ▼
                                      (Request Changes)      (Approve)
                                              │                   │
                                              ▼                   ▼
                                      In Revision ◀──(Resubmit)  Approved
                                              │                   │
                                              └───────────┬───────┘
                                                          ▼
                                                     Published
                                                          │
                                                          ▼
                                                 (Marketing Lead adds
                                                  Published URL)
```

### Step-by-Step Flow

| Step | Role | Action | State Transition | Key Validations & Requirements |
|------|------|--------|------------------|--------------------------------|
| 1 | **Marketing Lead** | Create Content Item | `Planned` | Only Marketing Lead / System Manager can create |
| 2 | **Marketing Lead** | Assign Writer, Reviewer, Calendar, Dates | `Planned` | All metadata editable by Lead |
| 3 | **Marketing Lead** | **Issue Brief** | `Planned` → `Briefed` | Email + In-app notification to Writer |
| 4 | **Content Writer** | **Start Work** (accepts brief) | `Briefed` → `In Progress` | Stamps `brief_accepted_on`; attachments unlocked |
| 5 | **Content Writer** | Attach Primary Draft (`content_file_1`) | `In Progress` | Can edit `sla_due_date`, draft files, notes |
| 6 | **Content Writer** | **Run AI Copilot Review** (optional) | No State Mutation | Requires `content_file_1` attached + Copilot enabled + Count < Writer Limit |
| 7 | **Content Writer** | **Submit for Review** | `In Progress` → `In Review` | Requires `content_file_1` & assigned `reviewer_technical` |
| 8 | **Technical Reviewer** | Review in `In Review` state | `In Review` | Metadata & draft files locked; feedback notes editable |
| 9 | **Technical Reviewer** | **Run Copilot Review (Reviewer)** (optional) | No State Mutation | Requires `content_file_1` attached + Copilot enabled + Count < Reviewer Limit |
| 10 | **Technical Reviewer** | **Approve** OR **Request Changes** | `In Review` → `Approved` / `In Revision` | Request Changes requires mandatory `revision_feedback_notes` |
| 11 | **Content Writer** | **Resubmit Draft** (if changes requested) | `In Revision` → `In Progress` | Loop back to step 5 |
| 12 | **Marketing Lead / Publisher** | Add `published_url` & **Publish** | `Approved` → `Published` | Requires `published_url` |
| 13 | **System** | Auto-notify Writer of publication | `Published` | Email with live URL |

---

## Installation Guide

### Prerequisites
- **Frappe Framework v16+** (Python 3.10+, MariaDB 10.6+, Redis, Node 18+)
- **ERPNext v16+** (optional, for user management integration)
- **frappe-bench** or **frappe_docker** environment

---

### Option A: Installation via frappe-bench (Traditional)

```bash
# 1. Navigate to your bench directory
cd /path/to/frappe-bench

# 2. Get the app (from private repository)
bench get-app https://github.com/your-org/oda_marketing.git --branch main
# OR if using a local path:
# bench get-app /path/to/oda_marketing

# 3. Install on your site
bench --site your-site.local install-app oda_marketing

# 4. Run production setup (creates roles, options, workflow, kanban, workspace, desktop icon)
bench --site your-site.local execute oda_marketing.setup_fixtures.run_setup

# 5. Build assets and restart
bench build
bench restart
```

**Post-Install Steps:**
1. Login as **Administrator**
2. Go to **Desk → ODA Marketing → Marketing Settings**
3. Configure:
   - **Default Publisher** (User who will publish)
   - **Default Content Calendar** (optional)
   - **Email Notifications** (enable + select templates)
   - **AI Copilot** (enable + configure provider, model, API keys via Env Variables)
   - **Writer/Reviewer AI Review Limits** (default: 3 each)
4. Assign **Roles** to users:
   - `Marketing Lead` - Full create/edit/publish access
   - `Content Writer` - Draft creation, AI review, submission
   - `Technical Reviewer` - Review, approve, request changes, AI review
   - `System Manager` - Full administrative access

---

### Option B: Installation via frappe_docker (Production/Containerized)

#### 1. Add to `apps.json` or `apps.txt`

**For custom apps in frappe_docker**, add to your `apps.json`:

```json
[
  {
    "url": "https://github.com/your-org/oda_marketing.git",
    "branch": "main"
  }
]
```

Or in `apps.txt`:
```
https://github.com/your-org/oda_marketing.git main
```

#### 2. Build Custom Image

```bash
# In your frappe_docker directory
docker compose -f docker-compose.yml -f overrides/compose.mariadb.yml build --build-arg APPS_JSON_BASE64=$(cat apps.json | base64 -w0) backend
```

#### 3. Deploy with Docker Compose

```bash
# Start services
docker compose -f docker-compose.yml -f overrides/compose.mariadb.yml up -d

# Run setup inside backend container
docker compose exec backend bench --site your-site.local execute oda_marketing.setup_fixtures.run_setup

# Restart to pick up new assets
docker compose restart backend
```

#### 4. Kubernetes (Helm) Deployment

```yaml
# values.yaml additions for oda_marketing
apps:
  oda_marketing:
    url: "https://github.com/your-org/oda_marketing.git"
    branch: "main"

# Post-install job to run setup
postInstallJobs:
  - name: oda-marketing-setup
    image: "{{ .Values.global.image.repository }}:{{ .Values.global.image.tag }}"
    command: ["bench", "--site", "your-site.local", "execute", "oda_marketing.setup_fixtures.run_setup"]
```

---

### Option C: Development Setup (frappe-bench with hot-reload)

```bash
# 1. Create bench with development config
bench init frappe-bench --frappe-branch version-16 --python python3.10
cd frappe-bench

# 2. Add as local app (symlink for hot-reload)
bench get-app /full/path/to/oda_marketing

# 3. Create site
bench new-site dev.local --admin-password admin --mariadb-root-password root

# 4. Install app
bench --site dev.local install-app oda_marketing

# 5. Run setup
bench --site dev.local execute oda_marketing.setup_fixtures.run_setup

# 6. Start development servers (with file watching)
bench start
# OR separately:
# bench serve --port 8000
# bench watch (in another terminal)
```

---

## Configuration Reference

### Marketing Settings (Single DocType)

Navigate: **Desk → ODA Marketing → Marketing Settings**

| Section | Field | Description | Default |
|---------|-------|-------------|---------|
| **Master Switches** | `enable_email_notifications` | Master email toggle | `0` |
| | `enable_auto_overdue_flag` | Auto-set "Late" risk flag | `0` |
| | `default_sla_lead_days` | Reference SLA lead time | `14` |
| | `default_publisher` | Default Publisher user | - |
| | `default_content_calendar` | Default calendar link | - |
| **Reminders** | `sla_reminder_enabled` | Enable due date reminders | `0` |
| | `sla_reminder_days_before` | Days before due for reminder | `3` |
| **Email Templates** | `writer_email_template` | Writer notification template | - |
| | `reviewer_email_template` | Reviewer notification template | - |
| | `publisher_email_template` | Publisher approval template | - |
| | `published_email_template` | Publication confirmation template | - |
| | `overdue_sla_email_template` | Overdue escalation template | - |
| **AI Copilot** | `enable_ai_copilot` | Enable AI evaluation engine | `0` |
| | `ai_copilot_passing_score` | Quality benchmark score | `80` |
| | `max_writer_copilot_reviews_per_item` | **Writer** AI review limit | `3` |
| | `max_reviewer_copilot_reviews_per_item` | **Reviewer** AI review limit | `3` |
| | `ai_provider` | LLM Provider | `APIM Gateway` |
| | `ai_api_key_var` | API Key (Env Variable link) | - |
| | `ai_endpoint_var` | Endpoint URL (Env Variable link) | - |
| | `ai_model_name` | Model name (e.g. `gpt-4o`) | `gpt-4o` |
| | `subagent_meta_prompt` | Prompt generator template | Built-in |
| | `evaluator_default_prompt` | Evaluator rubric template | Built-in |

### Env Variables (Encrypted Storage)

Navigate: **Desk → ODA Marketing → Env Variables**

Create records for:
- `APIM_SUBSCRIPTION_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` (Password field - encrypted)
- `APIM_GATEWAY_URL` / `OPENAI_BASE_URL` (Data field)
- Reference these in **Marketing Settings** via Link fields

---

## Role Permissions Matrix

| Permission | Marketing Lead | Content Writer | Technical Reviewer | System Manager |
|------------|:--------------:|:--------------:|:------------------:|:--------------:|
| **Create Content Item** | ✅ | ❌ | ❌ | ✅ |
| **Delete Content Item** | ✅ | ❌ | ❌ | ✅ |
| **Edit Metadata** (title, type, topic, calendar, dates, assignments) | ✅ | ❌ | ❌ | ✅ |
| **Edit Due Date (`sla_due_date`)** | ✅ | ✅ | ❌ | ✅ |
| **Edit Attachments/Notes** (after Briefed) | ✅ | ✅ | ❌ | ✅ |
| **Edit Attachments/Notes** (Planned state) | ✅ | ❌ | ❌ | ✅ |
| **Edit Revision Feedback** | ✅ | ❌ | ✅ | ✅ |
| **Edit Reviewer Copilot Instructions** | ✅ | ❌ | ✅ (In Review only) | ✅ |
| **Run Writer AI Copilot** | ✅ | ✅ | ❌ | ✅ |
| **Run Reviewer AI Copilot** | ✅ | ❌ | ✅ | ✅ |
| **Submit for Review** | ✅ | ✅ | ❌ | ✅ |
| **Approve / Request Changes** | ✅ | ❌ | ✅ | ✅ |
| **Publish** | ✅ | ❌ | ❌ | ✅ |
| **View Writer AI Reviews** | ✅ | ✅ (own) | ❌ | ✅ |
| **View Reviewer AI Reviews** | ✅ | ❌ | ✅ (own) | ✅ |

---

## Email Notification Matrix

| Trigger State | Recipient | CC | Template |
|:-------------|:---------|:---|:---------|
| **Briefed** | Writer (`assigned_to`) | Creator (`owner`) | Writer Notification |
| **In Review** | Reviewer (`reviewer_technical`) | Creator, Writer, Publisher | Reviewer Notification |
| **In Revision** | Writer (`assigned_to`) | Creator (`owner`) | Writer Notification |
| **Approved** | Publisher (`default_publisher`) | Creator, Writer | Publisher Notification |
| **Published** | Writer (`assigned_to`) | - | Published Notification |
| **Overdue SLA** | Writer, Reviewer | - | Overdue SLA Alert |
| **Reminder (pre-due)** | Writer, Reviewer | - | Overdue SLA Alert (custom subject) |
| **Writer AI Fail** | Writer (`assigned_to`) | - | Auto-generated |

---

## Running Tests

```bash
# Unit tests
bench --site your-site.local run-tests --app oda_marketing

# Specific test file
bench --site your-site.local run-tests --app oda_marketing --module oda_marketing.tests.test_ai_agent
```

---

## Architecture Documentation

- [System Architecture & Operational Flow](app-architecture-and-flow.md)
- [Development Guide](development-guide.md)

---

## Project Structure

```
oda_marketing/
├── oda_marketing/
│   ├── __init__.py                 # App version
│   ├── hooks.py                    # Frappe hooks (permissions, scheduler, install)
│   ├── permissions.py              # Role-based permission logic
│   ├── desktop.py                  # Desk module definition
│   ├── setup_fixtures.py           # One-time setup (roles, workflow, kanban, etc.)
│   ├── patches/                    # Migration patches (v1_1)
│   │   └── v1_1/
│   │       ├── create_content_item_options.py
│   │       ├── rename_workflow_state_in_review.py
│   │       └── remove_sharepoint_field.py
│   ├── doctype/
│   │   ├── content_item/           # Core deliverable DocType
│   │   ├── content_calendar/       # Master calendar
│   │   ├── content_item_option/    # Dynamic Format/Practice Area options
│   │   ├── content_item_ai_review/ # AI review history (child table)
│   │   ├── marketing_settings/     # Single DocType configuration
│   │   └── env_variable/           # Encrypted secrets storage
│   └── ai_engine/
│       ├── runner.py               # AI review orchestrator
│       ├── evaluator_agent.py      # Primary LLM evaluator
│       ├── prompt_subagent.py      # Dynamic prompt generator
│       ├── file_extractor.py       # Attachment text extraction
│       └── key_manager.py          # Secure credential resolution
├── workspace_sidebar/              # Workspace sidebar definition
├── desktop_icon/                   # Desktop icon definition
├── README.md                       # This file
├── license.txt                     # License
├── app-architecture-and-flow.md    # Architecture documentation
├── development-guide.md            # Development guide
└── setup.py                        # Package metadata
```

---

## License

**Proprietary License - Optimum Data Analytics Private Limited**

Copyright (c) 2026 Optimum Data Analytics Private Limited. All rights reserved.

This software and associated documentation files (the "Software") are the proprietary property of Optimum Data Analytics Private Limited ("ODA"). The Software is licensed, not sold, and is protected by copyright laws and international treaty provisions.

### License Grant
Subject to the terms of this Agreement, ODA grants you a limited, non-exclusive, non-transferable, revocable license to:
- Use the Software internally within your organization
- Modify the Software solely for internal business purposes
- Create derivative works for internal use only

### Restrictions
You shall NOT:
- Distribute, sublicense, lease, rent, or transfer the Software to any third party
- Reverse engineer, decompile, or disassemble the Software
- Remove or alter any proprietary notices or labels on the Software
- Use the Software for any unlawful purpose
- Publish benchmark results without prior written consent

### Ownership
ODA retains all right, title, and interest in and to the Software, including all intellectual property rights. This license does not grant you any ownership rights in the Software.

### Confidentiality
The Software contains trade secrets and confidential information of ODA. You agree to maintain the confidentiality of the Software and not disclose it to any third party.

### Warranty Disclaimer
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. ODA DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

### Limitation of Liability
IN NO EVENT SHALL ODA BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS, DATA, OR BUSINESS INTERRUPTION.

### Termination
This license terminates automatically upon breach. Upon termination, you must cease all use and destroy all copies of the Software.

### Governing Law
This Agreement shall be governed by the laws of India, with exclusive jurisdiction in the courts of Mumbai.

### Contact
For licensing inquiries: legal@optimumdataanalytics.com