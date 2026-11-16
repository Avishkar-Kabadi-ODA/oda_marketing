# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def has_app_permission(user=None):
	if not user:
		user = frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	allowed = {"System Manager", "Marketing Lead", "Desk User", "Employee"}
	return bool(allowed & set(roles))


def get_default_publisher():
	try:
		return frappe.db.get_single_value("Marketing Settings", "default_publisher")
	except Exception:
		return None


def is_content_item_publisher(user, doc):
	user_lower = (user or "").lower()
	if user_lower and user_lower == (get_default_publisher() or "").lower():
		return True
	if not doc or not getattr(doc, "content_type", None):
		return False
	publisher = frappe.db.get_value(
		"Content Item Option",
		doc.content_type,
		"default_publisher",
	)
	return bool(publisher and user_lower == publisher.lower())


def safe_escape(val):
	try:
		if getattr(frappe, "db", None) and hasattr(frappe.db, "escape"):
			return frappe.db.escape(val)
	except Exception:
		pass
	clean = str(val or "").replace("'", "''")
	return f"'{clean}'"


def get_content_item_permission_query_conditions(user=None):
	if not user:
		user = getattr(getattr(frappe, "session", None), "user", None) or "Administrator"

	user_lower = (user or "").lower()
	publisher = get_default_publisher()
	publisher_lower = (publisher or "").lower()

	try:
		roles = frappe.get_roles(user)
	except Exception:
		roles = []

	if user == "Administrator" or "System Manager" in roles or "Marketing Lead" in roles or user_lower == publisher_lower:
		return ""

	user_esc = safe_escape(user_lower)
	# Non-leads can ONLY see items assigned to them or where they are the reviewer, AND only once moved out of 'Planned' state
	return f"""(
		(LOWER(`tabContent Item`.assigned_to) = {user_esc} AND IFNULL(`tabContent Item`.workflow_state, 'Planned') != 'Planned')
		OR (LOWER(`tabContent Item`.reviewer_technical) = {user_esc} AND IFNULL(`tabContent Item`.workflow_state, 'Planned') != 'Planned')
		OR (
			IFNULL(`tabContent Item`.workflow_state, 'Planned') IN ('Approved', 'Published')
			AND EXISTS (
				SELECT 1 FROM `tabContent Item Option`
				WHERE `tabContent Item Option`.name = `tabContent Item`.content_type
				AND LOWER(`tabContent Item Option`.default_publisher) = {user_esc}
			)
		)
	)"""


def has_content_item_permission(doc, ptype="read", user=None):
	if not user:
		user = getattr(getattr(frappe, "session", None), "user", None) or "Administrator"

	user_lower = (user or "").lower()
	publisher = get_default_publisher()
	publisher_lower = (publisher or "").lower()

	try:
		roles = frappe.get_roles(user)
	except Exception:
		roles = []

	is_lead = user == "Administrator" or "System Manager" in roles or "Marketing Lead" in roles or user_lower == publisher_lower

	if is_lead:
		return True

	# Creation and deletion rights are strictly restricted to Marketing Leads / System Managers
	if ptype in ["delete", "create"]:
		return False

	if doc and not isinstance(doc, str):
		state = getattr(doc, "workflow_state", None) or getattr(doc, "status", None) or "Planned"
		if state in ("Approved", "Published") and is_content_item_publisher(user, doc):
			return ptype in ("read", "write", "email", "print")

	# If doc is None or a string (DocType-level permission check), allow baseline read/write for Desk Users
	if not doc or isinstance(doc, str):
		return True

	# Non-leads cannot view or edit items while in Planned state
	state = getattr(doc, "workflow_state", None) or getattr(doc, "status", None) or "Planned"
	if state == "Planned":
		return False

	assigned = (getattr(doc, "assigned_to", None) or "").lower()
	tech_rev = (getattr(doc, "reviewer_technical", None) or "").lower()

	if user_lower in [assigned, tech_rev]:
		return True

	return False


def validate_user_marketing_roles(doc, method=None):
	"""No-op: Users can hold Marketing Lead, Technical Reviewer, or multiple roles simultaneously."""
	pass
