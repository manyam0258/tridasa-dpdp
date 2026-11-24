## Tridasa DPDP

DPDP Act awareness training for Tridasa employees: invite staff from ERPNext/HRMS, they read the playbook slides, pass a randomised assessment, and get a verifiable certificate. The IT department runs the whole process; HR has no part in it.

Requires `erpnext` and `hrms`.

### Flow

1. **Everyone is assigned automatically, without emails.** With **Assign to All Active Employees** ticked on the course (the default), every active employee is assigned when the course is published, after every `bench migrate` (each deploy), and daily for anyone added or re-activated later. The IT department can also press **Actions → Assign to All Active Employees**. No email is sent and no logins are created. Employees see the course on `/training` and are taken to it when they log in. If a login is linked to an Employee later (for example a test user), it picks up that employee's training automatically. Training is mapped to Employees only: a login gets training through the active Employee it is linked to (Employee → User ID), matched automatically by company, preferred or personal email when not linked yet. Logins without an Employee record get none. Assignments the IT department cancelled are not reopened.
2. **The IT department emails invitations when it chooses.** **Email All Employees** (or **Actions → Email Invitations…**) sends the course link either to everyone not emailed yet or to everyone who hasn't finished, optionally for one department, with an optional message. It sends right away (in the background for very large companies), and employees without a login get one with a set-password link. **Invite Employees** assigns a filtered group and has a **Send invitation email** checkbox. On an assignment, **Send Invitation Email / Send Reminder** emails one person. Automatic reminders and manager escalations go only to employees who were sent an invitation.
3. **The employee reads the slides** at `/training`. With **Open Training Right After Login** ticked (the default), anyone with this training pending is taken straight to it when they log in, whether they use the portal or the Desk. A link the user clicked on purpose (`?redirect-to=`) still wins. There are 15 slides from the playbook, read in order, with progress saved on the server.
4. **The employee takes the assessment.** It has 10 questions, one per topic, drawn from a 40-question bank, with options shuffled. Questions the employee has already seen are avoided. The pass mark is 80%, the time limit is 20 minutes and they get 3 attempts. Answers are graded on the server and are never sent to the browser before submit.
5. **Certificate.** It is issued as soon as they pass and emailed as a PDF. It is valid for 12 months. Anyone can check it at `/training/verify`.
6. **Follow-up.** Reminders go out every 3 days. Overdue training is escalated to the employee's reporting manager. Expired certificates trigger re-certification. Employees who leave are removed from the pending counts.

### Admin views

- **DPDP Academy** workspace (everyone): a **My Trainings** link.
- **DPDP Training Admin** workspace (Training Manager, System Manager): number cards and charts for invited, slides completed, attempted, certified and overdue, plus admin shortcuts.
- **Training Compliance** report: the funnel by department, branch or designation, with completion %.
- **Training Course** form: a live funnel, Send Reminders Now, and Preview a Paper with the answer key.
- **Training Assignment**: Send Reminder, Grant One More Attempt, Cancel, and Open as Learner.
- **Training Certificate**: Download PDF and Revoke.

### Roles

- **Training Manager**: full admin. Give this role (or System Manager) to the IT department only. HR roles have no access.
- **Training Learner**: portal only. Learners get no DocType permissions. Every learner endpoint checks that the assignment belongs to them.

### Setup notes

- Learners who have a problem are told on the portal to contact the IT department.
- Configure a default outgoing **Email Account**. Without one, enrolment still works, but emails are logged in Error Log instead of being sent.
- Set `host_name` in site config so links in emails and on certificates use your real domain.
- Sample data: `bench --site <site> execute tridasa_dpdp.demo.make_demo`

### Tests

Run the tests on a separate test site that has erpnext, hrms and this app installed:

```
bench --site <test-site> run-tests --app tridasa_dpdp
```
