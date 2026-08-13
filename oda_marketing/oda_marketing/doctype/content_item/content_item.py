# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, now_datetime, get_url


class ContentItem(Document):
	def validate(self):
		self.validate_creation_permissions()
		self.validate_metadata_edit_permissions()
		self.validate_writer_readonly_before_briefed()
		self.sync_status_with_workflow()
		self.validate_publish_date_with_calendar()
		self.check_overdue_sla()
		self.validate_primary_attachment_mandatory()
		self.validate_technical_reviewer_mandatory()
		self.validate_revision_notes()
		self.validate_published_url_mandatory()
		self.stamp_brief_accepted_on()

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
		if frappe.flags.ignore_permissions or self.flags.ignore_permissions:
			return
		if self.is_new() and not self.is_lead_user():
			frappe.throw(_("Only <b>Marketing Leads</b> can create new Content Items."), frappe.PermissionError)

	def validate_metadata_edit_permissions(self):
		if frappe.flags.ignore_permissions or self.flags.ignore_permissions:
			return
		if not self.is_new() and not self.is_lead_user():
			before = self.get_doc_before_save()
			if not before:
				return
			# sla_due_date is explicitly excluded — Content Writers can edit Due Date
			metadata_fields = [
				"title", "content_type", "topic", "practice_area",
				"content_calendar", "planned_publish_date", "assigned_to",
				"reviewer_technical"
			]
			for field in metadata_fields:
				val_self = getattr(self, field, None)
				val_before = getattr(before, field, None)

				if field in ["planned_publish_date"]:
					if val_self and val_before and getdate(val_self) != getdate(val_before):
						frappe.throw(_("Only <b>Marketing Leads</b> are permitted to modify core item metadata ({0}).").format(field), frappe.PermissionError)
				else:
					if str(val_self or "") != str(val_before or ""):
						frappe.throw(_("Only <b>Marketing Leads</b> are permitted to modify core item metadata ({0}).").format(field), frappe.PermissionError)

	def validate_writer_readonly_before_briefed(self):
		"""Content Writer cannot edit attachments or notes while item is in Planned state."""
		if frappe.flags.ignore_permissions or self.flags.ignore_permissions:
			return
		if self.is_lead_user():
			return
		if getattr(self, "workflow_state", None) != "Planned":
			return

		before = self.get_doc_before_save()
		if not before:
			return

		attachment_fields = ["content_file_1", "content_file_2", "content_file_3", "notes"]
		for field in attachment_fields:
			val_self = getattr(self, field, None)
			val_before = getattr(before, field, None)
			if str(val_self or "") != str(val_before or ""):
				frappe.throw(
					_("Content Writers cannot edit attachments or notes while the item is in <b>Planned</b> state. Wait until the brief is issued."),
					frappe.PermissionError
				)

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

	def check_overdue_sla(self):
		if self.sla_due_date and getattr(self, "workflow_state", None) not in ["Approved", "Published"]:
			if getdate(nowdate()) > getdate(self.sla_due_date):
				self.risk_flag = "Late"

	def validate_primary_attachment_mandatory(self):
		target_states = ["Marketing Copilot Review", "In Review", "Approved", "Published"]
		if getattr(self, "workflow_state", None) in target_states and not self.content_file_1:
			frappe.throw(_("<b>Primary Content Draft (content_file_1)</b> is mandatory before submitting for review or publishing."))

	def validate_technical_reviewer_mandatory(self):
		if getattr(self, "workflow_state", None) == "In Review" and not self.reviewer_technical:
			frappe.throw(_("<b>Reviewer</b> must be assigned before submitting for Review."))

	def validate_revision_notes(self):
		if getattr(self, "workflow_state", None) == "In Revision" and not getattr(self, "revision_feedback_notes", None):
			frappe.throw(_("<b>Revision Feedback / Notes</b> are mandatory when requesting revisions."))

	def validate_published_url_mandatory(self):
		if getattr(self, "workflow_state", None) == "Published" and not getattr(self, "published_url", None):
			frappe.throw(_("<b>Published URL</b> is mandatory when marking a deliverable as Published."))

	def stamp_brief_accepted_on(self):
		"""Auto-stamp brief_accepted_on when writer transitions from Briefed to In Progress."""
		if getattr(self, "workflow_state", None) == "In Progress" and not getattr(self, "brief_accepted_on", None):
			before = self.get_doc_before_save()
			if before and getattr(before, "workflow_state", None) == "Briefed":
				self.brief_accepted_on = now_datetime()

	def get_user_full_name(self, user_email):
		if not user_email:
			return "Team Member"
		first_name, last_name = frappe.db.get_value("User", user_email, ["first_name", "last_name"]) or (None, None)
		if first_name:
			return f"{first_name} {last_name or ''}".strip()

		if "@" in user_email:
			username_part = user_email.split("@")[0]
			formatted = username_part.replace(".", " ").replace("_", " ").title()
			return formatted

		return user_email

	def get_file_link_html(self, file_path, label="View Primary Draft"):
		if not file_path:
			return ""
		full_url = get_url(file_path)
		return f'<a href="{full_url}" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: 600;">{label}</a>'

	def get_template_context(self):
		settings = frappe.get_single("Marketing Settings")
		publisher_email = settings.default_publisher if hasattr(settings, "default_publisher") else None
		item_url = get_url(f"/app/content-item/{self.name}")

		context = {
			"doc": self,
			"content_item_url": item_url,
			"creator_name": self.get_user_full_name(self.owner),
			"assigned_to_name": self.get_user_full_name(self.assigned_to),
			"reviewer_technical_name": self.get_user_full_name(self.reviewer_technical),
			"publisher_name": self.get_user_full_name(publisher_email),
			"content_file_1_link": self.get_file_link_html(self.content_file_1, "View Primary Content Draft"),
			"content_file_2_link": self.get_file_link_html(self.content_file_2, "View Supporting Asset 1"),
			"content_file_3_link": self.get_file_link_html(self.content_file_3, "View Supporting Asset 2"),
		}
		return context

	def on_update(self):
		self.trigger_workflow_notifications()
		self.trigger_system_notifications()
		self.trigger_ai_copilot_review()

	def trigger_ai_copilot_review(self):
		if getattr(frappe.flags, "in_ai_copilot_review", False):
			return

		settings = frappe.get_single("Marketing Settings")
		if not getattr(settings, "enable_ai_copilot", 0):
			return

		if getattr(self, "workflow_state", None) == "Marketing Copilot Review":
			if getattr(self, "ai_review_status", None) not in ["In Progress", "Completed", "Queued"]:
				# Check usage limit before queuing (Writer limit)
				max_reviews = int(getattr(settings, "max_writer_copilot_reviews_per_item", 3) or 3)
				current_count = len([r for r in (self.ai_reviews or []) if r.get("review_type") == "Writer"])
				if current_count >= max_reviews:
					frappe.msgprint(
						_("Writer Copilot review limit reached ({0}/{1}). No additional AI reviews will be triggered.").format(current_count, max_reviews),
						indicator="orange",
						alert=True
					)
					return

				self.db_set("ai_review_status", "Queued", update_modified=False)
				try:
					from oda_marketing.oda_marketing.ai_engine.runner import run_ai_review
					run_ai_review(self.name, review_type="Writer")
				except Exception as e:
					frappe.log_error(f"AI Copilot review execution error for {self.name}: {str(e)}")

	def trigger_system_notifications(self):
		"""Sends targeted Frappe In-App Bell 🔔 Notifications to the specific user involved."""
		previous_doc = self.get_doc_before_save()
		previous_state = getattr(self.flags, "previous_workflow_state", None) or (previous_doc.workflow_state if previous_doc else None)
		current_state = self.workflow_state

		if previous_state == current_state or not current_state:
			return

		target_user = None
		subject = None

		if current_state == "Briefed" and self.assigned_to:
			target_user = self.assigned_to
			subject = f"Assigned Deliverable: '{self.title}' (Brief Issued)"

		elif current_state == "In Review" and self.reviewer_technical:
			target_user = self.reviewer_technical
			subject = f"Review Required: '{self.title}'"

		elif current_state == "In Revision" and self.assigned_to:
			target_user = self.assigned_to
			subject = f"Revisions Requested: '{self.title}'"

		elif current_state == "Approved":
			settings = frappe.get_single("Marketing Settings")
			publisher = getattr(settings, "default_publisher", None)
			if publisher:
				target_user = publisher
				subject = f"Approved for Publishing: '{self.title}'"

		elif current_state == "Published" and self.assigned_to:
			target_user = self.assigned_to
			subject = f"Congratulations! Deliverable Published: '{self.title}'"

		if target_user and subject:
			try:
				if frappe.db.exists("User", target_user):
					doc_n = frappe.get_doc({
						"doctype": "Notification Log",
						"subject": subject,
						"for_user": target_user,
						"type": "Alert",
						"document_type": "Content Item",
						"document_name": self.name,
						"email_content": f"Deliverable '{self.title}' status is now {current_state}."
					})
					doc_n.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Failed to insert in-app Notification Log for {target_user}: {str(e)}")

	def trigger_workflow_notifications(self):
		settings = frappe.get_single("Marketing Settings")
		if not settings.enable_email_notifications:
			return

		previous_doc = self.get_doc_before_save()
		previous_state = getattr(self.flags, "previous_workflow_state", None) or (previous_doc.workflow_state if previous_doc else None)
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
			if self.owner and self.owner != self.assigned_to:
				cc.add(self.owner)
			template_name = settings.writer_email_template

		elif current_state == "In Review":
			if self.reviewer_technical:
				recipients.add(self.reviewer_technical)
			if self.assigned_to and self.assigned_to != self.reviewer_technical:
				cc.add(self.assigned_to)
			if self.owner and self.owner != self.reviewer_technical:
				cc.add(self.owner)
			if publisher_email and publisher_email != self.reviewer_technical:
				cc.add(publisher_email)
			template_name = settings.reviewer_email_template

		elif current_state == "In Revision":
			if self.assigned_to:
				recipients.add(self.assigned_to)
			if self.owner and self.owner != self.assigned_to:
				cc.add(self.owner)
			template_name = settings.writer_email_template

		elif current_state == "Approved":
			if publisher_email:
				recipients.add(publisher_email)
			if self.owner and self.owner != publisher_email:
				cc.add(self.owner)
			if self.assigned_to and self.assigned_to != publisher_email:
				cc.add(self.assigned_to)
			template_name = settings.publisher_email_template

		elif current_state == "Published":
			if self.assigned_to:
				recipients.add(self.assigned_to)
			template_name = getattr(settings, "published_email_template", None)

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
					now=False
				)
			except Exception as e:
				frappe.log_error(f"Failed to send workflow email for Content Item {self.name}: {str(e)}")


