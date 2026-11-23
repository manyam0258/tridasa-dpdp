"""Logins without an Employee record are trained too; keep them in step with the login."""

import frappe
from frappe import _
from frappe.utils import today


def on_update(doc, method=None):
	if not doc.has_value_changed("enabled") or frappe.flags.in_install:
		return
	from tridasa_dpdp.services import enrolment

	if not doc.enabled:
		enrolment.cancel_user_assignments(doc.name, _("Login disabled on {0}").format(today()))
		return
	frappe.db.savepoint("tridasa_dpdp_user")
	try:
		enrolment.assign_user_now(doc.name, reopen_cancelled=True)
	except Exception:
		frappe.db.rollback(save_point="tridasa_dpdp_user")
		frappe.log_error(title=f"Tridasa DPDP: could not assign training to {doc.name}")
