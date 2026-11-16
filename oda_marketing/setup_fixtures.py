# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate


def setup_roles():
	roles = [
		{"role_name": "Marketing Lead", "desk_access": 1},
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

	frappe.clear_cache(doctype="Content Item")
	frappe.clear_cache(doctype="Content Calendar")
	frappe.clear_cache(doctype="Content Item Option")


def setup_content_item_options():
	"""Create default Content Item Option records for Format and Industry Domain."""
	format_options = [
		{"label": "Blog", "desc": "Detailed written article or post focusing on enterprise software or domain topics."},
		{"label": "Poll", "desc": "Interactive survey or quick question format designed for engagement."},
		{"label": "Flowchart", "desc": "Visual diagram detailing processes, data flows, or workflows."},
		{"label": "Carousel", "desc": "Multi-slide visual presentation or swipeable graphic summary."}
	]
	industry_domain_options = [
		{"label": "HCLS", "desc": "Healthcare and Life Sciences domain, patient analytics, clinical trials, FDA regulatory compliance."},
		{"label": "Pharma Supply Chain", "desc": "Pharmaceutical supply chain governance, serialization, cold-chain tracking, Good Distribution Practice."},
		{"label": "Fintech", "desc": "Financial technologies, payments infrastructure, fraud prevention, banking compliance."},
		{"label": "Agriculture", "desc": "Agri-tech, precision farming, crop monitoring, supply sustainability."},
		{"label": "Cross-domain", "desc": "Cross-industry enterprise analytics, cloud infrastructure, AI architecture."}
	]

	for idx, f in enumerate(format_options):
		if not frappe.db.exists("Content Item Option", f["label"]):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Format",
				"option_label": f["label"],
				"option_description": f["desc"],
				"is_active": 1,
				"sort_order": idx
			}).insert(ignore_permissions=True)
			print(f"Created Content Item Option: Format - {f['label']}")

	for idx, d in enumerate(industry_domain_options):
		if not frappe.db.exists("Content Item Option", d["label"]):
			frappe.get_doc({
				"doctype": "Content Item Option",
				"option_type": "Industry Domain",
				"option_label": d["label"],
				"option_description": d["desc"],
				"is_active": 1,
				"sort_order": idx
			}).insert(ignore_permissions=True)
			print(f"Created Content Item Option: Industry Domain - {d['label']}")


