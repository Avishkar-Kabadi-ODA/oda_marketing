# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe


def has_app_permission(user=None):
	return True


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
	if user == "Administrator" or "System Manager" in roles or "Marketing Lead" in roles or user_lower == publisher_lower:
		return True

	assigned = (doc.assigned_to or "").lower()
	tech_rev = (doc.reviewer_technical or "").lower()
	owner = (doc.owner or "").lower()

	if user_lower in [assigned, tech_rev, owner]:
		return True

	return False
