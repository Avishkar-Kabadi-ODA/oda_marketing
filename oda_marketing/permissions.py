# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe


def has_app_permission(user=None):
	return True


def get_content_item_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user) or "Marketing Lead" in frappe.get_roles(user):
		return ""

	user_esc = frappe.db.escape(user)
	return f"(`tabContent Item`.assigned_to = {user_esc} OR `tabContent Item`.reviewer_technical = {user_esc} OR `tabContent Item`.reviewer_business = {user_esc} OR `tabContent Item`.owner = {user_esc})"


def has_content_item_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user) or "Marketing Lead" in frappe.get_roles(user):
		return True

	if doc.assigned_to == user or doc.reviewer_technical == user or doc.reviewer_business == user or doc.owner == user:
		return True

	return False


def get_content_brief_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user) or "Marketing Lead" in frappe.get_roles(user):
		return ""

	user_esc = frappe.db.escape(user)
	return f"(`tabContent Brief`.owner = {user_esc} OR `tabContent Brief`.content_item IN (SELECT name FROM `tabContent Item` WHERE assigned_to = {user_esc} OR reviewer_technical = {user_esc} OR reviewer_business = {user_esc} OR owner = {user_esc}))"


def has_content_brief_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user) or "Marketing Lead" in frappe.get_roles(user):
		return True

	if doc.owner == user:
		return True

	if doc.content_item:
		item = frappe.get_doc("Content Item", doc.content_item)
		return has_content_item_permission(item, ptype=ptype, user=user)

	return True