def send_overdue_sla_notifications():
	"""Scheduled job to alert involved parties for late items and upcoming due dates."""
	settings = frappe.get_single("Marketing Settings")
	if not settings.enable_email_notifications:
		return

	template_name = settings.overdue_sla_email_template
	if not (template_name and frappe.db.exists("Email Template", template_name)):
		return

	tmpl = frappe.get_doc("Email Template", template_name)

	# Send alerts for overdue (Late) items
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

	# Send reminder notifications for items approaching due date
	sla_reminder_enabled = getattr(settings, "sla_reminder_enabled", 0)
	if not sla_reminder_enabled:
		return

	days_before = int(getattr(settings, "sla_reminder_days_before", 3) or 3)
	reminder_date = add_days(nowdate(), days_before)

	upcoming_items = frappe.get_all(
		"Content Item",
		filters={
			"sla_due_date": ["between", [nowdate(), reminder_date]],
			"risk_flag": ["!=", "Late"],
			"workflow_state": ["not in", ["Approved", "Published"]]
		},
		fields=["name"]
	)

	for item_data in upcoming_items:
		item = frappe.get_doc("Content Item", item_data.name)
		recipients = set()
		if item.assigned_to:
			recipients.add(item.assigned_to)
		if item.reviewer_technical:
			recipients.add(item.reviewer_technical)

		if recipients:
			try:
				ctx = item.get_template_context()
				subject = f"[REMINDER] Deliverable '{item.title}' due date approaching ({item.sla_due_date})"
				message = frappe.render_template(tmpl.response, ctx)

				frappe.sendmail(
					recipients=list(recipients),
					subject=subject,
					message=message,
					now=True
				)
			except Exception as e:
				frappe.log_error(f"Failed to send reminder email for {item.name}: {str(e)}")


