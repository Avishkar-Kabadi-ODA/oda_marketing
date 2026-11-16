# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password


class EnvVariable(Document):
	def get_password_value(self):
		"""Safely retrieve decrypted password value from DB."""
		return get_decrypted_password("Env Variable", self.name, fieldname="value")


@frappe.whitelist()
def get_env_var(variable_name, default=None):
	"""Return a configured secret only to users with Env Variable read access."""
	if not frappe.has_permission("Env Variable", "read"):
		frappe.throw(_("You do not have permission to read environment variables."), frappe.PermissionError)

	if frappe.db.exists("Env Variable", variable_name):
		doc = frappe.get_doc("Env Variable", variable_name)
		doc.check_permission("read")
		val = doc.get_password_value()
		if val:
			return val

	return default
