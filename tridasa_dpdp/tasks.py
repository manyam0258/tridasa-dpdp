from tridasa_dpdp.services import assessment, enrolment


def daily():
	enrolment.assign_all_active()
	enrolment.mark_overdue_and_escalate()
	enrolment.send_due_reminders()
	enrolment.expire_certificates()


def hourly():
	assessment.close_stale_attempts()
