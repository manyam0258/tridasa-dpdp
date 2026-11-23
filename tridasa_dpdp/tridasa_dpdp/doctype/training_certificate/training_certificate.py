# Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

# No 0/O/1/I so numbers read back correctly over the phone
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class TrainingCertificate(Document):
	def autoname(self):
		"""Random, non-sequential numbers: the public verify page can't be used to list staff."""
		prefix = frappe.db.get_value("Training Course", self.course, "certificate_prefix") or "CERT"
		year = getdate(self.issue_date).year
		while True:
			name = f"{prefix}-{year}-" + "".join(secrets.choice(ALPHABET) for _ in range(7))
			if not frappe.db.exists("Training Certificate", name):
				self.name = name
				return

	@frappe.whitelist()
	def revoke(self, reason: str):
		frappe.only_for(("Training Manager", "System Manager"))
		if self.status == "Revoked":
			return
		self.status = "Revoked"
		self.revoked_reason = reason
		self.revoked_on = now_datetime()
		self.save()
		if self.assignment and frappe.db.get_value("Training Assignment", self.assignment, "certificate") == self.name:
			assignment = frappe.get_doc("Training Assignment", self.assignment)
			assignment.status = "Assessment Failed" if assignment.attempts_used else "Course Completed"
			assignment.certificate = None
			assignment.certified_on = None
			assignment.save()
		self.add_comment("Comment", _("Certificate revoked: {0}").format(reason))
