## Tridasa DPDP

DPDP Act awareness training for Tridasa employees: invite staff from ERPNext/HRMS, they read the playbook slides, pass a randomised assessment, and get a verifiable certificate. HR tracks who has completed each step.

Requires `erpnext` and `hrms`.

### Flow

1. **HR invites.** Open **Training Course → DPDP-2026 → Actions → Invite Employees**. Filter by company, department, branch or designation, or pick people. Each active employee gets an assignment and an email. Employees without a login get a portal-only login and a set-password link. New joiners are invited automatically.
2. **The employee reads the slides** at `/training`. There are 15 slides from the playbook, read in order, with progress saved on the server.
3. **The employee takes the assessment.** It has 10 questions, one per topic, drawn from a 40-question bank, with options shuffled. Questions the employee has already seen are avoided. The pass mark is 80%, the time limit is 20 minutes and they get 3 attempts. Answers are graded on the server and are never sent to the browser before submit.
4. **Certificate.** It is issued as soon as they pass and emailed as a PDF. It is valid for 12 months. Anyone can check it at `/training/verify`.
5. **Follow-up.** Reminders go out every 3 days. Overdue training is escalated to the employee's reporting manager. Expired certificates trigger re-certification. Employees who leave are removed from the pending counts.

### Admin views

- **DPDP Academy** workspace: number cards and charts for invited, slides completed, attempted, certified and overdue.
- **Training Compliance** report: the funnel by department, branch or designation, with completion %.
- **Training Course** form: a live funnel, Send Reminders Now, and Preview a Paper with the answer key.
- **Training Assignment**: Send Reminder, Grant One More Attempt, Cancel, and Open as Learner.
- **Training Certificate**: Download PDF and Revoke.

### Roles

- **Training Manager**: full admin.
- **HR Manager**: read and report.
- **Training Learner**: portal only. Learners get no DocType permissions. Every learner endpoint checks that the assignment belongs to them.

### Setup notes

- Configure a default outgoing **Email Account**. Without one, enrolment still works, but emails are logged in Error Log instead of being sent.
- Set `host_name` in site config so links in emails and on certificates use your real domain.
- Sample data: `bench --site <site> execute tridasa_dpdp.demo.make_demo`

### Tests

Run the tests on a separate test site that has erpnext, hrms and this app installed:

```
bench --site <test-site> run-tests --app tridasa_dpdp
```
