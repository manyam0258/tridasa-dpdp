from tridasa_dpdp.api import get_my_trainings
from tridasa_dpdp.utils import portal_context

STATUS_PILL = {
	"Invited": ("Not started", "info"),
	"In Progress": ("Reading slides", "info"),
	"Course Completed": ("Assessment pending", "warn"),
	"Assessment Failed": ("Retake needed", "bad"),
	"Certified": ("Certified", "ok"),
	"Expired": ("Certificate expired", "bad"),
}

CTA = {
	"Invited": "Start training",
	"In Progress": "Continue slides",
	"Course Completed": "Take the assessment",
	"Assessment Failed": "Retake the assessment",
	"Certified": "View certificate",
	"Expired": "Renew",
}


def get_context(context):
	portal_context(context)
	context.trainings = get_my_trainings()
	for t in context.trainings:
		t.pill_label, t.pill_class = STATUS_PILL.get(t.status, (t.status, "info"))
		t.cta = CTA.get(t.status, "Open")
	context.first_name = (context.user_full_name or "").split(" ")[0]
	context.title = "My Trainings"
	return context
