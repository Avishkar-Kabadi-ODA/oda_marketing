// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Content Item", {
	refresh(frm) {
		frm.trigger("apply_role_field_permissions");

		if (frm.doc.content_calendar) {
			frm.add_custom_button(__("View Content Calendar"), function() {
				frappe.set_route("Form", "Content Calendar", frm.doc.content_calendar);
			}, __("Navigate"));
		}

		frappe.call({
			method: "oda_marketing.oda_marketing.doctype.content_item.content_item.get_ai_copilot_status",
			callback: function(res) {
				const enable_ai = res && res.message ? res.message.enable_ai_copilot : 0;
				const max_reviews = res && res.message ? res.message.max_copilot_reviews_per_item : 3;
				const current_review_count = (frm.doc.ai_reviews || []).length;
				const limit_reached = current_review_count >= max_reviews;

				if (enable_ai) {
					// Writer: show Run AI Copilot button when in Copilot Review or In Progress
					const writer_copilot_states = ["Marketing Copilot Review", "In Progress"];
					if (writer_copilot_states.includes(frm.doc.workflow_state) || frm.doc.ai_review_status === "Queued") {
						if (!limit_reached) {
							frm.add_custom_button(__("Run AI Copilot Review"), function() {
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
							}, __("Copilot"));
						} else {
							frm.add_custom_button(__("Copilot Limit Reached"), function() {
								frappe.msgprint(__("Maximum Copilot reviews ({0}) reached for this item.", [max_reviews]));
							}, __("Copilot"));
						}
					}

					// Reviewer: show Run Copilot Review button when in "In Review" state
					const is_reviewer = frappe.user.has_role("Technical Reviewer");
					if (is_reviewer && frm.doc.workflow_state === "In Review") {
						if (!limit_reached) {
							frm.add_custom_button(__("Run Copilot Review (Reviewer)"), function() {
								let d = new frappe.ui.Dialog({
									title: __("Reviewer Copilot Instructions"),
									fields: [
										{
											label: __("Instructions for AI Copilot"),
											fieldname: "instructions",
											fieldtype: "Small Text",
											reqd: 1,
											description: __("Provide specific evaluation instructions for the AI Copilot (e.g., 'Check technical accuracy of the AWS migration section').")
										}
									],
									primary_action_label: __("Run Copilot Review"),
									primary_action(values) {
										d.hide();
										frappe.show_progress(__("Marketing Copilot Review"), 15, 100, __("Starting Reviewer Copilot Review..."));
										frappe.call({
											method: "oda_marketing.oda_marketing.doctype.content_item.content_item.trigger_reviewer_copilot",
											args: {
												docname: frm.doc.name,
												instructions: values.instructions
											},
											callback: function(r) {
												frappe.hide_progress();
												frappe.show_alert({ message: __("Reviewer Copilot Review completed!"), indicator: "green" });
												frm.reload_doc();
											}
										});
									}
								});
								d.show();
							}, __("Copilot"));
						}
					}
				} else {
					// Hide AI section and evaluation fields when AI Copilot is disabled
					frm.set_df_property("ai_section", "hidden", 1);
					frm.set_df_property("ai_score", "hidden", 1);
					frm.set_df_property("ai_review_status", "hidden", 1);
					frm.set_df_property("ai_copilot_feedback", "hidden", 1);
					frm.set_df_property("ai_reviews", "hidden", 1);
				}

				// Clean up internal workflow action buttons that users shouldn't see directly
				setTimeout(() => {
					frm.page.clear_action_item(__("Submit for Copilot Review"));
					frm.page.remove_inner_button(__("Submit for Copilot Review"));
					frm.page.clear_action_item(__("Resubmit Draft"));
					frm.page.remove_inner_button(__("Resubmit Draft"));
				}, 300);
			}
		});

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
		const is_reviewer = frappe.user.has_role("Technical Reviewer");

		if (!is_lead) {
			const metadata_fields = [
				"title", "content_type", "topic", "practice_area",
				"content_calendar", "planned_publish_date", "assigned_to",
				"reviewer_technical", "published_url", "risk_flag"
			];
			metadata_fields.forEach(field => frm.set_df_property(field, "read_only", 1));

			// Due Date is editable by Content Writer (carved out from metadata protection)
			if (is_writer) {
				frm.set_df_property("sla_due_date", "read_only", 0);
			}

			setTimeout(() => {
				$("a:contains('Edit Sidebar'), .sidebar-item-container:contains('Edit Sidebar')").hide();
			}, 300);
		}

		// Writer read-only enforcement before Briefed state
		const is_planned = frm.doc.workflow_state === "Planned";

		if (is_writer) {
			frm.set_df_property("content_file_1", "read_only", is_planned && !is_lead ? 1 : 0);
			frm.set_df_property("content_file_2", "read_only", is_planned && !is_lead ? 1 : 0);
			frm.set_df_property("content_file_3", "read_only", is_planned && !is_lead ? 1 : 0);
			frm.set_df_property("notes", "read_only", is_planned && !is_lead ? 1 : 0);
			frm.set_df_property("revision_feedback_notes", "read_only", 1);
		} else if (is_reviewer) {
			frm.set_df_property("content_file_1", "read_only", 1);
			frm.set_df_property("content_file_2", "read_only", 1);
			frm.set_df_property("content_file_3", "read_only", 1);
			frm.set_df_property("notes", "read_only", 1);
			frm.set_df_property("revision_feedback_notes", "read_only", 0);
			// Reviewer can write copilot instructions when in review
			frm.set_df_property("reviewer_copilot_instructions", "read_only", frm.doc.workflow_state === "In Review" ? 0 : 1);
		}

		// Require revision feedback notes if state is In Revision
		if (frm.doc.workflow_state === "In Revision") {
			frm.set_df_property("revision_feedback_notes", "reqd", 1);
		}

		// Hidden for all users on form view (viewable in Marketing Settings)
		frm.set_df_property("ai_generated_prompt", "hidden", 1);

		// AI Copilot Feedback & Review History Thread: visible ONLY to Content Writer (assigned writer / owner / Content Writer role) and Marketing Lead / System Manager
		const is_assigned_writer = (frappe.session.user === frm.doc.assigned_to) || (frappe.session.user === frm.doc.owner) || frappe.user.has_role("Content Writer");
		const can_see_ai_feedback = is_assigned_writer || is_lead || is_reviewer;

		frm.set_df_property("ai_copilot_feedback", "hidden", (can_see_ai_feedback && frm.doc.ai_copilot_feedback) ? 0 : 1);
		frm.set_df_property("ai_reviews", "hidden", (can_see_ai_feedback && frm.doc.ai_reviews && frm.doc.ai_reviews.length > 0) ? 0 : 1);
	}
});
