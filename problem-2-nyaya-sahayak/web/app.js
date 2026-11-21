/* Nyaya Sahayak site. Talks only to POST /api/turn (unchanged contract). */
(function () {
  const { esc, icon, art, icons, meta, $, $$, router, header, api, copyText, downloadText } = window.UI;
  const view = $("#view"), askView = $("#askView"), ask = $("#ask");
  const DISCLAIMER = "General legal information from a small set of sourced references, not legal advice, and not reviewed by a lawyer. In an emergency call 112. Free legal aid: 15100.";
  let session = null, busy = false;

  icons(document); header();
  meta($("#identMeta"), "Legal help for money disputes");
  setInterval(() => meta($("#identMeta"), "Legal help for money disputes"), 30000);
  $("#disclaimerTop").textContent = DISCLAIMER;
  renderPanelEmpty();

  // ---------- Home and About (ordinary pages) ----------
  function home() {
    view.innerHTML = `
      <section class="hero">
        <div class="rise">
          <h1 class="display">Get back the money <span class="soft">you're owed.</span></h1>
          <p class="lead">Describe what happened in English, Hindi or Hinglish. Nyaya Sahayak sorts out the facts, explains your options with a source for every legal point, and drafts a notice you can send.</p>
          <div class="actions"><a class="btn primary" href="#/ask">Describe your problem${icon("arrowRight")}</a><a class="text-link" href="#/about">How it works</a></div>
        </div>
        <div class="stage rise"><div class="live">
          <div class="top"><span>Start with one of these</span><span>3 money problems</span></div>
          <ul class="rows" style="margin-top:12px">
            ${[["01", "A refund that never came", "Faulty product, cancelled order, service not provided", 0],
               ["02", "A deposit the landlord kept", "Security deposit not returned after you moved out", 1],
               ["03", "Salary that wasn't paid", "Unpaid wages, or final dues after resigning", 2]]
              .map(([n, t, m, i]) => `<li><a class="row" href="#/ask" data-starter="${i}"><span class="lead-col">${n}</span><span><span class="title">${t}</span><span class="meta" style="display:block">${m}</span></span><span class="end">${icon("arrowRight").replace("<svg", '<svg class="chev"')}</span></a></li>`).join("")}
          </ul>
          <p class="sub" style="margin-top:16px">Anything else, such as criminal, family or property matters, is sent to free legal aid on 15100.</p>
        </div></div>
      </section>

      <section class="section" aria-labelledby="how">
        <h2 class="title" id="how">How it works</h2>
        <div class="cards" style="--cols:4">
          ${[["chat", "Tell it what happened", "In your own words.", "It picks out the amount, the dates, the city, the other party and the proof you have, and asks about anything missing."],
             ["book", "See where you stand", "Every point has a source.", "Each legal statement comes from a fixed list of references, with a link, a confidence level and a caveat."],
             ["letter", "Send a notice", "Drafted from your facts.", "A legal notice you can copy or download. Anything it doesn't know stays as a blank for you to fill in."],
             ["shield", "Knows its limits", "Sends you on when it should.", "Safety numbers come first, and urgent or serious cases are told to see a lawyer or call free legal aid the same day."]]
            .map(([a, t, o, m], i) => `<article class="card"><p class="no">${String(i + 1).padStart(3, "0")}</p><div class="art">${art(a)}</div><h3 class="h3">${t}</h3><p class="one">${o}</p><p class="more">${m}</p></article>`).join("")}
        </div>
      </section>

      <section class="section" aria-labelledby="never">
        <div class="stage deep"><div class="showcase">
          <div>
            <h2 class="h2" id="never">It never makes up the law.</h2>
            <p>The most dangerous answer is a confident wrong one. So every legal statement comes from a fixed, sourced list, and a guard throws out any reply that names an unknown section, Act or case, invents an amount, or promises an outcome.</p>
          </div>
          <div class="live"><ul class="spec" aria-label="At a glance">
            <li><span class="k">Problems it handles</span><span class="v">Refunds, deposits, salary</span></li>
            <li><span class="k">Languages</span><span class="v">English, Hindi, Hinglish</span></li>
            <li><span class="k">Emergency</span><span class="v">112</span></li>
            <li><span class="k">Women's helpline</span><span class="v">181</span></li>
            <li><span class="k">Cyber fraud</span><span class="v">1930</span></li>
            <li><span class="k">Free legal aid</span><span class="v">15100</span></li>
          </ul></div>
        </div></div>
      </section>`;
    $$("[data-starter]").forEach((a) => a.addEventListener("click", () => { pendingStarter = +a.dataset.starter; }));
  }

  function about() {
    view.innerHTML = `
      <div class="view"><article class="prose">
        <h1 class="h1">About Nyaya Sahayak.</h1>
        <p class="lead">Many people in India who are owed money give up, because a lawyer seems expensive and the process confusing. This tool handles three common money problems carefully, rather than every legal question badly.</p>
        <h2>What it covers</h2>
        <ul>
          <li><strong>Consumer refunds:</strong> the free national helpline 1915, consumer commissions, and the two-year limit for complaints.</li>
          <li><strong>Unpaid salary:</strong> the Code on Wages, when wages are due, and the three-year limit for claims.</li>
          <li><strong>Rent deposits:</strong> the Model Tenancy Act where a state has adopted it, Lok Adalat, and the civil courts.</li>
        </ul>
        <h2>How it stays honest</h2>
        <p>Every legal statement is tagged with the source it came from, and you can open that source. An optional language model can make the explanation easier to read, but if it mentions anything that isn't in the sources, the sourced answer is shown on its own instead.</p>
        <h2>What it isn't</h2>
        <p>It is general legal information, not legal advice. The sources were checked on 21 November 2026, most of them are secondary, and none has been reviewed by a lawyer. It can misread unusual phrasing; when unsure, it asks rather than guesses.</p>
        <p><a class="btn primary" href="#/ask">Describe your problem${icon("arrowRight")}</a></p>
      </article></div>`;
  }

  // ---------- Ask (persistent conversation) ----------
  let pendingStarter = null;
  function showAsk() {
    view.hidden = true; askView.hidden = false; document.body.classList.add("asking");
    if (pendingStarter !== null) { const b = $$(".starters [data-start]")[pendingStarter]; pendingStarter = null; b && useStarter(b); }
  }
  function showPage(fn) { return () => { askView.hidden = true; view.hidden = false; document.body.classList.remove("asking"); fn(); }; }

  const msg = $("#msg");
  const status = (t) => { $("#composerStatus").textContent = t || ""; };
  const autosize = () => { msg.style.height = "auto"; msg.style.height = Math.min(msg.scrollHeight, 220) + "px"; };
  msg.addEventListener("input", autosize);
  msg.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("#composer").requestSubmit(); } });
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
  function useStarter(b) {
    msg.value = b.dataset.start; autosize(); msg.focus();
    const i = msg.value.indexOf("["); if (i >= 0) msg.setSelectionRange(i, msg.value.indexOf("]", i) + 1);
    status("Replace the parts in [brackets] with your details, then send.");
  }
  $$(".starters [data-start]").forEach((b) => b.addEventListener("click", () => useStarter(b)));

  async function send() {
    const text = msg.value.trim();
    if (!text) { status("Write a few sentences about what happened first."); msg.focus(); return; }
    if (busy) return;
    busy = true; $("#send").disabled = true; status("");
    $("#welcome") && $("#welcome").remove();
    addMsg("user", esc(text));
    msg.value = ""; autosize();
    const pending = addMsg("bot", '<span class="typing" role="img" aria-label="Preparing a reply"><span></span><span></span><span></span></span>');
    try {
      const r = await api("/api/turn", { body: { session, text } });
      session = r.session;
      pending.querySelector(".body").innerHTML = renderReply(r);
      renderPanel(r);
    } catch (err) {
      pending.querySelector(".body").innerHTML = `<div class="note bad">${icon("alertCircle")}<div>Couldn't reach the assistant: ${esc(err.message)} Your message is still shown above. Check that the app is running, then send it again.</div></div>`;
    } finally {
      busy = false; $("#send").disabled = false; msg.focus();
      pending.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
  function addMsg(who, html) {
    const el = document.createElement("div");
    el.className = "msg " + who;
    el.innerHTML = who === "bot" ? `<p class="who">Nyaya Sahayak</p><div class="body">${html}</div>` : html;
    $("#thread").appendChild(el);
    el.scrollIntoView({ block: "end" });
    return el;
  }

  const cite = (t) => esc(t).replace(/\[([A-Z][A-Z0-9-]+)\]/g, (m, id) => `<button class="cite" type="button" data-cite="${id}" aria-label="Open source ${id}">${id}</button>`);
  function renderReply(r) {
    const parts = [];
    (r.safety || []).forEach((s) => parts.push(`<div class="note bad">${icon("alert")}<div>${esc(s)}</div></div>`));
    if (r.type !== "advice") { parts.push(`<p>${cite(r.message)}</p>`); return parts.join(""); }
    const s = r.case_summary;
    parts.push(`<p>I understand this as <strong>${esc(s.problem.toLowerCase())}</strong>.</p>`);
    const known = [];
    if (s.amount_claimed !== "not clear yet") known.push(`Amount: ${esc(s.amount_claimed)}`);
    if (s.where !== "not given") known.push(`Where: ${esc(s.where.split(" (")[0])}`);
    if (s.when !== "not given") known.push(`When: ${esc(s.when)}`);
    if (known.length) parts.push(`<div class="understood">${known.map((k) => `<span class="tag">${k}</span>`).join("")}</div>`);
    if (r.plain_explanation) parts.push(`<p>${cite(r.plain_explanation)}</p>`);
    if (r.questions.length) parts.push(`<div><p><strong>To help further, tell me:</strong></p><ul>${r.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul></div>`);
    if (r.see_a_lawyer_if.length) parts.push(`<div class="note warn">${icon("alert")}<div>${esc(r.see_a_lawyer_if[0])}${r.see_a_lawyer_if.length > 1 ? ` <span class="muted">(${r.see_a_lawyer_if.length - 1} more under Next steps)</span>` : ""}</div></div>`);
    (r.also_noted || []).forEach((a) => parts.push(`<div class="note">${icon("info")}<div>${esc(a)}</div></div>`));
    parts.push(`<div class="actions"><button class="btn secondary sm" type="button" data-go="steps">See next steps</button><button class="btn ghost sm" type="button" data-go="notice">${icon("doc")}Draft legal notice</button></div>`);
    return parts.join("");
  }

  // ---------- Case panel ----------
  const panes = ["case", "steps", "sources", "notice"];
  function selectTab(name, focus) {
    panes.forEach((p) => { const t = $("#tab-" + p), on = p === name; t.setAttribute("aria-selected", String(on)); t.tabIndex = on ? 0 : -1; $("#pane-" + p).hidden = !on; });
    if (focus) $("#tab-" + name).focus();
  }
  panes.forEach((p, i) => {
    const t = $("#tab-" + p);
    t.addEventListener("click", () => selectTab(p));
    t.addEventListener("keydown", (e) => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { selectTab(panes[(i + (e.key === "ArrowRight" ? 1 : panes.length - 1)) % panes.length], true); e.preventDefault(); } });
  });
  const narrow = () => window.matchMedia("(max-width: 1020px)").matches;
  function setPane(p) { ask.dataset.pane = p; $$("[data-pane]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.pane === p))); }
  $$("[data-pane]").forEach((b) => b.addEventListener("click", () => setPane(b.dataset.pane)));
  setPane("convo");
  function showPanel(tab) { if (tab) selectTab(tab); if (narrow()) { setPane("case"); window.scrollTo(0, 0); } }
  document.addEventListener("click", (e) => {
    const go = e.target.closest("[data-go]"); if (go) showPanel(go.dataset.go);
    const c = e.target.closest("[data-cite]");
    if (c) { showPanel("sources"); const row = document.getElementById("src-" + c.dataset.cite); if (row) { row.scrollIntoView({ block: "center" }); row.classList.add("flash"); setTimeout(() => row.classList.remove("flash"), 1500); } }
  });

  function renderPanelEmpty() {
    const empty = (t, d) => `<div class="case-empty"><strong>${t}</strong>${d}</div>`;
    $("#pane-case").innerHTML = empty("Nothing yet", "Once you describe your problem, the facts I understood and the proof you have appear here.");
    $("#pane-steps").innerHTML = empty("No steps yet", "Your options, in the order to try them, appear here.");
    $("#pane-sources").innerHTML = empty("No sources yet", "Every legal statement links to the source it came from.");
    $("#pane-notice").innerHTML = empty("No notice yet", "A draft legal notice is prepared from your facts. Anything unknown stays as a blank for you to fill in.");
    $("#caseDot").textContent = "";
  }
  function renderPanel(r) {
    $("#caseDot").textContent = "•";
    if (r.type !== "advice") { $("#pane-sources").innerHTML = sourcesHtml(r.sources || []); return; }
    const s = r.case_summary;
    const where = s.where.replace(/ \(from '([^']+)'\)$/, (m, src) => (s.where.toLowerCase().startsWith(src) ? "" : ` (from ${src.replace(/\b\w/g, (c) => c.toUpperCase())})`));
    const kv = [["Problem", s.problem], ["Amount", s.amount_claimed], ["When", s.when], ["Where", where], ["Against", s.against]]
      .map(([k, v]) => `<dt>${k}</dt><dd>${/not given|not clear/.test(v) ? `<span class="muted">${esc(v)}</span>` : esc(v)}</dd>`).join("");
    const have = s.proof_you_mentioned.filter((p) => p !== "none yet");
    $("#pane-case").innerHTML = `
      <div><dl class="kv" style="grid-template-columns:96px 1fr">${kv}</dl></div>
      <div><span class="kicker">Proof you have</span>${have.length ? `<div class="tags">${have.map((p) => `<span class="badge good">${esc(p)}</span>`).join("")}</div>` : '<p class="small muted">None mentioned yet.</p>'}
        ${s.you_said_you_do_not_have.length ? `<p class="small muted" style="margin-top:8px">You said you don't have: ${esc(s.you_said_you_do_not_have.join("; "))}</p>` : ""}</div>
      ${s.proof_that_would_help.length ? `<div><span class="kicker">Proof that would help</span><ul>${s.proof_that_would_help.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>` : ""}
      ${r.questions.length ? `<div><span class="kicker">Still needed</span><ul>${r.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul></div>` : ""}`;
    $("#pane-steps").innerHTML = `
      ${(r.safety || []).map((x) => `<div class="note bad">${icon("alert")}<div>${esc(x)}</div></div>`).join("")}
      ${r.see_a_lawyer_if.length ? `<div class="note warn">${icon("alert")}<div><strong>See a lawyer or call free legal aid (15100), because:</strong><ul style="margin-top:6px">${r.see_a_lawyer_if.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></div>` : ""}
      <div><span class="kicker">What you can do, in this order</span><ol>${r.options.map((o) => `<li>${cite(o.replace("(draft below)", "(see the Notice tab)"))}</li>`).join("")}</ol></div>
      ${r.hindi_summary ? `<div class="note" lang="hi">${icon("info")}<div>${esc(r.hindi_summary)}</div></div>` : ""}
      <details class="more"><summary>Where you stand legally${icon("chevron")}</summary><div class="content"><ul>${r.where_you_stand.map((w) => `<li>${cite(w)}</li>`).join("")}</ul></div></details>
      <p class="small muted">${esc(r.disclaimer)}</p>`;
    $("#pane-sources").innerHTML = sourcesHtml(r.sources);
    $("#pane-notice").innerHTML = noticeHtml(r);
    $("#copyNotice").addEventListener("click", () => copyText(r.draft_notice, "Notice copied. Fill every [BRACKET] before sending."));
    $("#dlNotice").addEventListener("click", () => downloadText("legal-notice-draft.txt", r.draft_notice));
  }
  function sourcesHtml(list) {
    if (!list.length) return '<p class="case-empty">No sources for this reply.</p>';
    const kind = { official: ["good", "Official source"], secondary: ["", "Secondary sources"], general: ["quiet", "General reference"] };
    return `<p class="small muted">Every legal statement comes from this list. The label shows how firmly each was checked; none has been reviewed by a lawyer.</p>
      <div>${list.map((x) => { const [cls, lbl] = kind[x.verification] || ["quiet", x.verification];
        return `<div class="source" id="src-${esc(x.id)}"><div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start"><span class="law">${esc(x.law)}</span><span class="badge ${cls}">${lbl}</span></div>
          <p class="small muted" style="margin-top:4px">${esc(x.ref)} · <span class="mono">${esc(x.id)}</span></p>
          ${x.caveat ? `<p class="small" style="margin-top:6px">${esc(x.caveat)}</p>` : ""}
          <a class="text-link small" style="margin-top:6px;font-size:14px" href="${esc(x.url)}" target="_blank" rel="noopener">Open source${icon("external")}<span class="sr-only"> for ${esc(x.id)} (opens in a new tab)</span></a></div>`; }).join("")}</div>`;
  }
  function noticeHtml(r) {
    const blanks = (r.draft_notice.match(/\[[A-Z][^\]]*\]/g) || []).filter((b) => b !== "[BRACKET]");
    const preview = esc(r.draft_notice).replace(/\[([A-Z][^\]]*)\]/g, '<span class="blank">[$1]</span>');
    return `
      <div><span class="kicker">1 · Check the facts used</span>
        <dl class="kv" style="grid-template-columns:96px 1fr"><dt>Amount</dt><dd>${esc(r.case_summary.amount_claimed)}</dd><dt>Against</dt><dd>${esc(r.case_summary.against)}</dd><dt>When</dt><dd>${esc(r.case_summary.when)}</dd></dl>
        ${blanks.length ? `<div class="note warn" style="margin-top:12px">${icon("alert")}<div>${blanks.length} detail${blanks.length > 1 ? "s" : ""} to fill in yourself, highlighted below. Don't send the notice with blanks.</div></div>` : ""}</div>
      <div><span class="kicker">2 · Read the draft</span><div class="notice-preview" tabindex="0" aria-label="Draft notice">${preview}</div></div>
      <div><span class="kicker">3 · Copy or download</span><div class="actions">
        <button class="btn primary sm" type="button" id="copyNotice">${icon("copy")}Copy notice</button>
        <button class="btn secondary sm" type="button" id="dlNotice">${icon("download")}Download .txt</button></div></div>`;
  }

  // ---------- Voice (browser speech recognition, if available) ----------
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { $("#mic").disabled = true; $("#mic").setAttribute("title", "Voice input needs Chrome or Edge"); }
  // One recogniser at a time. Each result event rebuilds the spoken text from scratch and
  // replaces it (never appends), so repeated or cumulative events can't duplicate words.
  let rec = null;
  $("#mic").addEventListener("click", () => {
    if (rec) { rec.stop(); return; } // second click = stop listening
    const before = msg.value.trim();
    rec = new SR(); rec.lang = $("#lang").value; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
    status("Listening… click the mic again to stop"); $("#mic").setAttribute("aria-pressed", "true");
    rec.onresult = (e) => { msg.value = [before, spoken(e.results)].filter(Boolean).join(" "); autosize(); };
    rec.onend = () => { rec = null; status(""); $("#mic").setAttribute("aria-pressed", "false"); msg.focus(); };
    rec.onerror = (e) => { if (e.error !== "aborted" && e.error !== "no-speech") status("Voice input failed. Please type instead."); };
    rec.start();
  });
  // Joins result segments, dropping a segment that only repeats what came before it
  // (some Chrome builds, notably on Android, resend the earlier words in every new segment).
  function spoken(results) {
    let text = "";
    for (let i = 0; i < results.length; i++) {
      const part = results[i][0].transcript.trim();
      if (!part) continue;
      const low = part.toLowerCase(), have = text.toLowerCase();
      if (have && low.startsWith(have)) text = part; // cumulative segment: replace
      else if (have.endsWith(low)) continue; // exact repeat: skip
      else text = text ? text + " " + part : part;
    }
    return text;
  }

  $("#newCase").addEventListener("click", () => {
    if (session && !confirm("Start a new case? The current conversation will be cleared.")) return;
    location.hash = "#/ask"; location.reload();
  });

  router([
    [/^\/$/, showPage(home)],
    [/^\/ask$/, showAsk],
    [/^\/about$/, showPage(about)],
  ], { titleSuffix: "Nyaya Sahayak", nav: (p) => (p === "/ask" ? "ask" : p === "/about" ? "about" : "home") })();
})();
