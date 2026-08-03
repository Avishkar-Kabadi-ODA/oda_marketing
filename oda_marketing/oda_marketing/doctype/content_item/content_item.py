# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, get_url


class ContentItem(Document):
	def validate(self):
		self.validate_creation_permissions()
		self.validate_metadata_edit_permissions()
		self.sync_status_with_workflow()
		self.validate_publish_date_with_calendar()
		self.calculate_sla_due_date()
		self.check_overdue_sla()
		self.validate_content_brief_mandatory()
		self.validate_primary_attachment_mandatory()
		self.validate_revision_notes()

	def before_insert(self):
		if self.assigned_to:
			self.owner = self.assigned_to
		self.sync_status_with_workflow()

	def is_lead_user(self):
		user = frappe.session.user
		if user == "Administrator":
			return True
		roles = frappe.get_roles(user)
		return "Marketing Lead" in roles or "System Manager" in roles

	def validate_creation_permissions(self):
		if self.is_new() and not self.is_lead_user():
			frappe.throw(_("Only <b>Marketing Leads</b> can create new Content Items."), frappe.PermissionError)

	def validate_metadata_edit_permissions(self):
		if not self.is_new() and not self.is_lead_user():
			before = self.get_doc_before_save()
			if not before:
				return
			metadata_fields = [
				"title", "content_type", "topic", "practice_area",
				"content_calendar", "planned_publish_date", "assigned_to",
				"reviewer_technical", "reviewer_business"
			]
			for field in metadata_fields:
				if getattr(self, field, None) != getattr(before, field, None):
					frappe.throw(_("Only <b>Marketing Leads</b> are permitted to modify core item metadata ({0}).").format(field), frappe.PermissionError)

	def sync_status_with_workflow(self):
		wf_state = getattr(self, "workflow_state", None)
		if wf_state:
			self.status = wf_state
		elif not getattr(self, "status", None):
			self.status = "Planned"

	def validate_publish_date_with_calendar(self):
		if self.content_calendar and self.planned_publish_date:
			cal = frappe.get_doc("Content Calendar", self.content_calendar)
			pub_date = getdate(self.planned_publish_date)
			if cal.from_date and pub_date < getdate(cal.from_date):
				frappe.throw(_("Planned Publish Date ({0}) cannot be before Content Calendar start date ({1}).").format(self.planned_publish_date, cal.from_date))
			if cal.to_date and pub_date > getdate(cal.to_date):
				frappe.throw(_("Planned Publish Date ({0}) cannot be after Content Calendar end date ({1}).").format(self.planned_publish_date, cal.to_date))

	def calculate_sla_due_date(self):
		if not self.planned_publish_date:
			return

		dt = getdate(self.planned_publish_date)
		offsets = {
			"Blog": -30,
			"Poll": -7,
			"Flowchart": -14,
			"Carousel": -14
		}
		offset = offsets.get(self.content_type, -14)
		self.sla_due_date = add_days(dt, offset)

	def check_overdue_sla(self):
		if self.sla_due_date and getattr(self, "workflow_state", None) not in ["Approved", "Published"]:
			if getdate(nowdate()) > getdate(self.sla_due_date):
				self.risk_flag = "Late"

	def validate_content_brief_mandatory(self):
		if getattr(self, "workflow_state", None) == "Briefed" and not self.content_brief:
			frappe.throw(_("<b>Content Brief is mandatory</b> before issuing a brief or setting status to 'Briefed'. Please create and link a Content Brief first."))

	def validate_primary_attachment_mandatory(self):
		if getattr(self, "workflow_state", None) == "In Review - Technical" and not self.content_file_1:
			frappe.throw(_("<b>Primary Content File (content_file_1)</b> is mandatory before submitting for review."))

	def validate_revision_notes(self):
		if getattr(self, "workflow_state", None) == "In Revision" and not (self.revision_feedback_notes and self.revision_feedback_notes.strip()):
			frappe.throw(_("Revision Feedback / Notes are mandatory when requesting changes or sending an item to 'In Revision'."))

	def get_user_full_name(self, user_email):
		if not user_email:
			return "Team Member"
		first_name, last_name = frappe.db.get_value("User", user_email, ["first_name", "last_name"]) or (None, None)
		if first_name:
			return f"{first_name} {last_name or ''}".strip()
		return user_email

	def get_file_link_html(self, file_path, label="View Primary File"):
		if not file_path:
			return "<span>No File Attached</span>"
		full_url = get_url(file_path)
		return f'<a href="{full_url}" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: 600;">{label}</a>'

	def get_template_context(self):
		settings = frappe.get_single("Marketing Settings")
		publisher_email = settings.default_publisher if hasattr(settings, "default_publisher") else None

		context = {
			"doc": self,
			"assigned_to_name": self.get_user_full_name(self.assigned_to),
			"reviewer_technical_name": self.get_user_full_name(self.reviewer_technical),
			"reviewer_business_name": self.get_user_full_name(self.reviewer_business),
			"publisher_name": self.get_user_full_name(publisher_email),
			"content_file_1_link": self.get_file_link_html(self.content_file_1, "View Primary Deliverable"),
			"content_file_2_link": self.get_file_link_html(self.content_file_2, "View Supporting Asset 1"),
			"content_file_3_link": self.get_file_link_html(self.content_file_3, "View Supporting Asset 2"),
		}
		return context

	def on_update(self):
		self.trigger_workflow_notifications()

	def trigger_workflow_notifications(self):
		settings = frappe.get_single("Marketing Settings")
		if not settings.enable_email_notifications:
			return

		previous_state = self.get_doc_before_save().workflow_state if self.get_doc_before_save() else None
		current_state = self.workflow_state

		if previous_state == current_state or not current_state:
			return

		recipients = set()
		cc = set()
		template_name = None

		publisher_email = getattr(settings, "default_publisher", None)

		if current_state == "Briefed":
			if self.assigned_to:
				recipients.add(self.assigned_to)
			template_name = settings.writer_email_template

		elif current_state == "In Review - Technical":
			if self.reviewer_technical:
				recipients.add(self.reviewer_technical)
			if self.reviewer_business and self.reviewer_business != self.reviewer_technical:
				cc.add(self.reviewer_business)
			template_name = settings.reviewer_email_template

		elif current_state == "In Review - Business":
			if self.reviewer_business:
				recipients.add(self.reviewer_business)
			template_name = settings.reviewer_email_template

		elif current_state == "In Revision":
			if self.assigned_to:
				recipients.add(self.assigned_to)
			template_name = settings.writer_email_template

		elif current_state == "Approved":
			if publisher_email:
				recipients.add(publisher_email)
			if self.assigned_to:
				cc.add(self.assigned_to)
			template_name = settings.publisher_email_template

		elif current_state == "Published":
			if self.assigned_to:
				recipients.add(self.assigned_to)
			if publisher_email:
				cc.add(publisher_email)
			template_name = settings.publisher_email_template

		if recipients and template_name and frappe.db.exists("Email Template", template_name):
			try:
				tmpl = frappe.get_doc("Email Template", template_name)
				ctx = self.get_template_context()

				subject = frappe.render_template(tmpl.subject, ctx)
				message = frappe.render_template(tmpl.response, ctx)

				frappe.sendmail(
					recipients=list(recipients),
					cc=list(cc),
					subject=subject,
					message=message,
					now=True
				)
			except Exception as e:
				frappe.log_error(f"Failed to send workflow email for Content Item {self.name}: {str(e)}")


