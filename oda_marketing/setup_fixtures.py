# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate


def setup_roles():
	roles = [
		{"role_name": "Marketing Lead", "desk_access": 1},
		{"role_name": "Content Writer", "desk_access": 1},
		{"role_name": "Technical Reviewer", "desk_access": 1},
	]
	for r in roles:
		if not frappe.db.exists("Role", r["role_name"]):
			role_doc = frappe.get_doc({
				"doctype": "Role",
				"role_name": r["role_name"],
				"desk_access": r["desk_access"]
			})
			role_doc.insert(ignore_permissions=True)
			print(f"Created Role: {r['role_name']}")



def setup_email_templates_and_settings():
	templates = [
		{
			"name": "Marketing Writer Notification",
			"subject": "[TASK NOTIFICATION] Deliverable '{{ doc.title }}' Status: {{ doc.workflow_state }}",
			"response": """<p>Hello <b>{{ assigned_to_name }}</b>,</p>
{% if doc.workflow_state == "Briefed" %}
  <p>You have been assigned to create the content deliverable <b>{{ doc.title }}</b> (Type: {{ doc.content_type }}). Task details have been issued for your review.</p>
  <p><b>Planned Publish Date:</b> {{ doc.planned_publish_date }}</p>
  <p>Please log into the portal, review the task details, and proceed with drafting.</p>
{% elif doc.workflow_state == "In Revision" %}
  <p>Revisions have been requested for your deliverable <b>{{ doc.title }}</b>.</p>
  {% if doc.revision_feedback_notes %}
    <p style='background-color: #fef2f2; padding: 12px; border-left: 4px solid #ef4444; margin: 12px 0;'>
      <b>Reviewer Feedback / Notes:</b><br>{{ doc.revision_feedback_notes }}
    </p>
  {% endif %}
  {% if content_file_1_link %}
    <p><b>Current Primary Draft:</b> {{ content_file_1_link }}</p>
  {% endif %}
  <p>Please update your draft attachments and click <b>'Resubmit Draft'</b>.</p>
{% else %}
  <p>Your marketing deliverable <b>{{ doc.title }}</b> status is now: <b>{{ doc.workflow_state }}</b>.</p>
{% endif %}
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #4F46E5; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		},
		{
			"name": "Marketing Reviewer Notification",
			"subject": "[REVIEW NOTIFICATION] {{ doc.workflow_state }} for '{{ doc.title }}'",
			"response": """<p>Hello <b>{{ reviewer_technical_name }}</b>,</p>
<p>Content deliverable <b>{{ doc.title }}</b> (Type: {{ doc.content_type }}) requires your signoff for status: <b>{{ doc.workflow_state }}</b>.</p>
<ul>
  <li><b>Assigned Writer:</b> {{ assigned_to_name }}</li>
  <li><b>Created By:</b> {{ creator_name }}</li>
  <li><b>Technical Reviewer:</b> {{ reviewer_technical_name }}</li>
  <li><b>SLA Due Date:</b> {{ doc.sla_due_date }}</li>
  {% if content_file_1_link %}
    <li><b>Primary Content Draft:</b> {{ content_file_1_link }}</li>
  {% endif %}
  {% if content_file_2_link %}
    <li><b>Supporting Asset 1:</b> {{ content_file_2_link }}</li>
  {% endif %}
  {% if content_file_3_link %}
    <li><b>Supporting Asset 2:</b> {{ content_file_3_link }}</li>
  {% endif %}
</ul>
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #4F46E5; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		},
		{
			"name": "Marketing Publisher Notification",
			"subject": "[PUBLISHING NOTIFICATION] Deliverable '{{ doc.title }}' Status: Approved for Publishing",
			"response": """<p>Hello <b>{{ publisher_name }}</b>,</p>
<p>Great news! The deliverable <b>{{ doc.title }}</b> has passed technical review by <b>{{ reviewer_technical_name }}</b> and is marked <b>Approved</b> for final publishing.</p>
<ul>
  <li><b>Assigned Writer:</b> {{ assigned_to_name }}</li>
  <li><b>Created By:</b> {{ creator_name }}</li>
  {% if content_file_1_link %}
    <li><b>Primary Content Draft:</b> {{ content_file_1_link }}</li>
  {% endif %}
  {% if content_file_2_link %}
    <li><b>Supporting Asset 1:</b> {{ content_file_2_link }}</li>
  {% endif %}
  {% if content_file_3_link %}
    <li><b>Supporting Asset 2:</b> {{ content_file_3_link }}</li>
  {% endif %}
</ul>
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #059669; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		},
		{
			"name": "Marketing Published Notification",
			"subject": "[CONGRATULATIONS] Deliverable '{{ doc.title }}' Has Been Published Live!",
			"response": """<p>Hello <b>{{ assigned_to_name }}</b>,</p>
<p>Congratulations! Your marketing deliverable <b>{{ doc.title }}</b> has been published live!</p>
{% if doc.published_url %}
  <p><b>Live Asset URL:</b> <a href="{{ doc.published_url }}" target="_blank">{{ doc.published_url }}</a></p>
{% endif %}
<p>Thank you for your hard work on this deliverable.</p>
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #059669; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		},
		{
			"name": "Marketing Overdue SLA Alert",
			"subject": "[OVERDUE ALERT] Deliverable '{{ doc.title }}' Exceeded SLA Date",
			"response": """<p style='color: #dc2626; font-weight: bold;'>URGENT ESCALATION ALERT</p>
<p>Content deliverable <b>{{ doc.title }}</b> (Planned Publish Date: {{ doc.planned_publish_date }}) has passed its SLA Due Date ({{ doc.sla_due_date }}).</p>
{% if content_file_1_link %}
  <p><b>Primary Content Draft:</b> {{ content_file_1_link }}</p>
{% endif %}
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #DC2626; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		}
	]

	for t in templates:
		if frappe.db.exists("Email Template", t["name"]):
			et = frappe.get_doc("Email Template", t["name"])
			et.subject = t["subject"]
			et.response = t["response"]
			et.save(ignore_permissions=True)
		else:
			et = frappe.get_doc({
				"doctype": "Email Template",
				"name": t["name"],
				"subject": t["subject"],
				"response": t["response"],
				"use_html": 1
			})
			et.insert(ignore_permissions=True)
			print(f"Created/Updated Email Template: {t['name']}")

	# Initial Setup Defaults: Keep optional features (email notifications & AI copilot) disabled by default
	# to allow clean installation without requiring pre-configured publisher/API settings.
	settings = frappe.get_single("Marketing Settings")
	settings.enable_email_notifications = 0
	settings.enable_auto_overdue_flag = 0
	settings.enable_ai_copilot = 0
	settings.default_sla_lead_days = 14
	settings.ai_copilot_passing_score = 80
	settings.ai_provider = "APIM Gateway"
	settings.writer_email_template = "Marketing Writer Notification"
	settings.reviewer_email_template = "Marketing Reviewer Notification"
	settings.publisher_email_template = "Marketing Publisher Notification"
	settings.published_email_template = "Marketing Published Notification"
	settings.overdue_sla_email_template = "Marketing Overdue SLA Alert"

	settings.subagent_meta_prompt = """You are a constructive AI Copilot & Enterprise Marketing Auditor for Optimum Data Analytics (ODA).
Your task is to analyze deliverable metadata and create a practical, fair System Prompt for evaluating the document.

INPUT METADATA:
- Deliverable Title: {title}
- Content Type: {content_type} (Blog, Poll, Flowchart, Carousel)
- Topic / Brief: {topic}
- Practice Area / Domain: {practice_area}
- Minimum Passing Threshold: 80%

INSTRUCTIONS FOR GENERATING THE SYSTEM PROMPT:
Construct a System Prompt instructing the Evaluator Agent to:
1. Praise strong structure, clear domain terminology, engaging enterprise tone, and alignment with "{topic}".
2. Evaluate technical relevance for {practice_area} and structure for {content_type}.
3. Award high passing scores (85%–98%) for complete, well-written enterprise deliverables.
4. Only request revisions if content is missing, blank, or severely incomplete.

Return raw System Prompt text only."""

	settings.evaluator_default_prompt = """You are an encouraging AI Copilot & Technical Reviewer for Optimum Data Analytics (ODA).
You are evaluating the {content_type} titled "{title}" in the domain of {practice_area}.

EVALUATION GUIDELINES FOR THIS DELIVERABLE:
1. Praise strong structure, clear domain terminology ({practice_area}), and alignment with "{topic}".
2. Award high passing scores (85%–98%) for complete, well-written, publishable enterprise content.
3. Passing threshold is 80%."""

	if settings.default_content_calendar and not frappe.db.exists("Content Calendar", settings.default_content_calendar):
		settings.default_content_calendar = None

	settings.save(ignore_permissions=True)
	print("Initialized Marketing Settings with production defaults (Switches: 0, SLA Lead Days: 14).")


def setup_workflow_states_and_actions():
	state_names = [
		"Planned", "Briefed", "In Progress", "Marketing Copilot Review",
		"In Review - Technical", "In Revision", "Approved", "Published"
	]
	for state in state_names:
		if not frappe.db.exists("Workflow State", state):
			s_doc = frappe.get_doc({
				"doctype": "Workflow State",
				"workflow_state_name": state
			})
			s_doc.insert(ignore_permissions=True)
			print(f"Created Workflow State: {state}")

	action_names = [
		"Issue Brief", "Accept Brief", "Submit for Copilot Review",
		"Submit for Technical Review", "Approve AI Copilot", "Request Changes",
		"Approve Technical", "Resubmit Draft", "Publish"
	]
	for action in action_names:
		if not frappe.db.exists("Workflow Action Master", action):
			a_doc = frappe.get_doc({
				"doctype": "Workflow Action Master",
				"workflow_action_name": action
			})
			a_doc.insert(ignore_permissions=True)
			print(f"Created Workflow Action Master: {action}")


def setup_workflow():
	setup_workflow_states_and_actions()

	workflow_name = "Content Item Workflow"
	if frappe.db.exists("Workflow", workflow_name):
		frappe.delete_doc("Workflow", workflow_name, force=True, ignore_permissions=True)

	states = [
		{"state": "Planned", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Primary"},
		{"state": "Briefed", "doc_status": "0", "allow_edit": "Content Writer", "style": "Info"},
		{"state": "In Progress", "doc_status": "0", "allow_edit": "Content Writer", "style": "Warning"},
		{"state": "Marketing Copilot Review", "doc_status": "0", "allow_edit": "Content Writer", "style": "Info"},
		{"state": "In Review - Technical", "doc_status": "0", "allow_edit": "Technical Reviewer", "style": "Warning"},
		{"state": "In Revision", "doc_status": "0", "allow_edit": "Content Writer", "style": "Danger"},
		{"state": "Approved", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Success"},
		{"state": "Published", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Success"},
	]

	transitions = [
		{"state": "Planned", "action": "Issue Brief", "next_state": "Briefed", "allowed": "Marketing Lead"},
		{"state": "Planned", "action": "Issue Brief", "next_state": "Briefed", "allowed": "System Manager"},

		{"state": "Briefed", "action": "Accept Brief", "next_state": "In Progress", "allowed": "Content Writer"},
		{"state": "Briefed", "action": "Accept Brief", "next_state": "In Progress", "allowed": "Marketing Lead"},
		{"state": "Briefed", "action": "Accept Brief", "next_state": "In Progress", "allowed": "System Manager"},

		# AI Copilot workflow branch
		{"state": "Briefed", "action": "Submit for Copilot Review", "next_state": "Marketing Copilot Review", "allowed": "Content Writer"},
		{"state": "Briefed", "action": "Submit for Copilot Review", "next_state": "Marketing Copilot Review", "allowed": "Marketing Lead"},
		{"state": "Briefed", "action": "Submit for Copilot Review", "next_state": "Marketing Copilot Review", "allowed": "System Manager"},

		{"state": "In Progress", "action": "Submit for Copilot Review", "next_state": "Marketing Copilot Review", "allowed": "Content Writer"},
		{"state": "In Progress", "action": "Submit for Copilot Review", "next_state": "Marketing Copilot Review", "allowed": "Marketing Lead"},
		{"state": "In Progress", "action": "Submit for Copilot Review", "next_state": "Marketing Copilot Review", "allowed": "System Manager"},

		# Direct Technical Review workflow branch (Used when AI Copilot is disabled)
		{"state": "Briefed", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "Content Writer"},
		{"state": "Briefed", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "Marketing Lead"},
		{"state": "Briefed", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "System Manager"},

		{"state": "In Progress", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "Content Writer"},
		{"state": "In Progress", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "Marketing Lead"},
		{"state": "In Progress", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "System Manager"},

		{"state": "In Revision", "action": "Resubmit Draft", "next_state": "Marketing Copilot Review", "allowed": "Content Writer"},
		{"state": "In Revision", "action": "Resubmit Draft", "next_state": "Marketing Copilot Review", "allowed": "Marketing Lead"},
		{"state": "In Revision", "action": "Resubmit Draft", "next_state": "Marketing Copilot Review", "allowed": "System Manager"},

		{"state": "In Revision", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "Content Writer"},
		{"state": "In Revision", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "Marketing Lead"},
		{"state": "In Revision", "action": "Submit for Technical Review", "next_state": "In Review - Technical", "allowed": "System Manager"},

		{"state": "Marketing Copilot Review", "action": "Approve AI Copilot", "next_state": "In Review - Technical", "allowed": "Content Writer"},
		{"state": "Marketing Copilot Review", "action": "Approve AI Copilot", "next_state": "In Review - Technical", "allowed": "Marketing Lead"},
		{"state": "Marketing Copilot Review", "action": "Approve AI Copilot", "next_state": "In Review - Technical", "allowed": "System Manager"},

		{"state": "Marketing Copilot Review", "action": "Request Changes", "next_state": "In Revision", "allowed": "Content Writer"},
		{"state": "Marketing Copilot Review", "action": "Request Changes", "next_state": "In Revision", "allowed": "Marketing Lead"},
		{"state": "Marketing Copilot Review", "action": "Request Changes", "next_state": "In Revision", "allowed": "System Manager"},

		{"state": "In Review - Technical", "action": "Request Changes", "next_state": "In Revision", "allowed": "Technical Reviewer"},
		{"state": "In Review - Technical", "action": "Request Changes", "next_state": "In Revision", "allowed": "Marketing Lead"},
		{"state": "In Review - Technical", "action": "Request Changes", "next_state": "In Revision", "allowed": "System Manager"},

		{"state": "In Review - Technical", "action": "Approve Technical", "next_state": "Approved", "allowed": "Technical Reviewer"},
		{"state": "In Review - Technical", "action": "Approve Technical", "next_state": "Approved", "allowed": "Marketing Lead"},
		{"state": "In Review - Technical", "action": "Approve Technical", "next_state": "Approved", "allowed": "System Manager"},

		{"state": "Approved", "action": "Publish", "next_state": "Published", "allowed": "Marketing Lead"},
		{"state": "Approved", "action": "Publish", "next_state": "Published", "allowed": "System Manager"},
	]

	wf = frappe.get_doc({
		"doctype": "Workflow",
		"workflow_name": workflow_name,
		"document_type": "Content Item",
		"is_active": 1,
		"override_status": 1,
		"workflow_state_field": "workflow_state",
		"states": states,
		"transitions": transitions,
	})
	wf.insert(ignore_permissions=True)
	print(f"Created Workflow: {workflow_name}")


def setup_kanban_board():
	board_name = "Content Pipeline"
	if frappe.db.exists("Kanban Board", board_name):
		frappe.delete_doc("Kanban Board", board_name, force=True, ignore_permissions=True)

	columns = [
		{"column_name": "Planned", "status": "Active", "indicator": "Gray"},
		{"column_name": "Briefed", "status": "Active", "indicator": "Light Blue"},
		{"column_name": "In Progress", "status": "Active", "indicator": "Orange"},
		{"column_name": "Marketing Copilot Review", "status": "Active", "indicator": "Purple"},
		{"column_name": "In Review - Technical", "status": "Active", "indicator": "Yellow"},
		{"column_name": "In Revision", "status": "Active", "indicator": "Red"},
		{"column_name": "Approved", "status": "Active", "indicator": "Cyan"},
		{"column_name": "Published", "status": "Active", "indicator": "Green"},
	]

	board = frappe.get_doc({
		"doctype": "Kanban Board",
		"kanban_board_name": board_name,
		"reference_doctype": "Content Item",
		"field_name": "workflow_state",
		"private": 0,
		"columns": columns,
	})
	board.insert(ignore_permissions=True)
	print(f"Created Kanban Board: {board_name}")



def setup_workspace_sidebar():
	sidebar_name = "ODA Marketing"
	if frappe.db.exists("Workspace Sidebar", sidebar_name):
		frappe.delete_doc("Workspace Sidebar", sidebar_name, force=True, ignore_permissions=True)
	frappe.db.delete("Workspace Sidebar Item", {"parent": sidebar_name})

	items = [
		{
			"type": "Section Break",
			"label": "Content Execution",
			"icon": "list-checks",
			"collapsible": 0,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Content Item",
			"label": "Content Item",
			"icon": "calendar",
			"child": 0,
		},
		{
			"type": "Section Break",
			"label": "Setup",
			"icon": "settings",
			"collapsible": 1,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Content Calendar",
			"label": "Content Calendar",
			"icon": "calendar",
			"child": 0,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Marketing Settings",
			"label": "Marketing Settings",
			"icon": "settings",
			"child": 0,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Env Variable",
			"label": "Env Variables",
			"icon": "key",
			"child": 0,
		},
	]

	sidebar = frappe.get_doc({
		"doctype": "Workspace Sidebar",
		"title": sidebar_name,
		"app": "oda_marketing",
		"header_icon": "megaphone",
		"standard": 1,
		"items": items,
	})
	sidebar.insert(ignore_permissions=True)

	frappe.db.delete("Custom DocPerm", {"parent": "Workspace Sidebar"})

	frappe.get_doc({
		"doctype": "Custom DocPerm",
		"parent": "Workspace Sidebar",
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": "System Manager",
		"read": 1, "write": 1, "create": 1, "delete": 1
	}).insert(ignore_permissions=True)

	frappe.get_doc({
		"doctype": "Custom DocPerm",
		"parent": "Workspace Sidebar",
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": "Marketing Lead",
		"read": 1, "write": 1, "create": 1, "delete": 1
	}).insert(ignore_permissions=True)

	frappe.get_doc({
		"doctype": "Custom DocPerm",
		"parent": "Workspace Sidebar",
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": "Desk User",
		"read": 0, "write": 0, "create": 0, "delete": 0
	}).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Workspace Sidebar")
	frappe.clear_cache(doctype="Workspace")


def setup_desktop_icon():
	if frappe.db.exists("Desktop Icon", "ODA Marketing Copilot"):
		frappe.delete_doc("Desktop Icon", "ODA Marketing Copilot", force=True, ignore_permissions=True)

	if frappe.db.exists("Desktop Icon", "ODA Marketing"):
		icon_doc = frappe.get_doc("Desktop Icon", "ODA Marketing")
		icon_doc.label = "ODA Marketing"
		icon_doc.logo_url = "/assets/oda_marketing/images/oda_logo.svg"
		icon_doc.save(ignore_permissions=True)
	else:
		icon_doc = frappe.get_doc({
			"doctype": "Desktop Icon",
			"name": "ODA Marketing",
			"label": "ODA Marketing",
			"app": "oda_marketing",
			"logo_url": "/assets/oda_marketing/images/oda_logo.svg",
			"standard": 1,
			"icon_type": "App",
			"link": "/app/oda-marketing"
		})
		icon_doc.insert(ignore_permissions=True)


def run_setup():
	setup_roles()
	setup_email_templates_and_settings()
	setup_workflow()
	setup_kanban_board()
	setup_workspace_sidebar()
	setup_desktop_icon()
	frappe.db.commit()
