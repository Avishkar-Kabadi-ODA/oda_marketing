// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Content Item", {
	refresh(frm) {
		frm.trigger("apply_role_field_permissions");

		if (frm.doc.content_calendar) {
			frm.add_custom_button(__("View Content Calendar"), function() {
				frappe.set_route("Form", "Content Calendar", frm.doc.content_calendar);
			}, __("Actions"));
		}
	},

	apply_role_field_permissions(frm) {
		const is_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager");
		const is_writer = frappe.user.has_role("Content Writer");
		const is_reviewer = frappe.user.has_role("Technical Reviewer") || frappe.user.has_role("Business Reviewer");

		if (!is_lead) {
			// Lock core metadata fields for non-leads
			const metadata_fields = [
				"title", "content_type", "topic", "practice_area",
				"content_calendar", "planned_publish_date", "assigned_to",
				"reviewer_technical", "reviewer_business", "published_url",
				"sharepoint_folder_url", "risk_flag"
			];
			metadata_fields.forEach(field => frm.set_df_property(field, "read_only", 1));
		}

		if (is_writer && !is_lead) {
			// Assigned Writer can upload/edit all 3 draft attachments & working notes
			frm.set_df_property("content_file_1", "read_only", 0);
			frm.set_df_property("content_file_2", "read_only", 0);
			frm.set_df_property("content_file_3", "read_only", 0);
			frm.set_df_property("notes", "read_only", 0);
			frm.set_df_property("revision_feedback_notes", "read_only", 1);
		} else if (is_reviewer && !is_lead) {
			// Reviewers can view & download writer files, but CANNOT modify/replace them
			frm.set_df_property("content_file_1", "read_only", 1);
			frm.set_df_property("content_file_2", "read_only", 1);
			frm.set_df_property("content_file_3", "read_only", 1);
			frm.set_df_property("notes", "read_only", 1);
			frm.set_df_property("revision_feedback_notes", "read_only", 0);
		}
	}
});
