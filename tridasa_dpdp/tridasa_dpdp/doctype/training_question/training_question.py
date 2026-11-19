# Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from tridasa_dpdp.tridasa_dpdp.doctype.training_course.training_course import refresh_question_count


class TrainingQuestion(Document):
	def validate(self):
		self.topic = (self.topic or "").strip()
		self.options = [o for o in self.options if (o.option_text or "").strip()]
		if len(self.options) < 2:
			frappe.throw(_("Add at least two options."))
		if sum(1 for o in self.options if o.is_correct) != 1:
			frappe.throw(_("Mark exactly one option as correct."))

	def on_update(self):
		refresh_question_count(self.course)

	def on_trash(self):
		if frappe.db.exists("Training Attempt Question", {"question": self.name}):
			frappe.throw(_("This question appears in submitted papers. Disable it instead of deleting."))

	def after_delete(self):
		refresh_question_count(self.course)
