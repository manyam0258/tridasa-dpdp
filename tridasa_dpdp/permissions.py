def certificate_website_permission(doc, ptype, user, verbose=False):
	"""Lets a learner open/print their own certificate (used by print view & PDF)."""
	from tridasa_dpdp.utils import same_user

	return ptype in ("read", "print") and same_user(doc.user, user) and doc.status != "Revoked"