def send_overdue_sla_notifications():
	"""Scheduled job / function to alert involved parties for late items using Marketing Settings template."""
	settings = frappe.get_single("Marketing Settings")
	if not settings.enable_email_notifications:
		return

	template_name = settings.overdue_sla_email_template
	if not (template_name and frappe.db.exists("Email Template", template_name)):
		return

	tmpl = frappe.get_doc("Email Template", template_name)

	overdue_items = frappe.get_all(
		"Content Item",
		filters={
			"risk_flag": "Late",
			"workflow_state": ["not in", ["Approved", "Published"]]
		},
		fields=["name"]
	)

	for item_data in overdue_items:
		item = frappe.get_doc("Content Item", item_data.name)
		recipients = set()
		if item.assigned_to:
			recipients.add(item.assigned_to)
		if item.reviewer_technical:
			recipients.add(item.reviewer_technical)
		if item.reviewer_business:
			recipients.add(item.reviewer_business)

		if recipients:
			try:
				ctx = item.get_template_context()
				subject = frappe.render_template(tmpl.subject, ctx)
				message = frappe.render_template(tmpl.response, ctx)

				frappe.sendmail(
					recipients=list(recipients),
					subject=subject,
					message=message,
					now=True
				)
			except Exception as e:
				frappe.log_error(f"Failed to send overdue email for {item.name}: {str(e)}")
