// Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Training Certificate", {
	refresh(frm) {
		frm.disable_save();
		if (frm.is_new()) return;
		frm.add_custom_button(__("Download PDF"), () =>
			window.open(`/api/method/tridasa_lms.api.download_certificate?name=${encodeURIComponent(frm.doc.name)}`)
		);
		frm.add_custom_button(__("Verification Page"), () =>
			window.open(`/training/verify?no=${encodeURIComponent(frm.doc.name)}`)
		);
		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Revoke"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, ({ reason }) =>
					frm.call("revoke", { reason }).then(() => frm.reload_doc())
				, __("Revoke certificate"), __("Revoke"))
			, __("More"));
		}
	},
});