@frappe.whitelist()
def trigger_ai_copilot(docname):
	"""Manual API trigger for Marketing Copilot Review (Writer)."""
	if not frappe.db.exists("Content Item", docname):
		frappe.throw(_("Content Item {0} not found.").format(docname), frappe.DoesNotExistError)

	if not frappe.has_permission("Content Item", "write", doc=docname):
		frappe.throw(_("You do not have permission to trigger AI Copilot Review on this Content Item."), frappe.PermissionError)

	settings = frappe.get_single("Marketing Settings")
	if not getattr(settings, "enable_ai_copilot", 0):
		frappe.throw(
			_("AI Copilot is currently disabled in Marketing Settings. Enable it before triggering a review."),
			frappe.ValidationError
		)

	# Check usage limit for Writer
	doc = frappe.get_doc("Content Item", docname)
	max_reviews = int(getattr(settings, "max_writer_copilot_reviews_per_item", 3) or 3)
	current_count = len([r for r in (doc.ai_reviews or []) if r.get("review_type") == "Writer"])
	if current_count >= max_reviews:
		frappe.throw(
			_("Writer Copilot review limit reached ({0}/{1}). No additional AI reviews can be triggered for this item.").format(current_count, max_reviews),
			frappe.ValidationError
		)

	from oda_marketing.oda_marketing.ai_engine.runner import run_ai_review
	run_ai_review(docname, review_type="Writer")
	return frappe.get_doc("Content Item", docname)


