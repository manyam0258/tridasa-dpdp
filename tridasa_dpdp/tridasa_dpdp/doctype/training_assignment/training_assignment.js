// Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Training Assignment", {
	refresh(frm) {
		frm.disable_save();
		if (frm.is_new()) return;
		const open = ["Invited", "In Progress", "Course Completed", "Assessment Failed"].includes(frm.doc.status);
		if (open) {
			frm.add_custom_button(frm.doc.invitation_emailed_on ? __("Send Reminder") : __("Send Invitation Email"), () =>
				frm.call("resend_invite").then(() => {
					frappe.show_alert({ message: __("Email sent"), indicator: "green" });
					frm.reload_doc();
				})
			);
		}
		if (frm.doc.status === "Assessment Failed") {
			frm.add_custom_button(__("Grant One More Attempt"), () =>
				frappe.confirm(__("Allow {0} one more assessment attempt?", [frm.doc.employee_name]), () =>
					frm.call("grant_extra_attempt").then(() => frm.reload_doc())
				)
			);
		}
		if (frm.doc.status !== "Cancelled" && frm.doc.status !== "Certified") {
			frm.add_custom_button(__("Cancel Assignment"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, ({ reason }) =>
					frm.call("cancel_assignment", { reason }).then(() => frm.reload_doc())
				, __("Cancel assignment"), __("Cancel assignment"))
			, __("More"));
		}
		if (frm.doc.certificate) {
			frm.add_custom_button(__("Certificate"), () => frappe.set_route("Form", "Training Certificate", frm.doc.certificate), __("View"));
		}
		frm.add_custom_button(__("Attempts"), () =>
			frappe.set_route("List", "Training Assessment Attempt", { assignment: frm.doc.name })
		, __("View"));
		frm.add_custom_button(__("Open as Learner"), () => window.open(`/training/course?a=${encodeURIComponent(frm.doc.name)}`), __("View"));
		if (frm.doc.overdue) frm.dashboard.set_headline_alert(__("Overdue since {0}", [frappe.datetime.str_to_user(frm.doc.due_date)]), "red");
	},
});