def setup_email_templates_and_settings():
	templates = [
		{
			"name": "Marketing Writer Notification",
			"subject": "[TASK NOTIFICATION] Deliverable '{{ doc.title }}' Status: {{ doc.workflow_state }}",
			"response": """<p>Hello <b>{{ assigned_to_name }}</b>,</p>
{% if doc.workflow_state == "Briefed" %}
  <p>You have been assigned to create the content deliverable <b>{{ doc.title }}</b> (Format: {{ doc.content_type }}). Task details have been issued for your review.</p>
  <p><b>Due Date:</b> {{ doc.due_date }}</p>
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
<p>Content deliverable <b>{{ doc.title }}</b> (Format: {{ doc.content_type }}) requires your signoff for status: <b>{{ doc.workflow_state }}</b>.</p>
<ul>
  <li><b>Assigned Writer:</b> {{ assigned_to_name }}</li>
  <li><b>Created By:</b> {{ creator_name }}</li>
  <li><b>Reviewer:</b> {{ reviewer_technical_name }}</li>
  <li><b>Due Date:</b> {{ doc.due_date }}</li>
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
<p>Great news! The deliverable <b>{{ doc.title }}</b> has passed review by <b>{{ reviewer_technical_name }}</b> and is marked <b>Approved</b> for final publishing.</p>
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
			"name": "Marketing Overdue Alert",
			"subject": "[OVERDUE ALERT] Deliverable '{{ doc.title }}' Exceeded Due Date",
			"response": """<p style='color: #dc2626; font-weight: bold;'>URGENT ESCALATION ALERT</p>
<p>Content deliverable <b>{{ doc.title }}</b> (Planned Publish Date: {{ doc.planned_publish_date }}) has passed its Due Date ({{ doc.due_date }}).</p>
{% if content_file_1_link %}
  <p><b>Primary Content Draft:</b> {{ content_file_1_link }}</p>
{% endif %}
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #DC2626; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		},
		{
			"name": "Marketing Due Date Reminder",
			"subject": "[DUE DATE REMINDER] Deliverable '{{ doc.title }}' Due Soon ({{ doc.due_date }})",
			"response": """<p>Hello <b>{{ assigned_to_name }}</b>,</p>
<p>This is a friendly reminder that the content deliverable <b>{{ doc.title }}</b> is approaching its Due Date (<b>{{ doc.due_date }}</b>).</p>
<ul>
  <li><b>Format:</b> {{ doc.content_type }}</li>
  <li><b>Status:</b> {{ doc.workflow_state }}</li>
  <li><b>Assigned Reviewer:</b> {{ reviewer_technical_name }}</li>
</ul>
<div style='margin-top: 15px;'>
  <a href="{{ content_item_url }}" target="_blank" style="display: inline-block; background-color: #3B82F6; color: #ffffff; padding: 10px 18px; text-decoration: none; border-radius: 6px; font-weight: 600;">View Content Item in Desk</a>
</div>"""
		}
	]

	for t in templates:
		if not frappe.db.exists("Email Template", t["name"]):
			et = frappe.get_doc({
				"doctype": "Email Template",
				"name": t["name"],
				"subject": t["subject"],
				"response": t["response"],
				"use_html": 1
			})
			et.insert(ignore_permissions=True)
			print(f"Created/Updated Email Template: {t['name']}")

	# Fill only unset settings so migrations never overwrite administrator configuration.
	settings = frappe.get_single("Marketing Settings")
	settings_changed = False
	defaults = {
		"writer_email_template": "Marketing Writer Notification",
		"reviewer_email_template": "Marketing Reviewer Notification",
		"publisher_email_template": "Marketing Publisher Notification",
		"published_email_template": "Marketing Published Notification",
		"overdue_email_template": "Marketing Overdue Alert",
		"business_hours_start": 9,
		"business_hours_end": 19,
		"sla_reminder_days_before": 3,
		"max_writer_copilot_reviews_per_item": 2,
		"max_reviewer_copilot_reviews_per_item": 2,
	}
	for fieldname, value in defaults.items():
		if getattr(settings, fieldname, None) is None:
			settings.set(fieldname, value)
			settings_changed = True

	if getattr(settings, "subagent_meta_prompt", None) is None:
		settings.subagent_meta_prompt = """You are a constructive AI Copilot & Enterprise Marketing Auditor for Optimum Data Analytics (ODA).
Your task is to analyze deliverable metadata and create a practical, fair System Prompt for evaluating the document.

INPUT METADATA:
- Deliverable Title: {title}
- Content Type / Format: {content_type}
- Format Expectations: {format_description}
- Description / Brief: {topic}
- Industry Domain / Practice Area: {practice_area}
- Domain Context & Guidelines: {domain_description}
- Minimum Passing Threshold: {passing_score}%

INSTRUCTIONS FOR GENERATING THE SYSTEM PROMPT:
Construct a System Prompt instructing the Evaluator Agent to:
1. Praise strong structure, clear domain terminology, engaging enterprise tone, and alignment with "{topic}".
2. Evaluate technical relevance for Industry Domain "{practice_area}" ({domain_description}) and format expectations for "{content_type}" ({format_description}).
3. Score each criterion based on evidence in the draft; do not assume or target a particular score.
4. Apply the configured passing threshold without changing workflow state or treating the score as an approval.
5. Request revisions for any material factual, technical, structural, or brief-alignment gaps.

Return raw System Prompt text only."""
		settings_changed = True

	if getattr(settings, "evaluator_default_prompt", None) is None:
		settings.evaluator_default_prompt = """You are an encouraging AI Copilot & Technical Reviewer for Optimum Data Analytics (ODA).
You are evaluating the {content_type} ({format_description}) titled "{title}" in the domain of {practice_area} ({domain_description}).

EVALUATION GUIDELINES FOR THIS DELIVERABLE:
1. Praise strong structure, clear domain terminology ({practice_area}), and alignment with "{topic}".
2. Evaluate technical depth for {practice_area} and layout compliance for {content_type}.
3. Score each criterion based on evidence in the draft; do not assume or target a particular score.
4. Passing threshold is {passing_score}%. The score is informational and must not approve or route the item."""
		settings_changed = True

	if settings_changed:
		settings.save(ignore_permissions=True)
	print("Initialized Marketing Settings with production defaults (Switches: 0, SLA Lead Days: 14).")


def setup_workflow_states_and_actions():
	state_names = [
		"Planned", "Briefed", "In Progress",
		"In Review", "In Revision", "Approved", "Published"
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
		"Issue Brief", "Start Work", "Submit for Review",
		"Request Changes", "Approve", "Resubmit Draft", "Publish"
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
		return

	states = [
		{"state": "Planned", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Primary"},
		{"state": "Briefed", "doc_status": "0", "allow_edit": "Desk User", "style": "Info"},
		{"state": "In Progress", "doc_status": "0", "allow_edit": "Desk User", "style": "Warning"},
		{"state": "In Review", "doc_status": "0", "allow_edit": "Desk User", "style": "Warning"},
		{"state": "In Revision", "doc_status": "0", "allow_edit": "Desk User", "style": "Danger"},
		{"state": "Approved", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Success"},
		{"state": "Published", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Success"},
	]

	transitions = [
		# Planned -> Briefed (Lead only)
		{"state": "Planned", "action": "Issue Brief", "next_state": "Briefed", "allowed": "Marketing Lead"},
		{"state": "Planned", "action": "Issue Brief", "next_state": "Briefed", "allowed": "System Manager"},

		# Briefed -> In Progress (writer starts work, stamps brief_accepted_on)
		{"state": "Briefed", "action": "Start Work", "next_state": "In Progress", "allowed": "Desk User"},
		{"state": "Briefed", "action": "Start Work", "next_state": "In Progress", "allowed": "Marketing Lead"},

		# In Progress -> In Review (writer submits draft)
		{"state": "In Progress", "action": "Submit for Review", "next_state": "In Review", "allowed": "Desk User"},
		{"state": "In Progress", "action": "Submit for Review", "next_state": "In Review", "allowed": "Marketing Lead"},

		# In Review -> In Revision (reviewer requests changes)
		{"state": "In Review", "action": "Request Changes", "next_state": "In Revision", "allowed": "Desk User"},
		{"state": "In Review", "action": "Request Changes", "next_state": "In Revision", "allowed": "Marketing Lead"},

		# In Review -> Approved (reviewer approves)
		{"state": "In Review", "action": "Approve", "next_state": "Approved", "allowed": "Desk User"},
		{"state": "In Review", "action": "Approve", "next_state": "Approved", "allowed": "Marketing Lead"},

		# In Revision -> In Progress (writer resubmits draft)
		{"state": "In Revision", "action": "Resubmit Draft", "next_state": "In Progress", "allowed": "Desk User"},
		{"state": "In Revision", "action": "Resubmit Draft", "next_state": "In Progress", "allowed": "Marketing Lead"},

		# Approved -> Published (Lead/Publisher only)
		{"state": "Approved", "action": "Publish", "next_state": "Published", "allowed": "Marketing Lead"},
		{"state": "Approved", "action": "Publish", "next_state": "Published", "allowed": "System Manager"},
		{"state": "Approved", "action": "Publish", "next_state": "Published", "allowed": "Desk User"},
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
		return

	columns = [
		{"column_name": "Planned", "status": "Active", "indicator": "Gray"},
		{"column_name": "Briefed", "status": "Active", "indicator": "Light Blue"},
		{"column_name": "In Progress", "status": "Active", "indicator": "Orange"},
		{"column_name": "In Review", "status": "Active", "indicator": "Yellow"},
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
		return

	items = [
		{
			"type": "Section Break",
			"label": "Content Execution",
			"icon": "list-checks",
			"collapsible": 0,
		},
		{
			"type": "Link",
			"link_type": "Page",
			"link_to": "marketing-dashboard",
			"label": "Marketing Dashboard",
			"icon": "dashboard",
			"child": 0,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Content Item",
			"label": "Content Items",
			"icon": "clipboard-pen-line",
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
			"link_to": "Content Item Option",
			"label": "Content Item Options",
			"icon": "tag",
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

	frappe.clear_cache(doctype="Workspace Sidebar")
	frappe.clear_cache(doctype="Workspace")


def setup_desktop_icon():
	if frappe.db.exists("Desktop Icon", "ODA Marketing"):
		return
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


def setup_content_item_dashboard():
	"""Sets up native Dashboard Charts, Number Cards, and Dashboard for Content Item List Dashboard View."""
	# 1. Setup Number Cards
	cards_data = [
		{
			"label": "In Progress Drafts",
			"function": "Count",
			"document_type": "Content Item",
			"filters_json": '[["Content Item","workflow_state","=","In Progress"]]',
			"color": "#3B82F6"
		},
		{
			"label": "In Technical Review",
			"function": "Count",
			"document_type": "Content Item",
			"filters_json": '[["Content Item","workflow_state","=","In Review"]]',
			"color": "#F59E0B"
		},
		{
			"label": "Approved for Publishing",
			"function": "Count",
			"document_type": "Content Item",
			"filters_json": '[["Content Item","workflow_state","=","Approved"]]',
			"color": "#10B981"
		},
		{
			"label": "Published Deliverables",
			"function": "Count",
			"document_type": "Content Item",
			"filters_json": '[["Content Item","workflow_state","=","Published"]]',
			"color": "#8B5CF6"
		}
	]

	for card in cards_data:
		if not frappe.db.exists("Number Card", card["label"]):
			frappe.get_doc({
				"doctype": "Number Card",
				"name": card["label"],
				"label": card["label"],
				"document_type": card["document_type"],
				"function": card["function"],
				"filters_json": card["filters_json"],
				"color": card["color"],
				"is_public": 1,
				"module": "ODA Marketing"
			}).insert(ignore_permissions=True)
			print(f"Created Number Card: {card['label']}")

	# 2. Setup Dashboard Charts
	charts_data = [
		{
			"chart_name": "Content Items by Workflow State",
			"chart_type": "Group By",
			"group_by_type": "Count",
			"group_by_based_on": "workflow_state",
			"document_type": "Content Item",
			"type": "Donut",
			"is_public": 1,
			"module": "ODA Marketing"
		},
		{
			"chart_name": "Content Items by Format",
			"chart_type": "Group By",
			"group_by_type": "Count",
			"group_by_based_on": "content_type",
			"document_type": "Content Item",
			"type": "Donut",
			"is_public": 1,
			"module": "ODA Marketing"
		},
		{
			"chart_name": "Deliverables by Publish Month",
			"chart_type": "Count",
			"based_on": "planned_publish_date",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"document_type": "Content Item",
			"type": "Bar",
			"is_public": 1,
			"module": "ODA Marketing"
		},
		{
			"chart_name": "Content Items by Domain",
			"chart_type": "Group By",
			"group_by_type": "Count",
			"group_by_based_on": "industry_domain",
			"document_type": "Content Item",
			"type": "Bar",
			"is_public": 1,
			"module": "ODA Marketing"
		}
	]

	for chart in charts_data:
		if not frappe.db.exists("Dashboard Chart", chart["chart_name"]):
			frappe.get_doc({
				"doctype": "Dashboard Chart",
				"name": chart["chart_name"],
				"chart_name": chart["chart_name"],
				"chart_type": chart["chart_type"],
				"group_by_type": chart.get("group_by_type"),
				"group_by_based_on": chart.get("group_by_based_on"),
				"based_on": chart.get("based_on"),
				"timespan": chart.get("timespan"),
				"time_interval": chart.get("time_interval"),
				"document_type": chart["document_type"],
				"type": chart["type"],
				"filters_json": "[]",
				"is_public": 1,
				"module": "ODA Marketing"
			}).insert(ignore_permissions=True)
			print(f"Created Dashboard Chart: {chart['chart_name']}")

	# 3. Setup Dashboard record for Content Item
	dashboard_name = "Content Item"
	if frappe.db.exists("Dashboard", dashboard_name):
		return

	dash = frappe.get_doc({
		"doctype": "Dashboard",
		"name": dashboard_name,
		"dashboard_name": dashboard_name,
		"module": "ODA Marketing",
		"is_default": 1,
		"cards": [
			{"card": "In Progress Drafts"},
			{"card": "In Technical Review"},
			{"card": "Approved for Publishing"},
			{"card": "Published Deliverables"}
		],
		"charts": [
			{"chart": "Content Items by Workflow State", "width": "Half"},
			{"chart": "Content Items by Format", "width": "Half"},
			{"chart": "Deliverables by Publish Month", "width": "Half"},
			{"chart": "Content Items by Domain", "width": "Half"}
		]
	})
	dash.insert(ignore_permissions=True)
	print(f"Created native Dashboard: {dashboard_name}")


def run_setup():
	setup_roles()
	setup_content_item_options()
	setup_email_templates_and_settings()
	setup_workflow()
	setup_kanban_board()
	setup_content_item_dashboard()
	setup_workspace_sidebar()
	setup_desktop_icon()
