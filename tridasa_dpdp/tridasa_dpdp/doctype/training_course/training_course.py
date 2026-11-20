# Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class TrainingCourse(Document):
	def validate(self):
		self.course_code = (self.course_code or "").strip().upper()
		if (self.questions_per_attempt or 0) < 1:
			frappe.throw(_("Questions per Attempt must be at least 1."))
		if not 0 < flt(self.pass_percentage) <= 100:
			frappe.throw(_("Pass Percentage must be between 1 and 100."))
		self.active_questions = (
			frappe.db.count("Training Question", {"course": self.name, "enabled": 1}) if not self.is_new() else 0
		)
		if self.status == "Published":
			self.validate_publishable()

	def validate_publishable(self):
		if not self.chapters:
			frappe.throw(_("Add at least one slide before publishing."))
		if self.active_questions < self.questions_per_attempt:
			frappe.throw(
				_("Publishing needs at least {0} enabled questions in the bank; it has {1}.").format(
					self.questions_per_attempt, self.active_questions
				)
			)

	def on_update(self):
		# Slide count may have changed: keep everyone's progress % honest
		total = len(self.chapters)
		for name in frappe.get_all("Training Assignment", {"course": self.name, "total_chapters": ("!=", total)}, pluck="name"):
			doc = frappe.get_doc("Training Assignment", name)
			doc.flags.ignore_permissions = True
			doc.save()

		# Publishing (or switching on 'Assign to All') enrols every active employee
		if self.status == "Published" and self.assign_to_all_active and (
			self.has_value_changed("status") or self.has_value_changed("assign_to_all_active")
		):
			from tridasa_dpdp.services.enrolment import enqueue_assign_all

			enqueue_assign_all(self.name)
			frappe.msgprint(
				_("All active employees are being assigned in the background. No emails are sent; use Actions → Email Invitations when you're ready."),
				alert=True,
			)


def refresh_question_count(course: str):
	count = frappe.db.count("Training Question", {"course": course, "enabled": 1})
	frappe.db.set_value("Training Course", course, "active_questions", count, update_modified=False)
