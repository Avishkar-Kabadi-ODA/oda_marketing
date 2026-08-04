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

		if (frm.doc.workflow_state === "Marketing Copilot Review" || frm.doc.ai_review_status === "Queued") {
			frm.add_custom_button(__("Run AI Copilot Review Now"), function() {
				frappe.show_progress(__("Marketing Copilot Review"), 15, 100, __("Starting AI Copilot Review..."));
				frappe.call({
					method: "oda_marketing.oda_marketing.doctype.content_item.content_item.trigger_ai_copilot",
					args: { docname: frm.doc.name },
					callback: function(r) {
						frappe.hide_progress();
						frappe.show_alert({ message: __("AI Copilot Review completed!"), indicator: "green" });
						frm.reload_doc();
					}
				});
			}, __("Actions"));
		}

		// Listen for realtime streaming socket events from AI Agent
		if (!frm.ai_socket_listener) {
			frm.ai_socket_listener = true;
			frappe.realtime.on("ai_copilot_stream", function(data) {
				if (data && data.docname === frm.doc.name) {
					if (data.progress >= 100) {
						frappe.hide_progress();
						frappe.show_alert({ message: __("AI Copilot Review completed!"), indicator: "green" });
						setTimeout(() => frm.reload_doc(), 800);
					} else {
						frappe.show_progress(__("Marketing Copilot Review"), data.progress || 50, 100, data.message || __("Evaluating deliverable..."));
					}
				}
			});
		}
	},

	apply_role_field_permissions(frm) {
		const is_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";
		const is_writer = frappe.user.has_role("Content Writer") || is_lead;
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

		if (is_writer) {
			// Writer & Lead can upload/edit all 3 draft attachments & working notes
			frm.set_df_property("content_file_1", "read_only", 0);
			frm.set_df_property("content_file_2", "read_only", 0);
			frm.set_df_property("content_file_3", "read_only", 0);
			frm.set_df_property("notes", "read_only", 0);
			frm.set_df_property("revision_feedback_notes", "read_only", 1);
		} else if (is_reviewer) {
			// Reviewers can view & download writer files, but CANNOT modify/replace them
			frm.set_df_property("content_file_1", "read_only", 1);
			frm.set_df_property("content_file_2", "read_only", 1);
			frm.set_df_property("content_file_3", "read_only", 1);
			frm.set_df_property("notes", "read_only", 1);
			frm.set_df_property("revision_feedback_notes", "read_only", 0);
		}

		// Field Visibility Rules:
		// 1. Dynamic System Prompt (Subagent): ONLY visible to Marketing Lead or Admin
		frm.set_df_property("ai_generated_prompt", "hidden", is_lead ? 0 : 1);

		// 2. AI Copilot Feedback & Improvements: ONLY visible to assigned Content Writer / Owner (and Marketing Lead/Admin)
		const is_assigned_writer = (frappe.session.user === frm.doc.assigned_to) || (frappe.session.user === frm.doc.owner);
		const can_see_ai_feedback = frm.doc.ai_copilot_feedback && (is_assigned_writer || is_lead);
		frm.set_df_property("ai_copilot_feedback", "hidden", can_see_ai_feedback ? 0 : 1);
	}
});
