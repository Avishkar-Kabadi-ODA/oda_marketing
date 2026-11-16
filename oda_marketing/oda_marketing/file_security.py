# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import os
from urllib.parse import urlsplit

import frappe
from frappe import _
from frappe.utils import get_site_path


def resolve_site_file(file_url, max_bytes, attached_to=None):
	"""Resolve a Frappe File under site storage and enforce ownership and size limits."""
	path = urlsplit(str(file_url or "")).path
	if not path.startswith(("/files/", "/private/files/")):
		frappe.throw(_("The file must be a site attachment."), frappe.ValidationError)

	file_name = frappe.db.get_value("File", {"file_url": path}, "name")
	if not file_name:
		return None, None

	file_doc = frappe.get_doc("File", file_name)
	file_doc.check_permission("read")
	if attached_to and (
		file_doc.attached_to_doctype != attached_to[0]
		or file_doc.attached_to_name != attached_to[1]
	):
		frappe.throw(_("The file is not attached to this Content Item."), frappe.PermissionError)

	full_path = os.path.realpath(file_doc.get_full_path())
	site_roots = (
		os.path.realpath(get_site_path("public", "files")),
		os.path.realpath(get_site_path("private", "files")),
	)
	if not any(os.path.commonpath((root, full_path)) == root for root in site_roots):
		frappe.throw(_("The file path is outside the site's file storage."), frappe.PermissionError)

	if os.path.getsize(full_path) > max_bytes:
		frappe.throw(_("The file exceeds the maximum supported size."), frappe.ValidationError)

	return file_doc, full_path
