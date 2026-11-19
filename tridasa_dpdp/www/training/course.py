import frappe

from tridasa_dpdp.utils import portal_context


def get_context(context):
	portal_context(context)
	context.assignment = frappe.form_dict.get("a") or ""
	context.title = "Course"
	return context
