# ODA Marketing — Frappe Development & Customization Guide

Welcome to the **ODA Marketing** developer guide. This document provides step-by-step instructions for developers and administrators on how to extend the application, create new fields, build new DocTypes, link fields, and maintain data consistency across Frappe environments.

---

## 1. Prerequisites & Developer Mode

Before creating or editing any DocType, **Developer Mode** must be enabled on your Frappe site.

### Checking Developer Mode
Inspect site configuration at `sites/marketing.localhost/site_config.json`:
```json
{
 "developer_mode": 1
}
```
If `"developer_mode"` is `0` or missing, enable it via shell:
```bash
bench --site marketing.localhost set-config developer_mode 1
```

> [!IMPORTANT]
> **Why Developer Mode Matters**:
> When `developer_mode: 1` is enabled, all changes made via Desk UI or JSON schema are immediately written to `.json` files inside the app directory (`apps/oda_marketing/oda_marketing/oda_marketing/doctype/...`). If developer mode is disabled, changes exist only in the local database and cannot be committed to Git.

---

## 2. Creating a New Field in an Existing DocType

Follow these steps to add a new field to an existing DocType (e.g. adding `campaign_code` to `Content Item`).

### Method A: Via Desk UI (Recommended for Speed)
1. Log into Frappe Desk as `Administrator`.
2. Open **DocType List** → Click on the target DocType (e.g. **Content Item**).
3. Scroll to the **Fields** grid.
4. Click **Add Row** or insert a field in the desired sequence.
5. Set field properties:
   - **Label**: e.g., `Campaign Code`
   - **Field Type**: `Data` / `Select` / `Link` / `Check` / `Date` / `Attach`
   - **Field Name**: `campaign_code` (auto-generated in `snake_case`)
   - **Options**: (If Link: Target DocType name like `Content Calendar`; If Select: options separated by newline `Option A\nOption B`).
   - Check options as needed: `In List View`, `In Standard Filter`, `Mandatory (reqd)`, `Read Only`.
6. Click **Save**.
7. Confirm that the JSON file has updated automatically in Git:
   ```bash
   git status
   # Should show modified: apps/oda_marketing/oda_marketing/oda_marketing/doctype/content_item/content_item.json
   ```

### Method B: Via Direct JSON Editing
1. Open the DocType JSON file:
   `apps/oda_marketing/oda_marketing/oda_marketing/doctype/content_item/content_item.json`
2. Add the field object to the `"fields"` array:
   ```json
   {
    "fieldname": "campaign_code",
    "fieldtype": "Data",
    "in_list_view": 1,
    "label": "Campaign Code"
   }
   ```
3. Add `"campaign_code"` to the `"field_order"` array in the JSON.
4. Run `bench migrate` to update the database table:
   ```bash
   bench --site marketing.localhost migrate
   ```

---

## 3. Creating a Brand New DocType

Frappe supports three primary DocType architectures:

| DocType Type | Purpose | Example in App |
| :--- | :--- | :--- |
| **Standard DocType** | Standalone master/transaction record with database table | `Content Item`, `Content Brief` |
| **Single DocType** | Global application settings / configuration (1 record system-wide) | `Marketing Settings` |
| **Child Table** | Grid table embedded inside a parent DocType | `Calendar Slot` |

### Step 3.1: Creating a Standard DocType
1. Navigate to **DocType List** → Click **Add DocType**.
2. Set properties:
   - **DocType Name**: e.g., `Marketing Campaign`
   - **Module**: `ODA Marketing` (CRITICAL: Always select `ODA Marketing`, never `Frappe Core`)
   - **Naming Rule**: e.g., `By "Naming Series" field` or `Set by user`
3. Add fields (e.g. `campaign_name`, `start_date`, `end_date`, `budget`).
4. Set permissions under **Permissions** grid (Assign roles like `System Manager`, `Marketing Lead`).
5. Click **Save**.
6. Verify directory creation:
   `apps/oda_marketing/oda_marketing/oda_marketing/doctype/marketing_campaign/`
   - `marketing_campaign.json`
   - `marketing_campaign.py`
   - `marketing_campaign.js`

### Step 3.2: Creating a Single DocType (Settings Page)
1. Create DocType as usual.
2. Check **Is Single**: `[x]` (Check box).
3. Single DocTypes do not produce database tables; fields are stored in `tabSingle Docs`.
4. Access programmatically in Python:
   ```python
   settings = frappe.get_single("Marketing Settings")
   print(settings.enable_email_notifications)
   ```

### Step 3.3: Creating a Child Table DocType
1. Create DocType as usual.
2. Check **Is Child Table**: `[x]` (Check box).
3. Embed inside a parent DocType by adding a field of type **`Table`** with `Options = Child DocType Name`.

---

## 4. Linking Fields Between DocTypes

Linking connects documents and establishes relational integrity across your Frappe app.

### 1. Link Field (Foreign Key Relation)
Points a field to a single record in another DocType.
- **Field Type**: `Link`
- **Options**: `Target DocType Name` (e.g., `Content Calendar`)
- **Example**: In `Content Item`, field `content_calendar` has `Field Type: Link` and `Options: Content Calendar`.

### 2. Select Field (Enum Dropdown)
Presents a static list of string choices.
- **Field Type**: `Select`
- **Options**: Options separated by newline:
  ```text
  Planned
  Briefed
  In Progress
  Approved
  ```

### 3. Dynamic Fetch (Auto-Populating Fields from Linked Record)
To automatically fetch a value from a linked record when selected:
- **Field Type**: Match target field type (e.g., `Data`)
- **Fetch From**: `link_fieldname.target_fieldname`
- **Example**: `content_calendar.from_date` automatically fetches `from_date` when a calendar is picked.

---

## 5. Deployment & Schema Synchronization Workflow

Whenever schema changes or new DocTypes are committed, teammates or deployment environments must sync database schemas.

### Git & Bench Sync Command Sequence
```bash
# 1. Pull latest code changes
git pull origin main

# 2. Sync database schema changes with JSON definitions
bench --site marketing.localhost migrate

# 3. (Optional) Run setup fixtures to re-seed default data & sidebars
bench --site marketing.localhost execute oda_marketing.setup_fixtures.run_setup

# 4. Run automated test suite to ensure clean build
bench --site marketing.localhost run-tests --module oda_marketing.tests.test_demo_script
```

---

## 6. Development Best Practices Checklist

- [x] **Always check Developer Mode** before creating DocTypes.
- [x] **Never modify code in `frappe` core app** — keep all custom logic in `oda_marketing`.
- [x] **Use `snake_case` for fieldnames** (`assigned_to`, `planned_publish_date`).
- [x] **Commit after every DocType edit** so JSON schema updates are version-controlled.
- [x] **Run `bench migrate` after pulling Git updates**.
