/* Nyaya Sahayak front end. Talks only to POST /api/turn (unchanged contract). */
(function () {
  const { esc, icon, api, openSheet, closeSheet, trapTab, copyText, downloadText } = window.UI;
  const $ = (s) => document.querySelector(s);
  const DISCLAIMER = "This gives general legal information from a small set of sourced references. It is not legal advice. " +
    "In an emergency call 112. Free legal aid: 15100.";
  let session = null, last = null, busy = false;

  $("#brandIcon").innerHTML = icon("scale");
  $("#disclaimerTop").innerHTML = icon("info") + `<div class="body-md">${esc(DISCLAIMER)}</div>`;
  $("#send").insertAdjacentHTML("afterbegin", icon("send"));
  $("#mic").innerHTML = icon("mic");
  $("#closeCase").innerHTML = icon("close");
  renderPanelEmpty();

  // ---------- Composer ----------
  const msg = $("#msg");
  const autosize = () => { msg.style.height = "auto"; msg.style.height = Math.min(msg.scrollHeight, 200) + "px"; };
  msg.addEventListener("input", autosize);
  msg.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("#composer").requestSubmit(); } });
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
  document.querySelectorAll(".topic").forEach((b) => b.addEventListener("click", () => {
    msg.value = b.dataset.start; autosize(); msg.focus();
    const i = msg.value.indexOf("["); if (i >= 0) msg.setSelectionRange(i, msg.value.indexOf("]", i) + 1);
    status("Replace the parts in [brackets] with your details, then press Send.");
  }));
  const status = (t) => { $("#composerStatus").textContent = t || ""; };

  async function send() {
    const text = msg.value.trim();
    if (!text) { status("Type a few sentences about what happened first."); msg.focus(); return; }
    if (busy) return;
    busy = true; $("#send").disabled = true; status("");
    $("#welcome") && $("#welcome").remove();
    addMsg("user", esc(text));
    msg.value = ""; autosize();
    const pending = addMsg("bot", '<span class="typing" aria-label="Preparing a reply"><span></span><span></span><span></span></span>');
    try {
      const r = await api("/api/turn", { body: { session, text } });
      session = r.session; last = r;
      pending.querySelector(".bubble").innerHTML = renderReply(r);
      renderPanel(r);
    } catch (err) {
      pending.querySelector(".bubble").innerHTML = `<div class="banner error">${icon("error")}<div>Could not reach the assistant. ${esc(err.message)} Your message was not lost: it is shown above. Check that the app is running, then send again.</div></div>`;
    } finally {
      busy = false; $("#send").disabled = false; msg.focus();
      pending.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function addMsg(who, html) {
    const el = document.createElement("div");
    el.className = "msg " + who;
    el.innerHTML = `<div class="bubble">${html}</div>`;
    $("#thread").appendChild(el);
    el.scrollIntoView({ block: "end" });
    return el;
  }

  // Replace [ID] citations with small buttons that open the source.
  const cite = (t) => esc(t).replace(/\[([A-Z][A-Z0-9-]+)\]/g, (m, id) => `<button class="cite" data-cite="${id}" aria-label="Source ${id}">${id}</button>`);

  function renderReply(r) {
    const parts = [];
    (r.safety || []).forEach((s) => parts.push(`<div class="banner error">${icon("warning")}<div>${esc(s)}</div></div>`));
    if (r.type !== "advice") {
      parts.push(`<p>${cite(r.message)}</p>`);
      return `<div class="stack">${parts.join("")}</div>`;
    }
    const s = r.case_summary;
    parts.push(`<p>I understand this as <b>${esc(s.problem.toLowerCase())}</b>.</p>`);
    const known = [];
    if (s.amount_claimed !== "not clear yet") known.push(`Amount: ${esc(s.amount_claimed)}`);
    if (s.where !== "not given") known.push(`Where: ${esc(s.where.split(" (")[0])}`);
    if (s.when !== "not given") known.push(`When: ${esc(s.when)}`);
    if (known.length) parts.push(`<div class="understood">${known.map((k) => `<span class="status neutral">${k}</span>`).join("")}</div>`);
    if (r.plain_explanation) parts.push(`<p>${cite(r.plain_explanation)}</p>`);
    if (r.questions.length) parts.push(`<div><p class="title-sm">To help you further, please tell me:</p><ul>${r.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul></div>`);
    if (r.see_a_lawyer_if.length) parts.push(`<div class="banner warning">${icon("warning")}<div>${esc(r.see_a_lawyer_if[0])}${r.see_a_lawyer_if.length > 1 ? ` <span class="muted">(+${r.see_a_lawyer_if.length - 1} more in Next steps)</span>` : ""}</div></div>`);
    (r.also_noted || []).forEach((a) => parts.push(`<div class="banner info">${icon("info")}<div>${esc(a)}</div></div>`));
    parts.push(`<div class="actions"><button class="btn tonal" data-go="steps">See next steps</button><button class="btn text" data-go="notice">${icon("doc")}Draft legal notice</button></div>`);
    return `<div class="stack">${parts.join("")}</div>`;
  }

  // ---------- Case panel ----------
  const panes = ["case", "steps", "sources", "notice"];
  function selectTab(name, focus) {
    panes.forEach((p) => {
      const t = $("#tab-" + p), on = p === name;
      t.setAttribute("aria-selected", String(on)); t.tabIndex = on ? 0 : -1;
      $("#pane-" + p).hidden = !on;
    });
    if (focus) $("#tab-" + name).focus();
  }
  panes.forEach((p, i) => {
    const t = $("#tab-" + p);
    t.addEventListener("click", () => selectTab(p));
    t.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { const n = panes[(i + (e.key === "ArrowRight" ? 1 : panes.length - 1)) % panes.length]; selectTab(n, true); e.preventDefault(); }
    });
  });

  const panel = $("#casePanel"), scrim = $("#caseScrim");
  const narrow = () => window.matchMedia("(max-width: 1023px)").matches;
  function showPanel(tab) {
    if (tab) selectTab(tab);
    if (narrow()) openSheet(panel, scrim, document.activeElement);
  }
  $("#openCase").addEventListener("click", (e) => showPanel());
  $("#closeCase").addEventListener("click", () => closeSheet(panel, scrim));
  scrim.addEventListener("click", () => closeSheet(panel, scrim));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && panel.classList.contains("open")) closeSheet(panel, scrim); trapTab(panel, e); });

  document.addEventListener("click", (e) => {
    const go = e.target.closest("[data-go]");
    if (go) showPanel(go.dataset.go);
    const c = e.target.closest("[data-cite]");
    if (c) {
      showPanel("sources");
      const row = document.getElementById("src-" + c.dataset.cite);
      if (row) { row.scrollIntoView({ block: "center" }); row.classList.add("flash"); setTimeout(() => row.classList.remove("flash"), 1500); }
    }
  });

  function renderPanelEmpty() {
    const empty = (t, d) => `<div class="empty panel-empty"><div class="icon">${icon("doc")}</div><p class="title-md">${t}</p><p class="body-md">${d}</p></div>`;
    $("#pane-case").innerHTML = empty("Your case will appear here", "After you describe your problem, the facts I understood and the proof you have are listed here.");
    $("#pane-steps").innerHTML = empty("No steps yet", "Your options, in the order to try them, will appear here.");
    $("#pane-sources").innerHTML = empty("No sources yet", "Every legal statement links to the source it came from.");
    $("#pane-notice").innerHTML = empty("No notice yet", "A draft legal notice is prepared from your facts. Unknown details stay as blanks to fill in.");
    $("#openCase").hidden = true;
  }

  function renderPanel(r) {
    $("#openCase").hidden = false;
    if (r.type !== "advice") {
      $("#pane-sources").innerHTML = sourcesHtml(r.sources || []);
      return;
    }
    const s = r.case_summary;
    const where = s.where.replace(/ \(from '([^']+)'\)$/, (m, src) => (s.where.toLowerCase().startsWith(src) ? "" : ` (from ${src})`));
    const kv = [["Problem", s.problem], ["Amount", s.amount_claimed], ["When", s.when], ["Where", where], ["Against", s.against]]
      .map(([k, v]) => `<dt>${k}</dt><dd>${/not given|not clear/.test(v) ? `<span class="muted">${esc(v)}</span>` : esc(v)}</dd>`).join("");
    const have = s.proof_you_mentioned.filter((p) => p !== "none yet");
    $("#pane-case").innerHTML = `
      <div class="block"><dl class="kv">${kv}</dl></div>
      <div class="block"><p class="title-sm">Proof you have</p>${have.length ? `<div class="facts-chips">${have.map((p) => `<span class="status success">${icon("check")}${esc(p)}</span>`).join("")}</div>` : '<p class="body-md muted">None mentioned yet.</p>'}
        ${s.you_said_you_do_not_have.length ? `<p class="body-sm muted" style="margin-top:8px">You said you don't have: ${esc(s.you_said_you_do_not_have.join("; "))}</p>` : ""}</div>
      ${s.proof_that_would_help.length ? `<div class="block"><p class="title-sm">Proof that would help</p><ul class="body-md">${s.proof_that_would_help.map((p) => `<li>${esc(p)}</li>`).join("")}</ul></div>` : ""}
      ${r.questions.length ? `<div class="block"><p class="title-sm">Still needed</p><ul class="body-md">${r.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul></div>` : ""}`;

    $("#pane-steps").innerHTML = `
      ${(r.safety || []).map((x) => `<div class="banner error block">${icon("warning")}<div>${esc(x)}</div></div>`).join("")}
      ${r.see_a_lawyer_if.length ? `<div class="banner warning block">${icon("warning")}<div><p class="title-sm">Get a lawyer or free legal aid (15100) because</p><ul class="body-md">${r.see_a_lawyer_if.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></div>` : ""}
      <div class="block"><p class="title-sm">What you can do, in this order</p><ol class="steps body-md">${r.options.map((o) => `<li>${cite(o.replace("(draft below)", "(see the Notice tab)"))}</li>`).join("")}</ol></div>
      ${r.hindi_summary ? `<div class="block banner info" lang="hi">${icon("info")}<div class="body-md">${esc(r.hindi_summary)}</div></div>` : ""}
      <details class="disclosure block"><summary>Where you stand legally</summary><div class="content"><ul class="body-md">${r.where_you_stand.map((w) => `<li>${cite(w)}</li>`).join("")}</ul></div></details>
      <p class="body-sm muted block">${esc(r.disclaimer)}</p>`;

    $("#pane-sources").innerHTML = sourcesHtml(r.sources);
    $("#pane-notice").innerHTML = noticeHtml(r);
    $("#copyNotice").addEventListener("click", () => copyText(r.draft_notice, "Notice copied. Fill every [BRACKET] before sending."));
    $("#dlNotice").addEventListener("click", () => downloadText("legal-notice-draft.txt", r.draft_notice));
  }

  function sourcesHtml(list) {
    if (!list.length) return '<p class="body-md muted">No sources for this reply.</p>';
    const kind = { official: ["success", "Official source"], secondary: ["info", "Secondary sources"], general: ["neutral", "General reference"] };
    return `<p class="body-md muted block">Every legal statement comes from this list. Verification level shows how firmly each was checked; none has been reviewed by a lawyer.</p>
      <div class="block">${list.map((x) => {
        const [cls, lbl] = kind[x.verification] || ["neutral", x.verification];
        return `<div class="source" id="src-${esc(x.id)}"><div class="row"><span class="title-sm grow">${esc(x.law)}</span><span class="status ${cls}">${lbl}</span></div>
          <p class="body-md muted">${esc(x.ref)} · <span class="mono">${esc(x.id)}</span></p>
          ${x.caveat ? `<p class="body-sm" style="margin-top:4px">${esc(x.caveat)}</p>` : ""}
          <a class="body-md" href="${esc(x.url)}" target="_blank" rel="noopener">Open source<span class="sr-only"> for ${esc(x.id)} (opens in a new tab)</span></a></div>`;
      }).join("")}</div>`;
  }

  function noticeHtml(r) {
    const blanks = (r.draft_notice.match(/\[[A-Z][^\]]*\]/g) || []).filter((b) => b !== "[BRACKET]");
    const preview = esc(r.draft_notice).replace(/\[([A-Z][^\]]*)\]/g, '<span class="blank">[$1]</span>');
    return `
      <div class="notice-steps body-sm"><span class="notice-step"><b>1</b>Review facts</span><span class="notice-step"><b>2</b>Preview</span><span class="notice-step"><b>3</b>Copy or download</span></div>
      <div class="block"><p class="title-sm">1 · Check the facts used</p>
        <dl class="kv body-md"><dt>Amount</dt><dd>${esc(r.case_summary.amount_claimed)}</dd><dt>Against</dt><dd>${esc(r.case_summary.against)}</dd><dt>When</dt><dd>${esc(r.case_summary.when)}</dd></dl>
        ${blanks.length ? `<div class="banner warning" style="margin-top:12px">${icon("warning")}<div>${blanks.length} detail${blanks.length > 1 ? "s" : ""} to fill in yourself (highlighted). Do not send the notice with blanks.</div></div>` : ""}</div>
      <div class="block"><p class="title-sm">2 · Preview</p><div class="notice-preview" tabindex="0" aria-label="Draft notice preview">${preview}</div></div>
      <div class="block"><p class="title-sm">3 · Copy or download</p><div class="actions" style="margin-top:8px">
        <button class="btn filled" id="copyNotice">${icon("copy")}Copy notice</button>
        <button class="btn outlined" id="dlNotice">${icon("download")}Download .txt</button></div></div>`;
  }

  // ---------- Voice (browser speech recognition, if available) ----------
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { $("#mic").disabled = true; $("#mic").setAttribute("data-tip", "Voice input needs Chrome or Edge"); }
  // One recogniser at a time. Each result event rebuilds the spoken text from scratch and
  // replaces it (never appends), so repeated or cumulative events can't duplicate words.
  let rec = null;
  $("#mic").addEventListener("click", () => {
    if (rec) { rec.stop(); return; }              // second click = stop listening
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
      if (have && low.startsWith(have)) text = part;          // cumulative segment: replace
      else if (have.endsWith(low)) continue;                   // exact repeat: skip
      else text = text ? text + " " + part : part;
    }
    return text;
  }

  // ---------- New case ----------
  $("#newCase").addEventListener("click", () => {
    if (session && !confirm("Start a new case? The current conversation will be cleared.")) return;
    location.reload();
  });
})();