@frappe.whitelist()
def trigger_reviewer_copilot(docname, instructions=None):
	"""Reviewer-triggered Copilot review with custom instructions."""
	if not frappe.db.exists("Content Item", docname):
		frappe.throw(_("Content Item {0} not found.").format(docname), frappe.DoesNotExistError)

	if not frappe.has_permission("Content Item", "write", doc=docname):
		frappe.throw(_("You do not have permission to trigger AI Copilot Review on this Content Item."), frappe.PermissionError)

	settings = frappe.get_single("Marketing Settings")
	if not getattr(settings, "enable_ai_copilot", 0):
		frappe.throw(
			_("AI Copilot is currently disabled in Marketing Settings. Enable it before triggering a review."),
			frappe.ValidationError
		)

	# Check usage limit for Reviewer
	doc = frappe.get_doc("Content Item", docname)
	max_reviews = int(getattr(settings, "max_reviewer_copilot_reviews_per_item", 3) or 3)
	current_count = len([r for r in (doc.ai_reviews or []) if r.get("review_type") == "Reviewer"])
	if current_count >= max_reviews:
		frappe.throw(
			_("Reviewer Copilot review limit reached ({0}/{1}). No additional AI reviews can be triggered for this item.").format(current_count, max_reviews),
			frappe.ValidationError
		)

	# Store reviewer instructions on the document
	if instructions:
		doc.db_set("reviewer_copilot_instructions", instructions, update_modified=False)

	from oda_marketing.oda_marketing.ai_engine.runner import run_ai_review
	run_ai_review(docname, reviewer_instructions=instructions, review_type="Reviewer")
	return frappe.get_doc("Content Item", docname)


@frappe.whitelist()
def get_ai_copilot_status():
	"""Whitelisted helper to check AI Copilot status without requiring read permission on Marketing Settings DocType."""
	try:
		settings = frappe.get_single("Marketing Settings")
		return {
			"enable_ai_copilot": int(getattr(settings, "enable_ai_copilot", 0) or 0),
			"max_writer_copilot_reviews_per_item": int(getattr(settings, "max_writer_copilot_reviews_per_item", 3) or 3),
			"max_reviewer_copilot_reviews_per_item": int(getattr(settings, "max_reviewer_copilot_reviews_per_item", 3) or 3)
		}
	except Exception:
		return {"enable_ai_copilot": 0, "max_writer_copilot_reviews_per_item": 3, "max_reviewer_copilot_reviews_per_item": 3}
