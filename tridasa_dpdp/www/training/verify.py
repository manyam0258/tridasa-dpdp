import frappe

from tridasa_dpdp.api import verify_certificate
from tridasa_dpdp.utils import portal_context


def get_context(context):
	portal_context(context, require_login=False)
	context.query = (frappe.form_dict.get("no") or "").strip().upper()[:40]
	context.result = verify_certificate(context.query) if context.query else None
	context.title = "Verify a certificate"
	return context
