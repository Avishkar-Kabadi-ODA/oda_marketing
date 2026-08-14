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
	allowed = {"System Manager", "Marketing Lead", "Content Writer", "Technical Reviewer"}
	return bool(allowed & set(roles))


def get_default_publisher():
	try:
		return frappe.db.get_single_value("Marketing Settings", "default_publisher")
	except Exception:
		return None


def get_content_item_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	user_lower = (user or "").lower()
	publisher = get_default_publisher()
	publisher_lower = (publisher or "").lower()

	roles = frappe.get_roles(user)
	if user == "Administrator" or "System Manager" in roles or "Marketing Lead" in roles or user_lower == publisher_lower:
		return ""

	user_esc = frappe.db.escape(user_lower)
	return f"(LOWER(`tabContent Item`.assigned_to) = {user_esc} OR LOWER(`tabContent Item`.reviewer_technical) = {user_esc} OR LOWER(`tabContent Item`.owner) = {user_esc})"


def has_content_item_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user

	user_lower = (user or "").lower()
	publisher = get_default_publisher()
	publisher_lower = (publisher or "").lower()

	roles = frappe.get_roles(user)
	is_lead = user == "Administrator" or "System Manager" in roles or "Marketing Lead" in roles or user_lower == publisher_lower

	if is_lead:
		return True

	# Creation and deletion rights are strictly restricted to Marketing Leads / System Managers
	if ptype in ["delete", "create"]:
		return False

	assigned = (doc.assigned_to or "").lower()
	tech_rev = (doc.reviewer_technical or "").lower()
	owner = (doc.owner or "").lower()

	if user_lower in [assigned, tech_rev, owner]:
		return True

	return False


def validate_user_marketing_roles(doc, method=None):
	"""
	Enforces mutual exclusivity among marketing roles:
	A user cannot hold more than ONE of: Marketing Lead, Content Writer, Technical Reviewer.
	"""
	marketing_roles = {"Marketing Lead", "Content Writer", "Technical Reviewer"}
	assigned_marketing_roles = [
		r.role for r in (doc.roles or [])
		if r.role in marketing_roles
	]

	if len(assigned_marketing_roles) > 1:
		roles_list_str = ", ".join(f"<b>{r}</b>" for r in sorted(assigned_marketing_roles))
		frappe.throw(
			_("A user cannot hold multiple marketing roles simultaneously ({0}). A user can be assigned only ONE role among: <b>Marketing Lead</b>, <b>Content Writer</b>, or <b>Technical Reviewer</b>.").format(roles_list_str),
			frappe.ValidationError
		)
