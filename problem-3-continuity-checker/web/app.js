/* Continuity Checker front end. Uses /api/shows, /api/check, /api/results, /api/context, /api/export. */
(function () {
  const { esc, icon, api, openSheet, closeSheet, trapTab, wireNav, copyText } = window.UI;
  const $ = (s) => document.querySelector(s);
  const CHECKS = {
    NAME_DRIFT: ["Name spelled differently", "One person or place is spelled several ways across episodes."],
    LABEL_ALIAS: ["One character, two labels", "The same character appears under more than one speaker label."],
    UNNAMED_RECURRING: ["Recurring character has no name", "A speaker who recurs across episodes is known only by a description, so voice and character assets can't be keyed to them."],
    SPEECH_RATE: ["Line too fast to speak", "A line has more words than can be spoken in its time slot (over 4.5 words a second is a warning, over 5 an error)."],
    SELF_OVERLAP: ["Speaker overlaps themselves", "A speaker starts a new line before their previous one ends."],
    SCENE_BOUNDS: ["Cue outside its scene", "A cue falls outside its scene's time range, or scenes overlap or leave gaps."],
    CONTINUITY_REF: ["Wrong previous episode", "An episode's continuity notes refer to an episode that isn't the one before it."],
  };
  const nameOf = (t) => (CHECKS[t] || [t])[0];
  let shows = [], current = null, data = null, filtered = [], openIdx = -1, sev = "";

  $("#navBtn").innerHTML = icon("menu"); $("#brandIcon").innerHTML = icon("checklist");
  $("#navIcon1").innerHTML = icon("play"); $("#navIcon2").innerHTML = icon("list");
  $("#searchIcon").innerHTML = icon("search"); $("#sheetClose").innerHTML = icon("close");
  $("#checkBtn").innerHTML = icon("play") + "Run checks";
  $("#exportBtn").innerHTML = icon("download") + "Export CSV";
  $("#copyBtn").innerHTML = icon("copy") + "Copy locations";
  $("#checkList").innerHTML = Object.values(CHECKS).map(([n, d]) => `<p><b>${esc(n)}.</b> ${esc(d)}</p>`).join("") +
    "<p>Checks are rules, not a model, so the same screenplay always gives the same report. Each finding is a lead for an editor to confirm.</p>";
  wireNav(document.querySelector(".app"));

  function route() {
    const r = location.hash.startsWith("#/findings") ? "findings" : "check";
    if (r === "findings" && !data) { location.hash = "#/"; return; }
    $("#view-check").hidden = r !== "check"; $("#view-findings").hidden = r !== "findings";
    document.querySelectorAll(".nav-item").forEach((a) => { if (a.dataset.route === r) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    document.title = (r === "findings" ? "Findings" : "Run checks") + " · Continuity Checker";
  }
  window.addEventListener("hashchange", route);

  // Once a report exists, "View findings" is the main action and checking again becomes secondary.
  function setPrimary(has) {
    $("#checkBtn").className = "btn " + (has ? "outlined" : "filled");
    $("#checkBtn").innerHTML = icon("play") + (has ? "Check again" : "Run checks");
    $("#viewBtn").className = "btn filled";
  }
  const banner = (kind, html) => `<div class="banner ${kind}">${icon(kind === "success" ? "check" : kind)}<div>${html}</div></div>`;

  async function loadShows() {
    try { shows = (await api("/api/shows")).shows; }
    catch (e) { $("#showHint").textContent = "Could not load shows: " + e.message; return; }
    $("#showSelect").innerHTML = shows.map((s) => `<option value="${esc(s.id)}">${esc(s.name)} (${s.episodes} episodes)</option>`).join("");
    $("#checkBtn").disabled = !shows.length;
    $("#showSelect").addEventListener("change", onShow);
    await onShow();
  }

  async function onShow() {
    current = shows.find((s) => s.id === $("#showSelect").value);
    data = null; $("#viewBtn").hidden = true; $("#statusArea").innerHTML = ""; setPrimary(current.has_results);
    $("#showHint").textContent = current.has_results ? `Last checked ${current.checked_at}. View that report or check again.` : "Not checked yet. Checking takes a second or two.";
    if (current.has_results) { try { setData(await api("/api/results?show=" + encodeURIComponent(current.id)), false); } catch (e) { /* no report */ } }
    updateNav();
  }

  $("#checkBtn").addEventListener("click", async () => {
    const b = $("#checkBtn"); b.disabled = true; $("#showSelect").disabled = true;
    $("#statusArea").innerHTML = `<p class="title-sm">Checking ${esc(current.name)}</p><div class="progress" aria-hidden="true"></div>`;
    try {
      const res = await api("/api/check", { body: { show: current.id } });
      current.has_results = true; $("#showHint").textContent = "Checked just now."; setPrimary(true); setData(res, true);
      const e = res.findings.filter((f) => f.severity === "error").length;
      $("#statusArea").innerHTML = banner("success", `Checked ${res.run.episodes} episodes in ${res.run.runtime_seconds} s. Found ${res.findings.length} issues, ${e} of them errors.`);
    } catch (err) {
      $("#statusArea").innerHTML = banner("error", esc(err.message));
    } finally { b.disabled = false; $("#showSelect").disabled = false; }
  });
  $("#viewBtn").addEventListener("click", () => { location.hash = "#/findings"; $("#main").focus(); });
  $("#exportBtn").addEventListener("click", () => { location.href = "/api/export?show=" + encodeURIComponent(current.id); });

  function setData(res, fresh) {
    data = res; data.findings.forEach((f, i) => (f.n = i + 1));
    $("#viewBtn").hidden = false; $("#viewBtn").textContent = `View ${res.findings.length} findings`;
    if (fresh) $("#viewBtn").focus();
    updateNav(); build();
  }
  function updateNav() {
    const n = data ? data.findings.length : 0;
    $("#navCount").textContent = n || ""; $("#navFindings").setAttribute("aria-disabled", String(!n)); route();
  }

  function build() {
    const fs = data.findings, r = data.run;
    const errors = fs.filter((f) => f.severity === "error").length, warns = fs.filter((f) => f.severity === "warning").length;
    const eps = new Set(fs.flatMap((f) => f.episodes));
    $("#crumbShow").textContent = r.show;
    $("#findSummary").textContent = errors ? `Fix the ${errors} errors before voice and video generation. Warnings are worth a look but may be intended.` : "No errors found. Review the warnings, which may be intended.";
    $("#stats").innerHTML = [[errors, "Errors"], [warns, "Warnings"], [`${eps.size} of ${r.episodes}`, "Episodes affected"], [r.blocks.toLocaleString(), "Cues checked"]]
      .map(([v, l]) => `<div class="stat"><div class="value">${esc(v)}</div><div class="label">${esc(l)}</div></div>`).join("");
    const types = [...new Set(fs.map((f) => f.type))];
    $("#typeFilter").innerHTML = '<option value="">All checks</option>' + types.map((t) => `<option value="${t}">${esc(nameOf(t))} (${fs.filter((f) => f.type === t).length})</option>`).join("");
    $("#epFilter").innerHTML = '<option value="">All episodes</option>' + [...eps].sort((a, b) => a - b).map((e) => `<option value="${e}">Episode ${e}</option>`).join("");
    apply();
  }

  const sevBadge = (s) => `<span class="status ${s === "error" ? "error" : "warning"}">${icon(s === "error" ? "error" : "warning")}${s === "error" ? "Error" : "Warning"}</span>`;
  const epList = (eps) => eps.length > 6 ? `${eps.slice(0, 5).join(", ")} +${eps.length - 5} more` : eps.join(", ");

  function apply() {
    const q = $("#q").value.trim().toLowerCase(), t = $("#typeFilter").value, ep = $("#epFilter").value;
    filtered = data.findings.filter((f) => (!sev || f.severity === sev) && (!t || f.type === t) && (!ep || f.episodes.includes(+ep)) &&
      (!q || (f.title + " " + f.locations.map((l) => l.text).join(" ")).toLowerCase().includes(q)));
    $("#rows").innerHTML = filtered.map((f, i) => `<tr data-i="${i}" tabindex="0" aria-label="${esc(f.severity)}: ${esc(nameOf(f.type))}. Open details">
        <td>${sevBadge(f.severity)}</td>
        <td><div class="title-sm">${esc(nameOf(f.type))}</div><span class="clamp body-md muted">${esc(f.title)}</span></td>
        <td class="hide-md"><span class="mono body-sm muted">${esc(f.type)}</span></td>
        <td data-label="Episodes"><span class="eps">${esc(epList(f.episodes))}</span></td></tr>`).join("") ||
      `<tr><td colspan="4"><div class="empty"><div class="icon">${icon("search")}</div><p class="title-md">No findings match</p><p class="body-md">Try a different search or clear the filters.</p><button class="btn text" id="clearF">Clear filters</button></div></td></tr>`;
    $("#resultCount").textContent = `Showing ${filtered.length} of ${data.findings.length} findings, errors first.`;
    const c = $("#clearF"); if (c) c.addEventListener("click", clearFilters);
  }
  function clearFilters() { $("#q").value = ""; $("#typeFilter").value = ""; $("#epFilter").value = ""; setSev(""); }
  function setSev(v) { sev = v; document.querySelectorAll("[data-sev]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sev === v))); apply(); }
  document.querySelectorAll("[data-sev]").forEach((b) => b.addEventListener("click", () => setSev(b.dataset.sev)));
  $("#q").addEventListener("input", apply); $("#typeFilter").addEventListener("change", apply); $("#epFilter").addEventListener("change", apply);
  $("#rows").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-i]"); if (tr) openFinding(+tr.dataset.i, tr); });
  $("#rows").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-i]"); if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openFinding(+tr.dataset.i, tr); } });

  // ---------- Detail sheet ----------
  const sheet = $("#sheet"), scrim = $("#sheetScrim");
  function evidence(f) {
    const ev = f.evidence || {};
    if (ev.forms) {
      return `<table class="forms"><thead><tr><th scope="col">Spelling</th><th scope="col">Times</th><th scope="col">Episodes</th></tr></thead><tbody>${
        Object.entries(ev.forms).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="n">${v.count}</td><td class="n">${esc(v.episodes.join(", "))}</td></tr>`).join("")}</tbody></table>`;
    }
    if (ev.labels) {
      return `<table class="forms"><thead><tr><th scope="col">Speaker label</th><th scope="col">Lines</th></tr></thead><tbody>${
        Object.entries(ev.labels).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="n">${v}</td></tr>`).join("")}</tbody></table>`;
    }
    if (ev.likely_identity) {
      return ev.likely_identity.length ? `<p class="body-md">Most likely the named character <b>${esc(ev.likely_identity[0][0])}</b> (${ev.likely_identity[0][1]} nearby mentions)${
        ev.likely_identity.length > 1 ? `, otherwise ${ev.likely_identity.slice(1).map((x) => esc(x[0])).join(", ")}` : ""}. Confirm before renaming.</p>` : "";
    }
    if (ev.words_per_second) {
      return `<dl class="kv body-md"><dt>Words</dt><dd>${ev.words}</dd><dt>Time slot</dt><dd>${ev.seconds} s</dd><dt>Rate</dt><dd>${ev.words_per_second} words a second</dd></dl>`;
    }
    return "";
  }
  function openFinding(i, trigger) {
    openIdx = i; const f = filtered[i];
    $("#sheetKicker").innerHTML = `${sevBadge(f.severity)} <span>Finding ${f.n} of ${data.findings.length}</span>`;
    $("#sheetTitle").textContent = nameOf(f.type);
    const ev = evidence(f);
    const locs = f.locations.slice(0, 8).map((l, j) => `<div class="loc">
        <div class="loc-head"><span class="title-sm grow">Episode ${esc(l.episode)} · ${esc(l.block)}${l.time ? " · " + esc(l.time) : ""}</span>
        ${/^B\d+$/.test(l.block) ? `<button class="btn text ctx" data-j="${j}" aria-expanded="false">Show surrounding lines</button>` : ""}</div>
        <div class="loc-text">${esc(l.text)}</div><div class="ctx-out" id="ctx-${j}"></div></div>`).join("");
    $("#sheetBody").innerHTML = `
      <p class="body-lg">${esc(f.title)}</p>
      <p class="body-md muted" style="margin-top:8px">${esc((CHECKS[f.type] || ["", ""])[1])}</p>
      ${f.suggestion ? `<div class="sheet-section"><p class="title-sm">Suggested fix</p><div class="fix body-md">${esc(f.suggestion)}</div></div>` : ""}
      ${ev ? `<div class="sheet-section"><p class="title-sm">Evidence</p>${ev}</div>` : ""}
      <div class="sheet-section"><p class="title-sm">Where it happens${f.locations.length > 8 ? ` (first 8 of ${f.locations.length})` : ""}</p>${locs}</div>
      ${f.model_review && f.model_review.used ? `<div class="sheet-section"><p class="title-sm">Model review</p><p class="body-md">${esc(f.model_review.model)} suggests <b>${esc(f.model_review.canonical)}</b> as the canonical form.</p></div>` : ""}`;
    $("#sheetBody").querySelectorAll(".ctx").forEach((b) => b.addEventListener("click", () => toggleCtx(b, f.locations[+b.dataset.j])));
    $("#prevBtn").disabled = i <= 0; $("#nextBtn").disabled = i >= filtered.length - 1;
    if (!sheet.classList.contains("open")) openSheet(sheet, scrim, trigger);
    $("#sheetBody").scrollTop = 0;
  }
  async function toggleCtx(btn, l) {
    const out = $("#ctx-" + btn.dataset.j);
    if (btn.getAttribute("aria-expanded") === "true") { out.innerHTML = ""; btn.setAttribute("aria-expanded", "false"); btn.textContent = "Show surrounding lines"; return; }
    btn.disabled = true;
    try {
      const c = await api(`/api/context?show=${encodeURIComponent(current.id)}&episode=${encodeURIComponent(l.episode)}&block=${encodeURIComponent(l.block)}`);
      out.innerHTML = `<div class="transcript">${c.cues.map((q) => `<div class="line${q.id === c.target ? " mark-hook" : ""}${q.kind !== "dialogue" ? " action" : ""}"><span class="t">${esc(q.time)}</span><div>${
        q.kind === "dialogue" ? `<div class="who">${esc(q.speaker)}</div>` : ""}<div class="txt">${esc(q.text)}</div></div></div>`).join("")}</div>`;
      btn.setAttribute("aria-expanded", "true"); btn.textContent = "Hide surrounding lines";
    } catch (e) { out.innerHTML = `<p class="body-sm muted">Couldn't load the surrounding lines: ${esc(e.message)}</p>`; }
    btn.disabled = false;
  }
  $("#sheetClose").addEventListener("click", () => closeSheet(sheet, scrim));
  scrim.addEventListener("click", () => closeSheet(sheet, scrim));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sheet.classList.contains("open")) closeSheet(sheet, scrim); trapTab(sheet, e); });
  $("#prevBtn").addEventListener("click", () => openIdx > 0 && openFinding(openIdx - 1));
  $("#nextBtn").addEventListener("click", () => openIdx < filtered.length - 1 && openFinding(openIdx + 1));
  $("#copyBtn").addEventListener("click", () => {
    const f = filtered[openIdx];
    copyText(`${nameOf(f.type)}: ${f.title}\n` + f.locations.map((l) => `E${l.episode} ${l.block} ${l.time}`.trim()).join("\n"), "Locations copied");
  });

  route(); loadShows();
})();
