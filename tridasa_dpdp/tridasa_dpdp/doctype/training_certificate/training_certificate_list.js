// Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Training Certificate"] = {
	get_indicator(doc) {
		return [__(doc.status), { Active: "green", Expired: "orange", Revoked: "red" }[doc.status], `status,=,${doc.status}`];
	},
};
