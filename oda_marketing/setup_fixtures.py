# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe


def setup_roles():
	roles = [
		{"role_name": "Marketing User", "desk_access": 1},
		{"role_name": "Marketing Lead", "desk_access": 1},
		{"role_name": "Marketing Manager", "desk_access": 1},
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


def setup_workflow_states_and_actions():
	state_names = [
		"Planned", "Briefing", "Drafting", "In Review",
		"Revisions", "Approved", "Scheduled", "Published"
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
		"Start Briefing", "Submit Brief", "Submit for Review",
		"Request Changes", "Approve Content", "Resubmit Draft",
		"Schedule Content", "Publish Content"
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
		{"state": "Planned", "doc_status": "0", "allow_edit": "Marketing User", "style": "Primary"},
		{"state": "Briefing", "doc_status": "0", "allow_edit": "Marketing User", "style": "Info"},
		{"state": "Drafting", "doc_status": "0", "allow_edit": "Marketing User", "style": "Warning"},
		{"state": "In Review", "doc_status": "0", "allow_edit": "Marketing Lead", "style": "Warning"},
		{"state": "Revisions", "doc_status": "0", "allow_edit": "Marketing User", "style": "Inverse"},
		{"state": "Approved", "doc_status": "0", "allow_edit": "Marketing Manager", "style": "Success"},
		{"state": "Scheduled", "doc_status": "0", "allow_edit": "Marketing Manager", "style": "Info"},
		{"state": "Published", "doc_status": "0", "allow_edit": "Marketing Manager", "style": "Success"},
	]

	transitions = [
		# Planned -> Briefing
		{"state": "Planned", "action": "Start Briefing", "next_state": "Briefing", "allowed": "Marketing User"},
		{"state": "Planned", "action": "Start Briefing", "next_state": "Briefing", "allowed": "Marketing Lead"},
		{"state": "Planned", "action": "Start Briefing", "next_state": "Briefing", "allowed": "Marketing Manager"},
		{"state": "Planned", "action": "Start Briefing", "next_state": "Briefing", "allowed": "System Manager"},

		# Briefing -> Drafting
		{"state": "Briefing", "action": "Submit Brief", "next_state": "Drafting", "allowed": "Marketing User"},
		{"state": "Briefing", "action": "Submit Brief", "next_state": "Drafting", "allowed": "Marketing Lead"},
		{"state": "Briefing", "action": "Submit Brief", "next_state": "Drafting", "allowed": "Marketing Manager"},
		{"state": "Briefing", "action": "Submit Brief", "next_state": "Drafting", "allowed": "System Manager"},

		# Drafting -> In Review
		{"state": "Drafting", "action": "Submit for Review", "next_state": "In Review", "allowed": "Marketing User"},
		{"state": "Drafting", "action": "Submit for Review", "next_state": "In Review", "allowed": "Marketing Lead"},
		{"state": "Drafting", "action": "Submit for Review", "next_state": "In Review", "allowed": "Marketing Manager"},
		{"state": "Drafting", "action": "Submit for Review", "next_state": "In Review", "allowed": "System Manager"},

		# In Review -> Revisions
		{"state": "In Review", "action": "Request Changes", "next_state": "Revisions", "allowed": "Marketing Lead"},
		{"state": "In Review", "action": "Request Changes", "next_state": "Revisions", "allowed": "Marketing Manager"},
		{"state": "In Review", "action": "Request Changes", "next_state": "Revisions", "allowed": "System Manager"},

		# In Review -> Approved
		{"state": "In Review", "action": "Approve Content", "next_state": "Approved", "allowed": "Marketing Lead"},
		{"state": "In Review", "action": "Approve Content", "next_state": "Approved", "allowed": "Marketing Manager"},
		{"state": "In Review", "action": "Approve Content", "next_state": "Approved", "allowed": "System Manager"},

		# Revisions -> In Review
		{"state": "Revisions", "action": "Resubmit Draft", "next_state": "In Review", "allowed": "Marketing User"},
		{"state": "Revisions", "action": "Resubmit Draft", "next_state": "In Review", "allowed": "Marketing Lead"},
		{"state": "Revisions", "action": "Resubmit Draft", "next_state": "In Review", "allowed": "Marketing Manager"},
		{"state": "Revisions", "action": "Resubmit Draft", "next_state": "In Review", "allowed": "System Manager"},

		# Approved -> Scheduled
		{"state": "Approved", "action": "Schedule Content", "next_state": "Scheduled", "allowed": "Marketing Manager"},
		{"state": "Approved", "action": "Schedule Content", "next_state": "Scheduled", "allowed": "System Manager"},

		# Scheduled -> Published
		{"state": "Scheduled", "action": "Publish Content", "next_state": "Published", "allowed": "Marketing Manager"},
		{"state": "Scheduled", "action": "Publish Content", "next_state": "Published", "allowed": "System Manager"},
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
		{"column_name": "Briefing", "status": "Active", "indicator": "Light Blue"},
		{"column_name": "Drafting", "status": "Active", "indicator": "Orange"},
		{"column_name": "In Review", "status": "Active", "indicator": "Yellow"},
		{"column_name": "Revisions", "status": "Active", "indicator": "Red"},
		{"column_name": "Approved", "status": "Active", "indicator": "Cyan"},
		{"column_name": "Scheduled", "status": "Active", "indicator": "Blue"},
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

	items = [
		{
			"type": "Section Break",
			"label": "Campaign Planning",
			"icon": "calendar",
			"collapsible": 1,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Content Calendar",
			"label": "Content Calendar",
			"icon": "calendar",
			"child": 1,
		},
		{
			"type": "Section Break",
			"label": "Content Execution",
			"icon": "list-checks",
			"collapsible": 1,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Content Item",
			"label": "Content Item",
			"icon": "list-checks",
			"child": 1,
		},
		{
			"type": "Link",
			"link_type": "DocType",
			"link_to": "Content Brief",
			"label": "Content Brief",
			"icon": "file-text",
			"child": 1,
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
	print(f"Created Workspace Sidebar: {sidebar_name}")


def run_setup():
	setup_roles()
	setup_workflow()
	setup_kanban_board()
	setup_workspace_sidebar()
	frappe.db.commit()
