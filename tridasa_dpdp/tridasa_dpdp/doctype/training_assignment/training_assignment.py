# Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today

from tridasa_dpdp.utils import OPEN_STATUSES, attempts_left


class TrainingAssignment(Document):
	def validate(self):
		self.validate_unique()
		self.update_progress()
		self.overdue = int(bool(self.status in OPEN_STATUSES and self.due_date and getdate(self.due_date) < getdate(today())))

	def validate_unique(self):
		dup = frappe.db.exists(
			"Training Assignment", {"course": self.course, "employee": self.employee, "name": ("!=", self.name)}
		)
		if dup:
			frappe.throw(_("{0} is already enrolled in this course ({1}).").format(self.employee_name, dup))

	def update_progress(self):
		self.total_chapters = len(frappe.get_cached_doc("Training Course", self.course).chapters)
		self.chapters_read = min(len(self.chapter_progress), self.total_chapters)
		self.progress = flt(self.chapters_read * 100 / self.total_chapters, 1) if self.total_chapters else 0

	def can_still_finish(self) -> bool:
		if self.status not in OPEN_STATUSES:
			return False
		if self.status == "Assessment Failed":
			return attempts_left(frappe.get_cached_doc("Training Course", self.course), self) != 0
		return True

	def mark_chapter_read(self, idx: int) -> bool:
		"""Slides are read in order. Returns True if this call changed progress."""
		course = frappe.get_cached_doc("Training Course", self.course)
		if not 1 <= idx <= len(course.chapters):
			frappe.throw(_("Unknown slide."))
		read = {r.chapter_idx for r in self.chapter_progress}
		if idx in read:
			return False
		if idx > len(read) + 1:
			frappe.throw(_("Please read the slides in order."))

		now = now_datetime()
		self.append("chapter_progress", {"chapter_idx": idx, "chapter_title": course.chapters[idx - 1].chapter_title, "read_on": now})
		if self.status == "Invited":
			self.status = "In Progress"
			self.started_on = now
		if len(self.chapter_progress) >= len(course.chapters) and self.status == "In Progress":
			self.status = "Course Completed"
			self.course_completed_on = now
		self.flags.ignore_permissions = True
		self.save()
		return True

	def reset_for_new_cycle(self, due_date):
		"""Start again (annual refresher or re-invite after cancellation). History stays on the attempts."""
		self.cycle = (self.cycle or 1) + 1
		self.status = "Invited"
		self.due_date = due_date
		self.chapter_progress = []
		for field in ("started_on", "course_completed_on", "last_attempt_on", "certified_on", "certificate",
				"last_reminder_on", "escalated_on", "cancel_reason"):
			self.set(field, None)
		for field in ("attempts_used", "extra_attempts", "best_score", "last_score", "reminders_sent", "overdue"):
			self.set(field, 0)

	# ------------------------------------------------ desk actions

	@frappe.whitelist()
	def grant_extra_attempt(self):
		frappe.only_for(("Training Manager", "System Manager"))
		if self.status != "Assessment Failed":
			frappe.throw(_("Extra attempts can only be granted after a failed assessment."))
		self.extra_attempts = (self.extra_attempts or 0) + 1
		self.save()
		from tridasa_dpdp.services.enrolment import send_assignment_email

		send_assignment_email(self, kind="reminder")
		self.add_comment("Comment", _("Granted one more assessment attempt."))

	@frappe.whitelist()
	def resend_invite(self):
		"""Email this employee now: the invitation if they've never had one, else a reminder."""
		frappe.only_for(("Training Manager", "System Manager"))
		from tridasa_dpdp.services.enrolment import EMPLOYEE_FIELDS, ensure_user, send_assignment_email

		if not self.can_still_finish():
			frappe.throw(_("Nothing to remind about: status is {0}.").format(self.status))
		emp = frappe.db.get_value("Employee", self.employee, EMPLOYEE_FIELDS, as_dict=True)
		user, _created, link = ensure_user(emp)  # creates a portal login if they have none
		if not user:
			frappe.throw(_("{0} has no email address. Add one on the Employee record first.").format(self.employee_name))
		if self.user != user:
			self.db_set({"user": user, "email": frappe.db.get_value("User", user, "email")})

		first_time = not self.invitation_emailed_on
		kind = "invite" if first_time else ("overdue" if self.overdue else "reminder")
		if not send_assignment_email(self, kind=kind, password_link=link):
			frappe.throw(_("The email could not be sent. Set up a default outgoing Email Account first."))
		if first_time:
			self.db_set("invitation_emailed_on", now_datetime())
		else:
			self.db_set({"reminders_sent": (self.reminders_sent or 0) + 1, "last_reminder_on": now_datetime()})

	@frappe.whitelist()
	def cancel_assignment(self, reason: str):
		frappe.only_for(("Training Manager", "System Manager"))
		self.status = "Cancelled"
		self.cancel_reason = reason
		self.save()
