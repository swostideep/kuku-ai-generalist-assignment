/* Continuity Checker site. Talks to /api/shows, /api/check, /api/results, /api/context, /api/export (unchanged). */
(function () {
  const { esc, icon, art, icons, meta, $, $$, router, header, api, copyText, plural } = window.UI;
  const view = $("#view");
  const CHECKS = {
    NAME_DRIFT: ["Name spelled differently", "One person or place is spelled several ways across episodes, which leads to different pronunciations and mismatched on-screen text."],
    LABEL_ALIAS: ["One character, two labels", "The same character appears under more than one speaker label, so voice and character references split in two."],
    UNNAMED_RECURRING: ["Recurring character has no name", "A speaker who comes back across episodes is known only by a description, so their voice and look can't be tied to one identity."],
    SPEECH_RATE: ["Line too fast to speak", "A line has more words than can be said in its time slot. Over 4.5 words a second is a warning; over 5 is an error."],
    SELF_OVERLAP: ["Speaker talks over themselves", "A character starts a new line before their previous one has finished."],
    SCENE_BOUNDS: ["Cue outside its scene", "A cue falls outside its scene's time range, or two scenes overlap or leave a gap."],
    CONTINUITY_REF: ["Wrong previous episode", "An episode's continuity notes point to an episode that isn't the one before it."],
  };
  const nameOf = (t) => (CHECKS[t] || [t])[0];
  const state = { shows: [], show: null, data: null, busy: false, err: "", sev: "", type: "", ep: "", q: "" };

  icons(document); header();
  const tickMeta = () => meta($("#identMeta"), state.show && state.show.name);
  setInterval(tickMeta, 30000);

  async function boot() {
    try { state.shows = (await api("/api/shows")).shows; }
    catch (e) { state.err = "Couldn't load the shows: " + e.message; }
    let saved = null; try { saved = sessionStorage.getItem("cc-show"); } catch (e) { /* storage unavailable */ }
    state.show = state.shows.find((s) => s.id === saved) || state.shows[0] || null;
    tickMeta();
    if (state.show && state.show.has_results) await load();
    go();
  }
  async function load() {
    try { setData(await api("/api/results?show=" + encodeURIComponent(state.show.id))); } catch (e) { state.data = null; }
  }
  function setData(d) { state.data = d; d.findings.forEach((f, i) => (f.n = i + 1)); }
  async function pickShow(id) {
    state.show = state.shows.find((s) => s.id === id); state.data = null; state.err = "";
    try { sessionStorage.setItem("cc-show", id); } catch (e) { /* ignore */ }
    tickMeta(); if (state.show.has_results) await load(); renderLive();
  }
  async function check() {
    state.busy = true; state.err = ""; renderLive();
    try { setData(await api("/api/check", { body: { show: state.show.id } })); state.show.has_results = true; state.show.checked_at = "just now"; }
    catch (e) { state.err = e.message; }
    state.busy = false; renderLive();
  }

  const counts = () => { const f = state.data.findings; return { e: f.filter((x) => x.severity === "error").length, w: f.filter((x) => x.severity === "warning").length }; };
  const sevBadge = (s) => `<span class="badge ${s === "error" ? "bad" : "warn"}">${s === "error" ? "Error" : "Warning"}</span>`;
  const epList = (eps) => (eps.length > 6 ? `${eps.slice(0, 5).join(", ")} and ${eps.length - 5} more` : eps.join(", "));
  const pad = (n) => String(n).padStart(2, "0");

  // ---------- Home ----------
  function home() {
    view.innerHTML = `
      <section class="hero">
        <div class="rise">
          <h1 class="display">Catch the mistakes <span class="soft">before they're voiced.</span></h1>
          <p class="lead">AI-written episodes drift: a name gains three spellings, a villain loses his name, a line runs too fast to say. The Continuity Checker reads the whole show and points to every case, by episode, cue and time.</p>
          <div class="actions"><a class="btn primary" href="#/findings" id="heroCta">Review findings${icon("arrowRight")}</a><a class="text-link" href="#/method">What it checks</a></div>
        </div>
        <div class="stage rise"><div class="live" id="live" aria-live="polite"></div></div>
      </section>

      <section class="section" aria-labelledby="checks">
        <h2 class="title" id="checks">What it looks for</h2>
        <div class="cards" style="--cols:4">
          ${[["spell", "Names that drift", "Ashford, Ashforde, Ashferd.", "The same person or place written different ways, including first-letter changes such as Katherine and Catherine."],
             ["labels", "Speaker labels", "LADY MARA or MARA?", "One character under two labels, which splits their voice and character references. Married couples are recognised."],
             ["person", "Nameless regulars", "“TALL STRANGER”, eight episodes running.", "Recurring speakers known only by a description, with the name the scene directions use as a suggestion."],
             ["clock", "Timing", "Thirty-three words in four seconds.", "Lines too fast to say, speakers who talk over themselves, cues outside their scene and wrong episode references."]]
            .map(([a, t, o, m], i) => `<article class="card"><p class="no">${String(i + 1).padStart(3, "0")}</p><div class="art">${art(a)}</div><h3 class="h3">${t}</h3><p class="one">${o}</p><p class="more">${m}</p></article>`).join("")}
        </div>
      </section>

      <section class="section" aria-labelledby="rules">
        <div class="stage deep"><div class="showcase">
          <div>
            <h2 class="h2" id="rules">Rules where they work, judgement where it's needed.</h2>
            <p>Spelling, timing and labels are exact arithmetic, so plain rules are faster, cheaper and easier to test than a model, and the same script always gives the same report. Whether “Harlow” is a typo for “Harrow” or a different family is a judgement, so that is left to an editor.</p>
          </div>
          <div class="live"><ul class="spec" aria-label="Thresholds">
            <li><span class="k">Speech rate, warning</span><span class="v">over 4.5 words a second</span></li>
            <li><span class="k">Speech rate, error</span><span class="v">over 5 words a second</span></li>
            <li><span class="k">Spellings treated as one name</span><span class="v">72% alike or more</span></li>
            <li><span class="k">Recurring unnamed speaker</span><span class="v">2 episodes or more</span></li>
            <li><span class="k">Fifty episodes, checked in</span><span class="v">about 0.2 seconds</span></li>
          </ul></div>
        </div></div>
      </section>`;
    renderLive();
  }

  function renderLive() {
    const el = $("#live"); if (!el) return;
    const s = state.show, d = state.data;
    if (!s) { el.innerHTML = state.err ? `<div class="note bad">${icon("alertCircle")}<div>${esc(state.err)}</div></div>` : `<p class="h3">No shows found</p><p class="sub">Start the app with <span class="mono">--shows</span> pointing at a folder of episode files.</p>`; return; }
    const picker = state.shows.length > 1 ? `<div class="field" style="margin-top:24px"><label for="showPick">Show</label><select class="select" id="showPick">${state.shows.map((x) => `<option value="${esc(x.id)}" ${x.id === s.id ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></div>` : "";
    let body;
    if (state.busy) {
      body = `<div class="top"><span>Checking ${esc(s.name)}</span></div><div class="figure-row"><span class="figure">…</span><span class="unit">reading ${s.episodes} episodes</span></div>
        <div class="status-line"><div class="progress"><span style="width:60%"></span></div>This takes a second or two.</div>`;
    } else if (d) {
      const { e, w } = counts(), tot = e + w || 1, eps = new Set(d.findings.flatMap((f) => f.episodes)).size;
      const top = d.findings.slice(0, 3);
      body = `<div class="top"><span>${esc(s.name)}</span><span>${s.checked_at ? "Checked " + esc(s.checked_at) : ""}</span></div>
        <div class="figure-row"><span class="figure">${e}</span><span class="unit">${e === 1 ? "error" : "errors"} to fix</span></div>
        <p class="sub">And ${plural(w, "warning")} to look at, across ${eps} of ${d.run.episodes} episodes and ${d.run.blocks.toLocaleString("en-IN")} cues.</p>
        <div class="meter" aria-hidden="true"><span class="red" style="width:${(100 * e) / tot}%"></span><span class="amber" style="width:${(100 * w) / tot}%"></span></div>
        <div class="legend-row"><span class="red">Errors</span><span class="amber">Warnings</span></div>
        <ul class="mini" aria-label="First three findings">${top.map((f) => `<li><span class="k">${pad(f.n)}</span><span class="t">${esc(nameOf(f.type))}</span><span class="m">Ep. ${esc(epList(f.episodes.slice(0, 3)))}${f.episodes.length > 3 ? "…" : ""}</span></li>`).join("")}</ul>
        <div class="actions"><a class="btn primary" href="#/findings">See all ${d.findings.length}</a><button class="btn secondary" id="runBtn" type="button">Check again</button></div>`;
    } else {
      body = `<div class="top"><span>${esc(s.name)}</span><span>${s.episodes} episodes</span></div>
        <div class="figure-row"><span class="figure">–</span><span class="unit">not checked yet</span></div>
        <p class="sub">The checks read every episode and take a second or two.</p>
        <div class="actions"><button class="btn primary" id="runBtn" type="button">${icon("play")}Run the checks</button></div>`;
    }
    if (state.err && s) body += `<div class="note bad" style="margin-top:20px">${icon("alertCircle")}<div>${esc(state.err)}</div></div>`;
    el.innerHTML = body + picker;
    const run = $("#runBtn"); run && run.addEventListener("click", check);
    const pk = $("#showPick"); pk && pk.addEventListener("change", (ev) => pickShow(ev.target.value));
    const cta = $("#heroCta"); if (cta) cta.toggleAttribute("hidden", !d);
  }

  // ---------- Findings ----------
  function filtered() {
    const q = state.q.trim().toLowerCase();
    return state.data.findings.filter((f) => (!state.sev || f.severity === state.sev) && (!state.type || f.type === state.type) && (!state.ep || f.episodes.includes(+state.ep)) &&
      (!q || (f.title + " " + nameOf(f.type) + " " + f.locations.map((l) => l.text).join(" ")).toLowerCase().includes(q)));
  }
  function noData() {
    view.innerHTML = `<div class="view"><h1 class="h1">No report yet</h1><div class="empty"><p>Run the checks first. They read every episode and list each continuity mistake with its location.</p><div class="actions"><a class="btn primary" href="#/">Go to the checks</a></div></div></div>`;
  }
  function list() {
    if (!state.data) return noData();
    const d = state.data, { e, w } = counts(), fs = d.findings;
    const eps = [...new Set(fs.flatMap((f) => f.episodes))].sort((a, b) => a - b), types = [...new Set(fs.map((f) => f.type))];
    view.innerHTML = `
      <div class="view">
        <div class="view-head"><div><h1 class="h1">Findings</h1>
          <p class="lead">${e ? `Fix the ${plural(e, "error")} before voice and video are made. Warnings are worth a look, but some may be intended.` : "No errors. Look through the warnings; some may be intended."}</p></div>
          <button class="btn secondary" type="button" id="export">${icon("download")}Export CSV</button></div>
        <div class="stats">
          <div><div class="v">${e}</div><div class="k">Errors</div></div>
          <div><div class="v">${w}</div><div class="k">Warnings</div></div>
          <div><div class="v">${eps.length}<span class="muted" style="font-size:22px"> / ${d.run.episodes}</span></div><div class="k">Episodes affected</div></div>
          <div><div class="v">${d.run.blocks.toLocaleString("en-IN")}</div><div class="k">Cues checked</div></div>
        </div>
        <div class="toolbar" role="search">
          <div class="search">${icon("search")}<label class="sr-only" for="q">Search findings</label><input class="input" id="q" type="search" placeholder="Search names, labels or lines" value="${esc(state.q)}"></div>
          <label class="sr-only" for="type">Check</label>
          <select class="select" id="type"><option value="">All checks</option>${types.map((t) => `<option value="${t}" ${t === state.type ? "selected" : ""}>${esc(nameOf(t))}</option>`).join("")}</select>
          <label class="sr-only" for="ep">Episode</label>
          <select class="select" id="ep"><option value="">All episodes</option>${eps.map((x) => `<option value="${x}" ${String(x) === state.ep ? "selected" : ""}>Episode ${x}</option>`).join("")}</select>
          <div class="segmented" role="group" aria-label="Severity">
            ${[["", "All", fs.length], ["error", "Errors", e], ["warning", "Warnings", w]].map(([v, l, n]) => `<button type="button" data-sev="${v}" aria-pressed="${state.sev === v}">${l}<span class="count">${n}</span></button>`).join("")}
          </div>
        </div>
        <ul class="rows" id="rows"></ul>
        <p class="result-count" id="count" aria-live="polite"></p>
      </div>`;
    const draw = () => {
      const f = filtered();
      $("#rows").innerHTML = f.map((x) => `<li><a class="row" href="#/findings/${x.n}">
          <span class="lead-col">${pad(x.n)}</span>
          <span><span class="title">${esc(nameOf(x.type))}</span><span class="meta clamp-2">${esc(x.title)}</span>
            <span class="meta" style="display:block">Episode${x.episodes.length > 1 ? "s" : ""} ${esc(epList(x.episodes))}</span></span>
          <span class="end">${sevBadge(x.severity)}${icon("chevron").replace("<svg", '<svg class="chev"')}</span></a></li>`).join("") ||
        `<li><div class="empty"><p class="h3">Nothing matches</p><p>Try another word, or clear the filters.</p><div class="actions"><button class="btn secondary" type="button" id="clear">Clear filters</button></div></div></li>`;
      $("#count").textContent = `Showing ${f.length} of ${fs.length}, errors first.`;
      const c = $("#clear"); c && c.addEventListener("click", () => { Object.assign(state, { sev: "", type: "", ep: "", q: "" }); list(); });
    };
    $("#q").addEventListener("input", (ev) => { state.q = ev.target.value; draw(); });
    $("#type").addEventListener("change", (ev) => { state.type = ev.target.value; draw(); });
    $("#ep").addEventListener("change", (ev) => { state.ep = ev.target.value; draw(); });
    $$("[data-sev]").forEach((b) => b.addEventListener("click", () => { state.sev = b.dataset.sev; $$("[data-sev]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); draw(); }));
    $("#export").addEventListener("click", () => { location.href = "/api/export?show=" + encodeURIComponent(state.show.id); });
    draw();
  }

  // ---------- One finding ----------
  function evidence(f) {
    const ev = f.evidence || {};
    if (ev.forms) return `<div class="surface"><ul class="spec" style="padding:4px 24px">${Object.entries(ev.forms).map(([k, v]) => `<li><span>${esc(k)}</span><span class="v muted">${plural(v.count, "time")} · ep. ${esc(v.episodes.join(", "))}</span></li>`).join("")}</ul></div>`;
    if (ev.labels) return `<div class="surface"><ul class="spec" style="padding:4px 24px">${Object.entries(ev.labels).map(([k, v]) => `<li><span>${esc(k)}</span><span class="v muted">${plural(v, "line")}</span></li>`).join("")}</ul></div>`;
    if (ev.likely_identity) return ev.likely_identity.length ? `<p class="h3">Most likely <strong>${esc(ev.likely_identity[0][0])}</strong>, from ${plural(ev.likely_identity[0][1], "nearby mention")}${ev.likely_identity.length > 1 ? `; otherwise ${ev.likely_identity.slice(1).map((x) => esc(x[0])).join(", ")}` : ""}. Confirm before renaming.</p>` : "";
    if (ev.words_per_second) return `<dl class="kv"><dt>Words</dt><dd>${ev.words}</dd><dt>Time slot</dt><dd>${ev.seconds} seconds</dd><dt>Rate</dt><dd>${ev.words_per_second} words a second</dd></dl>`;
    return "";
  }
  function detail(m) {
    if (!state.data) return noData();
    const fl = filtered().length ? filtered() : state.data.findings;
    const i = fl.findIndex((x) => x.n === +m[1]);
    const f = i >= 0 ? fl[i] : state.data.findings.find((x) => x.n === +m[1]);
    if (!f) { location.hash = "#/findings"; return false; }
    const prev = i > 0 ? fl[i - 1] : null, next = i >= 0 && i < fl.length - 1 ? fl[i + 1] : null;
    const nav = (q, label, ic) => q ? `<a class="icon-btn bordered" href="#/findings/${q.n}" aria-label="${label}">${icon(ic)}</a>` : `<span class="icon-btn bordered" aria-hidden="true" style="opacity:.35">${icon(ic)}</span>`;
    const ev = evidence(f);
    view.innerHTML = `
      <div class="view">
        <a class="back" href="#/findings">${icon("arrowLeft")}All findings</a>
        <div class="detail-head">
          <div><p class="kicker">Finding ${f.n} of ${state.data.findings.length}</p>
            <h1 class="h1" style="margin-top:12px">${esc(nameOf(f.type))}</h1>
            <p class="lead">${esc(f.title)}</p></div>
          <div class="detail-tools">${sevBadge(f.severity)}
            <button class="btn secondary sm" type="button" id="copy">${icon("copy")}Copy locations</button>
            ${nav(prev, "Previous finding", "chevronLeft")}${nav(next, "Next finding", "chevron")}</div>
        </div>
        <div class="block"><span class="kicker">Why it matters</span><p class="h3 muted" style="max-width:40em">${esc((CHECKS[f.type] || ["", ""])[1])}</p></div>
        ${f.suggestion ? `<div class="block"><span class="kicker">Suggested fix</span><div class="note">${icon("check")}<div>${esc(f.suggestion)}</div></div></div>` : ""}
        ${ev ? `<div class="block"><span class="kicker">Evidence</span>${ev}</div>` : ""}
        <div class="block"><span class="kicker">Where it happens${f.locations.length > 8 ? `, first 8 of ${f.locations.length}` : ""}</span>
          <div class="stack" style="display:grid;gap:12px">${f.locations.slice(0, 8).map((l, j) => `
            <div class="surface pad">
              <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center">
                <span class="meta muted">Episode ${esc(l.episode)} · ${esc(l.block)}${l.time ? " · " + esc(l.time) : ""}</span>
                ${/^B\d+$/.test(l.block) ? `<button class="btn ghost sm ctx" type="button" data-j="${j}" aria-expanded="false">Show surrounding lines</button>` : ""}
              </div>
              <p class="h3" style="margin-top:8px">${esc(l.text)}</p>
              <div id="ctx-${j}" style="margin-top:12px"></div>
            </div>`).join("")}</div></div>
        ${f.model_review && f.model_review.used ? `<div class="block"><span class="kicker">Model review</span><p>${esc(f.model_review.model)} suggests <strong>${esc(f.model_review.canonical)}</strong> as the canonical form.</p></div>` : ""}
      </div>`;
    $$(".ctx").forEach((b) => b.addEventListener("click", () => toggleCtx(b, f.locations[+b.dataset.j])));
    $("#copy").addEventListener("click", () => copyText(`${nameOf(f.type)}: ${f.title}\n` + f.locations.map((l) => `E${l.episode} ${l.block} ${l.time}`.trim()).join("\n"), "Locations copied"));
  }
  async function toggleCtx(btn, l) {
    const out = $("#ctx-" + btn.dataset.j);
    if (btn.getAttribute("aria-expanded") === "true") { out.innerHTML = ""; btn.setAttribute("aria-expanded", "false"); btn.textContent = "Show surrounding lines"; return; }
    btn.disabled = true;
    try {
      const c = await api(`/api/context?show=${encodeURIComponent(state.show.id)}&episode=${encodeURIComponent(l.episode)}&block=${encodeURIComponent(l.block)}`);
      out.innerHTML = `<div class="transcript">${c.cues.map((q) => `<div class="line${q.id === c.target ? " target" : ""}${q.kind !== "dialogue" ? " action" : ""}"><span class="t">${esc(q.time)}</span><div>${q.kind === "dialogue" ? `<div class="who">${esc(q.speaker)}</div>` : ""}<div class="txt">${esc(q.text)}</div></div></div>`).join("")}</div>`;
      btn.setAttribute("aria-expanded", "true"); btn.textContent = "Hide surrounding lines";
    } catch (e) { out.innerHTML = `<p class="small muted">Couldn't load the surrounding lines: ${esc(e.message)}</p>`; }
    btn.disabled = false;
  }

  // ---------- Checks ----------
  function method() {
    view.innerHTML = `
      <div class="view"><article class="prose">
        <h1 class="h1">What the checker looks for.</h1>
        <p class="lead">Seven checks, all plain rules. Each finding points to an episode, a cue and a time, and is a lead for an editor to confirm rather than a verdict.</p>
        ${Object.entries(CHECKS).map(([k, [n, d]]) => `<h2>${esc(n)}</h2><p>${esc(d)}</p><p class="small"><span class="mono">${k}</span></p>`).join("")}
        <h2>What it doesn't check yet</h2>
        <p>Costumes, props, injuries and where characters are. It also can't link very distant spellings, such as Harrowgate and Harwick, or tell a typo from a deliberate alias. A show bible with the canonical names would fix both.</p>
      </article></div>`;
  }

  const go = router([
    [/^\/$/, home],
    [/^\/findings$/, list],
    [/^\/findings\/(\d+)$/, detail],
    [/^\/method$/, method],
  ], { titleSuffix: "Continuity Checker", nav: (p) => (p.startsWith("/findings") ? "findings" : p === "/method" ? "method" : "home") });

  view.innerHTML = `<div class="view"><h1 class="h1">Loading…</h1></div>`;
  boot();
})();
