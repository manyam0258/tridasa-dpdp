/* Tridasa DPDP Academy: course player (overview → slides → assessment → result → certificate).
   All state lives on the server; this page only renders it. Correct answers arrive only after submit. */
(() => {
	const root = document.getElementById("app");
	const ASSIGNMENT = root.dataset.assignment;
	const CSRF = root.dataset.csrf;
	const M = "tridasa_dpdp.api.";

	let S = null; // player state from get_course_player
	let paper = null; // open attempt (no answers)
	let lastPaper = null; // paper kept for the review after submit
	let lastResult = null;
	let timer = null;
	let busy = false;

	/* ------------------------------------------------ helpers */
	const esc = (s) =>
		String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
	const pct = (n) => `${Math.round(n || 0)}%`;
	const $ = (sel) => root.querySelector(sel);
	const store = {
		get(k) { try { return JSON.parse(sessionStorage.getItem(k)); } catch (e) { return null; } },
		set(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
		del(k) { try { sessionStorage.removeItem(k); } catch (e) { /* private mode */ } },
	};

	function serverError(j) {
		try {
			if (j._server_messages) {
				const msgs = JSON.parse(j._server_messages).map((m) => JSON.parse(m).message);
				const div = document.createElement("div");
				div.innerHTML = msgs.join(" ");
				return div.textContent.trim();
			}
		} catch (e) { /* fall through */ }
		if (j.exc_type === "PermissionError") return "You don't have access to this training.";
		return "Something went wrong. Please try again.";
	}

	async function call(method, args = {}, post = false) {
		const opts = { headers: { Accept: "application/json" }, credentials: "same-origin" };
		let url = "/api/method/" + M + method;
		if (post) {
			opts.method = "POST";
			opts.headers["Content-Type"] = "application/json";
			opts.headers["X-Frappe-CSRF-Token"] = CSRF;
			opts.body = JSON.stringify(args);
		} else {
			url += "?" + new URLSearchParams(args);
		}
		const r = await fetch(url, opts);
		let j = {};
		try { j = await r.json(); } catch (e) { /* non-JSON */ }
		if (!r.ok) throw new Error(serverError(j));
		return j.message;
	}

	function fail(err) {
		busy = false;
		const box = $("#err");
		if (box) { box.textContent = err.message; box.hidden = false; box.scrollIntoView({ block: "center" }); }
		else root.innerHTML = `<div class="panel empty"><h3>We couldn't load this training</h3><p>${esc(err.message)}</p><a class="btn" href="/training">Back to my trainings</a></div>`;
	}

	const slidesDone = () => S.chapters.every((c) => c.read);
	const nextUnread = () => (S.chapters.find((c) => !c.read) || {}).idx || null;
	const certified = () => S.assignment.status === "Certified";

	/* ------------------------------------------------ routing */
	function go(hash) {
		if (location.hash === hash) route();
		else location.hash = hash;
	}

	function route() {
		stopTimer();
		const h = location.hash.slice(1);
		const m = /^slide-(\d+)$/.exec(h);
		if (m) renderSlide(parseInt(m[1], 10));
		else if (h === "assessment") renderAssessment();
		else if (h === "result") renderResult();
		else if (h === "certificate") renderCertificate();
		else renderOverview();
		window.scrollTo(0, 0);
	}

	function journey(current) {
		const a = S.assignment;
		const steps = [
			{ key: "slides", n: 1, label: "Read the slides", sub: `${a.chapters_read || 0} of ${S.chapters.length} read`, done: slidesDone(), href: `#slide-${nextUnread() || 1}`, open: true },
			{ key: "assessment", n: 2, label: "Pass the assessment", sub: certified() ? `Passed · best ${pct(a.best_score)}` : `${S.course.questions} questions · pass ${pct(S.course.pass_percentage)}`, done: certified(), href: "#assessment", open: slidesDone() },
			{ key: "certificate", n: 3, label: "Get your certificate", sub: S.certificate ? S.certificate.name : "Issued instantly on passing", done: !!S.certificate, href: "#certificate", open: !!S.certificate },
		];
		return `<nav class="journey" aria-label="Your progress">${steps
			.map((s) => {
				const cls = [s.done ? "done" : "", s.key === current ? "current" : "", s.open ? "" : "locked"].join(" ");
				const inner = `<span class="node" aria-hidden="true">${s.done ? "✓" : s.n}</span><b>${esc(s.label)}</b><span>${esc(s.sub)}</span>`;
				return s.open ? `<a class="${cls}" href="${s.href}">${inner}</a>` : `<span class="${cls}" aria-disabled="true">${inner}</span>`;
			})
			.join("")}</nav>`;
	}

	/* ------------------------------------------------ overview */
	function primaryCta() {
		const a = S.assignment;
		if (certified()) return `<a class="btn sun" href="#certificate">View my certificate</a><a class="btn ghost" href="#slide-1">Revisit the slides</a>`;
		if (paper) return `<a class="btn sun" href="#assessment">Resume your assessment</a>`;
		if (!slidesDone()) {
			const n = nextUnread();
			return `<a class="btn sun" href="#slide-${n}">${n === 1 ? "Start the slides" : `Continue from slide ${n}`}</a>`;
		}
		if (a.can_attempt) return `<a class="btn sun" href="#assessment">${a.attempts_used ? "Retake the assessment" : "Take the assessment"}</a><a class="btn ghost" href="#slide-1">Revisit the slides</a>`;
		return `<a class="btn ghost" href="#slide-1">Revisit the slides</a>`;
	}

	function renderOverview() {
		const a = S.assignment, c = S.course;
		const left = a.attempts_left === null ? "Unlimited" : a.attempts_left;
		let banner = "";
		if (a.overdue && !certified()) banner = `<div class="callout"><b>Overdue</b><p>This training was due on ${esc(a.due_label)}. Please complete it today.</p></div>`;
		else if (a.status === "Assessment Failed" && !a.can_attempt) banner = `<div class="callout"><b>No attempts left</b><p>You've used all ${esc(a.attempts_used)} attempts. HR has been notified and can grant another one. Meanwhile, re-read the slides.</p></div>`;
		else if (a.status === "Expired") banner = `<div class="callout"><b>Certificate expired</b><p>Your certificate has lapsed. HR will re-enrol you for the refreshed course.</p></div>`;

		root.innerHTML = `<section class="view">
			<div class="hero-split"><div class="hero">
				<h1>${esc(c.course_name)}</h1>
				${c.introduction || ""}
			</div><img class="skyline" src="/assets/tridasa_dpdp/images/skyline-night.svg" alt=""></div>
			${banner}
			${journey("")}
			<div class="stats facts">
				<div class="stat"><b>${S.chapters.length}</b><span>Slides · about ${esc(c.minutes)} min</span></div>
				<div class="stat"><b>${esc(c.questions)}</b><span>Questions · pass ${pct(c.pass_percentage)}</span></div>
				<div class="stat"><b>${c.time_limit ? esc(c.time_limit) + " min" : "None"}</b><span>Time limit</span></div>
				<div class="stat"><b>${esc(left)}</b><span>Attempts left</span></div>
				<div class="stat"><b>${a.due_label ? esc(a.due_label) : "–"}</b><span>Complete by</span></div>
			</div>
			<div class="cta-row">${primaryCta()}</div>
		</section>`;
	}

	/* ------------------------------------------------ slides */
	function renderSlide(n) {
		const total = S.chapters.length;
		const limit = nextUnread() || total;
		if (!(n >= 1 && n <= total)) return go("#slide-1");
		if (n > limit) return go(`#slide-${limit}`);
		const ch = S.chapters[n - 1];
		const last = n === total;
		const nextLabel = last ? (certified() ? "Finish" : "Finish slides → assessment") : "Next slide →";

		root.innerHTML = `<section class="view">
			${journey("slides")}
			<div class="player">
				<nav class="rail" aria-label="Slides">${S.chapters
					.map((c) => `<button type="button" data-n="${c.idx}" class="${c.read ? "read" : ""}" aria-current="${c.idx === n}" ${c.idx > limit ? "disabled" : ""}><span class="ix">${c.idx}</span><span>${esc(c.title)}</span></button>`)
					.join("")}</nav>
				<div>
					<article class="slide" style="--read:${Math.round((n / total) * 100)}%"><div class="ch">
						<span class="num">Slide ${n} of ${total}</span>
						<h2>${esc(ch.title)}</h2>
						${ch.content}
					</div></article>
					<p class="err" id="err" hidden></p>
					<div class="slide-nav">
						${n > 1 ? `<a class="btn ghost" href="#slide-${n - 1}">← Previous</a>` : `<a class="btn ghost" href="#overview">Overview</a>`}
						<span class="slide-count"><span>${S.assignment.chapters_read || 0}/${total} read</span><span class="keys"><kbd>←</kbd> <kbd>→</kbd> to move</span></span>
						<button class="btn sun" type="button" id="nextBtn">${nextLabel}</button>
					</div>
				</div>
			</div>
		</section>`;

		root.querySelectorAll(".rail button").forEach((b) => (b.onclick = () => go(`#slide-${b.dataset.n}`)));
		$("#nextBtn").onclick = async () => {
			if (busy) return;
			try {
				if (!ch.read) {
					busy = true;
					$("#nextBtn").disabled = true;
					const r = await call("mark_chapter_read", { assignment: ASSIGNMENT, idx: n }, true);
					ch.read = true;
					Object.assign(S.assignment, { status: r.status, progress: r.progress, chapters_read: r.chapters_read });
					if (S.assignment.status === "Course Completed") S.assignment.can_attempt = true;
					busy = false;
				}
				go(last ? (certified() ? "#certificate" : "#assessment") : `#slide-${n + 1}`);
			} catch (e) { fail(e); }
		};
	}

	/* ------------------------------------------------ assessment */
	function renderAssessment() {
		const a = S.assignment, c = S.course;
		if (!slidesDone()) {
			root.innerHTML = `<section class="view">${journey("assessment")}<div class="panel empty"><h3>Read all the slides first</h3><p>The assessment unlocks after the last slide.</p><a class="btn" href="#slide-${nextUnread()}">Continue from slide ${nextUnread()}</a></div></section>`;
			return;
		}
		if (certified()) return go("#certificate");
		if (paper) return renderQuiz();
		if (!a.can_attempt) {
			root.innerHTML = `<section class="view">${journey("assessment")}<div class="panel empty"><h3>No attempts left</h3><p>You've used all your attempts. HR has been notified and can grant another one.</p><a class="btn ghost" href="#slide-1">Re-read the slides</a></div></section>`;
			return;
		}
		const left = a.attempts_left === null ? "unlimited attempts" : `${a.attempts_left} attempt${a.attempts_left === 1 ? "" : "s"} left`;
		root.innerHTML = `<section class="view">
			${journey("assessment")}
			<div class="panel">
				<span class="eyebrow">Assessment · ${esc(c.questions)} questions · pass mark ${pct(c.pass_percentage)}</span>
				<h2>${a.attempts_used ? "Ready for another try?" : "Knowledge check"}</h2>
				<ul class="rules">
					<li>One question from each area of the course, drawn from a larger bank. Every attempt gets a fresh paper.</li>
					${c.time_limit ? `<li>You have <b>${esc(c.time_limit)} minutes</b>. The timer keeps running if you leave the page, and answers are submitted automatically when it ends.</li>` : ""}
					<li>Starting uses an attempt. You have <b>${esc(left)}</b>.</li>
					<li>Answer on your own. Your result goes to HR.</li>
				</ul>
				<label class="check"><input type="checkbox" id="honour"> I have read the course and will answer on my own.</label>
				<p class="err" id="err" hidden></p>
				<div class="cta-row"><button class="btn sun" type="button" id="startBtn" disabled>Start the assessment</button><a class="btn ghost" href="#slide-1">Review slides first</a></div>
			</div>
		</section>`;
		$("#honour").onchange = (e) => ($("#startBtn").disabled = !e.target.checked);
		$("#startBtn").onclick = async () => {
			if (busy) return;
			busy = true;
			$("#startBtn").disabled = true;
			try {
				paper = await call("start_attempt", { assignment: ASSIGNMENT }, true);
				S.assignment.attempts_used = paper.attempt_no;
				busy = false;
				renderQuiz();
			} catch (e) { fail(e); }
		};
	}

	function renderQuiz() {
		const key = "tdpdp-ans-" + paper.attempt;
		const saved = store.get(key) || {};
		const n = paper.questions.length;
		root.innerHTML = `<section class="view">
			<div class="timer" id="timer"><span class="prog"><span id="progTxt">0 of ${n} answered</span><span class="bar"><i id="progBar"></i></span></span>
				<span>${paper.seconds_left !== null ? `Time left <span class="clock" id="clock">--:--</span>` : `<span class="note">No time limit</span>`}</span></div>
			<form id="quiz" class="panel">
				<span class="eyebrow">Attempt ${esc(paper.attempt_no)}</span>
				<div>${paper.questions
					.map((q, i) => `<fieldset class="q" style="border:0;margin:0;padding-inline:0"><span class="area">${esc(q.topic)}</span>
						<legend class="stem" style="padding:0"><span class="n">Q${i + 1}.</span>${esc(q.question)}</legend>
						<div class="opts">${q.options
							.map((o, k) => `<label class="opt"><input type="radio" name="q${q.idx}" value="${k}" ${saved[q.idx] === k ? "checked" : ""}><span>${esc(o)}</span></label>`)
							.join("")}</div></fieldset>`)
					.join("")}</div>
				<p class="err" id="err" hidden></p>
				<div class="cta-row"><button class="btn sun" type="submit" id="submitBtn" disabled>Submit answers</button><span class="note">You can't change answers after submitting.</span></div>
			</form>
		</section>`;

		const answers = () => {
			const out = {};
			paper.questions.forEach((q) => {
				const c = root.querySelector(`input[name="q${q.idx}"]:checked`);
				if (c) out[q.idx] = parseInt(c.value, 10);
			});
			return out;
		};
		const update = () => {
			const ans = answers(), k = Object.keys(ans).length;
			store.set(key, ans);
			$("#progTxt").textContent = `${k} of ${n} answered`;
			$("#progBar").style.width = (k / n) * 100 + "%";
			$("#submitBtn").disabled = k < n;
		};
		$("#quiz").addEventListener("change", update);
		update();

		const submit = async (auto) => {
			if (busy) return;
			if (!auto && !confirm("Submit your answers? You can't change them afterwards.")) return;
			busy = true;
			stopTimer();
			$("#submitBtn").disabled = true;
			try {
				const r = await call("submit_attempt", { attempt: paper.attempt, answers: JSON.stringify(answers()) }, true);
				store.del(key);
				lastPaper = paper;
				lastResult = r;
				paper = null;
				S = await call("get_course_player", { assignment: ASSIGNMENT });
				busy = false;
				go("#result");
			} catch (e) { fail(e); }
		};
		$("#quiz").addEventListener("submit", (e) => { e.preventDefault(); submit(false); });

		if (paper.seconds_left !== null) {
			const endAt = Date.now() + paper.seconds_left * 1000;
			const tick = () => {
				const s = Math.max(0, Math.round((endAt - Date.now()) / 1000));
				const clock = $("#clock");
				if (!clock) return stopTimer();
				clock.textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
				$("#timer").classList.toggle("low", s <= 60);
				if (s === 0) submit(true);
			};
			tick();
			timer = setInterval(tick, 1000);
		}
	}

	function stopTimer() {
		if (timer) clearInterval(timer);
		timer = null;
	}

	/* ------------------------------------------------ result */
	function renderResult() {
		if (!lastResult) return go(S.history.length ? "#assessment" : "#overview");
		const r = lastResult, passed = r.result === "Passed";
		const first = (S.assignment.employee_name || "").split(" ")[0];
		let msg;
		if (passed) msg = `Well done${first ? ", " + esc(first) : ""}. Your certificate number is <b class="mono">${esc(r.certificate || "")}</b>.`;
		else if (r.status === "Timed Out") msg = "Time ran out before your answers reached us, so this attempt counts as not passed.";
		else if (r.attempts_left === 0) msg = "You've used all your attempts. HR has been notified and can grant another one.";
		else msg = "Re-read the slides for the questions you missed, then try again. You'll get a different paper.";

		const review = r.review && lastPaper
			? `<div class="panel"><h2>Review</h2><div>${lastPaper.questions
					.map((q, i) => {
						const rv = r.review.find((x) => x.idx === q.idx) || {};
						return `<div class="q"><span class="area">${esc(q.topic)}</span><p class="stem"><span class="n">Q${i + 1}.</span>${esc(q.question)}</p>
							<div class="opts">${q.options.map((o, k) => `<div class="opt ${k === rv.correct ? "right" : k === rv.selected ? "wrong" : ""}"><span>${esc(o)}</span></div>`).join("")}</div>
							<p class="why"><b>${rv.is_correct ? "Correct." : "Not quite."}</b> ${esc(rv.explanation || "")}</p></div>`;
					})
					.join("")}</div></div>`
			: "";

		root.innerHTML = `<section class="view">
			${journey("assessment")}
			<div class="panel">
				<div class="score"><div class="ring ${passed ? "ok" : ""}" style="--p:${Math.round(r.score || 0)}"><span class="big">${esc(r.correct)}/${esc(r.total)}</span></div>
					<div style="display:grid;gap:6px"><span class="pill ${passed ? "ok" : "bad"}">${passed ? "PASSED" : "NOT PASSED"}</span>
					<span class="note">Score ${pct(r.score)} · pass mark ${pct(r.pass_percentage)}</span></div></div>
				<p>${msg}</p>
				<div class="cta-row">${passed
					? `<a class="btn sun" href="#certificate">View my certificate</a>`
					: S.assignment.can_attempt
						? `<a class="btn" href="#assessment">Retake with a new paper</a><a class="btn ghost" href="#slide-1">Back to the slides</a>`
						: `<a class="btn ghost" href="#slide-1">Back to the slides</a>`}</div>
			</div>
			${review}
		</section>`;
	}

	/* ------------------------------------------------ certificate */
	function renderCertificate() {
		const cert = S.certificate;
		if (!cert) {
			root.innerHTML = `<section class="view">${journey("certificate")}<div class="panel empty"><h3>No certificate yet</h3><p>Pass the assessment with ${pct(S.course.pass_percentage)} or more and your certificate appears here.</p><a class="btn" href="#overview">Back to the course</a></div></section>`;
			return;
		}
		const name = encodeURIComponent(cert.name);
		const valid = cert.status === "Active";
		root.innerHTML = `<section class="view">
			${journey("certificate")}
			<div class="hero">
				<span class="eyebrow">Certificate</span>
				<h1>${valid ? "You're certified" : "Certificate " + esc(cert.status.toLowerCase())}</h1>
				<p class="lede">Issued to ${esc(S.assignment.employee_name)} on ${esc(cert.issue_label)}${cert.valid_label ? `, valid until ${esc(cert.valid_label)}` : ""}.</p>
			</div>
			<div class="certbox"><iframe class="certframe" id="certFrame" title="Certificate preview"
				src="/printview?doctype=Training%20Certificate&name=${name}&format=DPDP%20Certificate&no_letterhead=1"></iframe></div>
			<div class="cta-row">
				${valid ? `<a class="btn sun" href="/api/method/${M}download_certificate?name=${name}">Download PDF</a>` : ""}
				<a class="btn ghost" href="/training/verify?no=${name}" target="_blank" rel="noopener">Verification page</a>
				<span class="note">Certificate no. <span class="mono">${esc(cert.name)}</span></span>
			</div>
		</section>`;
		const frame = $("#certFrame");
		frame.onload = () => {
			try {
				// Scale the A4 print layout to fit the preview width
				const doc = frame.contentDocument;
				const fmt = doc.querySelector(".print-format");
				const toolbar = doc.querySelector(".print-format-gutter") || doc.body;
				toolbar.style.padding = "0";
				doc.body.style.margin = "0";
				doc.body.style.background = "#fff";
				if (fmt) {
					fmt.style.margin = "0";
					fmt.style.boxShadow = "none";
					doc.body.style.zoom = frame.clientWidth / fmt.scrollWidth;
				}
			} catch (e) { /* cross-origin or blocked: leave unscaled */ }
		};
	}

	/* ------------------------------------------------ keyboard: ← / → on slides (same as the buttons) */
	function slideKeys(e) {
		if (!/^#slide-\d+$/.test(location.hash) || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
		if (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
		if (e.key === "ArrowRight") {
			const next = $("#nextBtn");
			if (next && !next.disabled) { e.preventDefault(); next.click(); }
		} else if (e.key === "ArrowLeft") {
			const prev = root.querySelector(".slide-nav a.ghost");
			if (prev) { e.preventDefault(); prev.click(); }
		}
	}

	/* ------------------------------------------------ boot */
	(async () => {
		if (!ASSIGNMENT) return fail(new Error("No training was specified. Open it from your trainings list."));
		try {
			S = await call("get_course_player", { assignment: ASSIGNMENT });
			paper = S.open_attempt;
			addEventListener("hashchange", route);
			addEventListener("keydown", slideKeys);
			route();
		} catch (e) { fail(e); }
	})();
})();
