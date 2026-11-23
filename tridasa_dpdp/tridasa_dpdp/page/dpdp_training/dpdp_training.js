// /app/dpdp-training: open to every user. It also makes the DPDP Academy workspace
// visible to everyone (Frappe shows a workspace only when its module has something the
// user can open). It just takes them to their trainings.
frappe.pages["dpdp-training"].on_page_load = function () {
	window.location.href = "/training";
};
