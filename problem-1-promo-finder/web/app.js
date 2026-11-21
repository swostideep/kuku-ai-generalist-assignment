/* Promo Finder front end. Uses /api/shows, /api/analyse, /api/status, /api/results. */
(function () {
  const { esc, icon, api, openSheet, closeSheet, trapTab, wireNav, copyText } = window.UI;
  const $ = (s) => document.querySelector(s);
  let shows = [], current = null, data = null, filtered = [], openIdx = -1, poll = null;

  $("#navBtn").innerHTML = icon("menu"); $("#brandIcon").innerHTML = icon("movie");
  $("#navIcon1").innerHTML = icon("play"); $("#navIcon2").innerHTML = icon("list");
  $("#searchIcon").innerHTML = icon("search"); $("#sheetClose").innerHTML = icon("close");
  $("#analyseBtn").innerHTML = icon("play") + "Analyse screenplay";
  $("#copyBtn").innerHTML = icon("copy") + "Copy timestamps";
  wireNav(document.querySelector(".app"));

  // ---------- Routing ----------
  function route() {
    const r = location.hash.startsWith("#/promos") ? "promos" : "analyse";
    if (r === "promos" && !data) { location.hash = "#/"; return; }
    $("#view-analyse").hidden = r !== "analyse"; $("#view-promos").hidden = r !== "promos";
    document.querySelectorAll(".nav-item").forEach((a) => { if (a.dataset.route === r) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    document.title = (r === "promos" ? "Ranked promos" : "Analyse") + " · Promo Finder";
  }
  window.addEventListener("hashchange", route);

  // ---------- Analyse view ----------
  async function loadShows() {
    try {
      shows = (await api("/api/shows")).shows;
    } catch (e) { $("#showHint").textContent = "Could not load shows: " + e.message; return; }
    $("#showSelect").innerHTML = shows.map((s) => `<option value="${esc(s.id)}">${esc(s.name)} (${s.episodes} episodes)</option>`).join("");
    $("#analyseBtn").disabled = !shows.length;
    $("#showSelect").addEventListener("change", onShow);
    await onShow();
  }

  async function onShow() {
    current = shows.find((s) => s.id === $("#showSelect").value);
    data = null; updateNav();
    $("#viewBtn").hidden = true; setPrimary(current.has_results);
    $("#showHint").textContent = current.has_results ? `Last analysed ${current.analysed_at}. View those results or analyse again.` : "Not analysed yet. Analysis takes about a minute for 50 episodes.";
    $("#statusArea").innerHTML = "";
    if (current.has_results) await loadResults(false);
    const st = await api("/api/status?show=" + encodeURIComponent(current.id));
    if (st.state === "running") track();
  }

  $("#analyseBtn").addEventListener("click", async () => {
    try { await api("/api/analyse", { body: { show: current.id } }); track(); }
    catch (e) { $("#statusArea").innerHTML = banner("error", "Could not start the analysis. " + e.message); }
  });
  $("#viewBtn").addEventListener("click", () => { location.hash = "#/promos"; $("#main").focus(); });

  // Once results exist, "View" is the main action and analysing again becomes secondary.
  function setPrimary(hasResults) {
    $("#analyseBtn").className = "btn " + (hasResults ? "outlined" : "filled");
    $("#analyseBtn").innerHTML = icon("play") + (hasResults ? "Analyse again" : "Analyse screenplay");
    $("#viewBtn").className = "btn filled";
  }
  const banner = (kind, text) => `<div class="banner ${kind}">${icon(kind === "success" ? "check" : kind)}<div>${esc(text)}</div></div>`;

  function track() {
    $("#analyseBtn").disabled = true; $("#showSelect").disabled = true;
    clearInterval(poll);
    const tick = async () => {
      const st = await api("/api/status?show=" + encodeURIComponent(current.id)).catch(() => ({ state: "error", message: "Lost contact with the server." }));
      if (st.state === "running") {
        $("#statusArea").innerHTML = `<p class="title-sm">Analysing ${esc(current.name)}</p>${st.total ? `<div class="progress determinate" role="progressbar" aria-label="Analysis progress" aria-valuemin="0" aria-valuemax="${st.total}" aria-valuenow="${st.done}"><span style="width:${Math.max(3, (100 * st.done) / st.total)}%"></span></div>` : '<div class="progress" aria-hidden="true"></div>'}<p class="body-md muted">${esc(st.message)}</p>`;
        return;
      }
      clearInterval(poll); $("#analyseBtn").disabled = false; $("#showSelect").disabled = false;
      if (st.state === "done") {
        current.has_results = true; current.analysed_at = "just now";
        $("#showHint").textContent = "Analysed just now.";
        await loadResults(true); setPrimary(true);
        $("#statusArea").innerHTML = banner("success", `Analysis complete. ${st.message}`);
      } else if (st.state === "error") {
        $("#statusArea").innerHTML = banner("error", st.message + " Check the show folder and try again.");
      }
    };
    tick(); poll = setInterval(tick, 800);
  }

  async function loadResults(fresh) {
    try { data = await api("/api/results?show=" + encodeURIComponent(current.id)); }
    catch (e) { data = null; updateNav(); return; }
    $("#viewBtn").hidden = false; $("#viewBtn").textContent = `View ${data.promos.length} ranked promos`;
    if (fresh) $("#viewBtn").focus();
    updateNav(); buildResults();
  }

  function updateNav() {
    const n = data ? data.promos.length : 0;
    $("#navCount").textContent = n ? n : "";
    $("#navPromos").setAttribute("aria-disabled", String(!n));
    route();
  }

  // ---------- Promos view ----------
  let bands = [0, 0];
  function strength(p) {
    const s = p.final_score;
    if (s >= bands[1]) return ["success", "Strong"];
    if (s >= bands[0]) return ["info", "Solid"];
    return ["neutral", "Weaker"];
  }

  function buildResults() {
    const r = data.run, ps = data.promos;
    const sc = ps.map((p) => p.final_score).sort((a, b) => a - b);
    bands = [sc[Math.floor(sc.length / 3)], sc[Math.floor((2 * sc.length) / 3)]];
    const covered = new Set(ps.map((p) => p.episode)).size;
    $("#crumbShow").textContent = r.show;
    $("#promoSummary").textContent = `${ps.length} clips you could post, ranked. Open one to see its hook, cliffhanger, timestamps and the screenplay lines behind it.`;
    $("#stats").innerHTML = [
      [ps.length, "Ranked promos"], [`${covered} of ${r.episode_count}`, "Episodes with a promo"],
      [r.windows_scored.toLocaleString(), "Clip windows checked"], [r.episodes_without_promo.length, "Episodes with nothing strong enough"],
    ].map(([v, l]) => `<div class="stat"><div class="value">${esc(v)}</div><div class="label">${esc(l)}</div></div>`).join("");
    const eps = [...new Set(ps.map((p) => p.episode))].sort((a, b) => a - b);
    $("#epFilter").innerHTML = '<option value="">All episodes</option>' + eps.map((e) => `<option value="${e}">Episode ${e}</option>`).join("");
    applyFilters();
  }

  function applyFilters() {
    const q = $("#q").value.trim().toLowerCase(), ep = $("#epFilter").value, wave = $("#waveChip").getAttribute("aria-pressed") === "true";
    filtered = data.promos.filter((p) => (!ep || String(p.episode) === ep) && (!wave || p.post_wave === "first wave") &&
      (!q || (p.hook.text + " " + p.cliffhanger.text + " " + p.why_it_works).toLowerCase().includes(q)));
    $("#rows").innerHTML = filtered.map((p, i) => {
      const s = p.segments[0], [cls, lbl] = strength(p);
      return `<tr data-i="${i}" tabindex="0" aria-label="Rank ${p.rank}, episode ${p.episode}. Open details">
        <td data-label="Rank"><span class="rank">#${p.rank}</span>${p.post_wave === "first wave" ? `<span class="wave-dot status info" title="In the first 10 to post">First 10</span>` : ""}</td>
        <td><div class="title-sm">Episode ${p.episode}</div><div class="clip-when num">${s.start_time} – ${s.end_time} · ${Math.round(p.duration_seconds)} s</div></td>
        <td class="col-hook"><span class="clamp">${esc(p.hook.text)}</span></td>
        <td class="hide-md"><span class="clamp">${esc(p.cliffhanger.text)}</span></td>
        <td data-label="Strength"><span class="status ${cls}">${lbl}</span></td></tr>`;
    }).join("") || `<tr><td colspan="5"><div class="empty"><div class="icon">${icon("search")}</div><p class="title-md">No promos match</p><p class="body-md">Try a different search or clear the filters.</p><button class="btn text" id="clearF">Clear filters</button></div></td></tr>`;
    $("#resultCount").textContent = `Showing ${filtered.length} of ${data.promos.length} promos. Strength compares each promo with the others in this show (top, middle and bottom third by score).`;
    const c = $("#clearF"); if (c) c.addEventListener("click", () => { $("#q").value = ""; $("#epFilter").value = ""; $("#waveChip").setAttribute("aria-pressed", "false"); applyFilters(); });
  }
  $("#q").addEventListener("input", applyFilters);
  $("#epFilter").addEventListener("change", applyFilters);
  $("#waveChip").addEventListener("click", (e) => { const b = e.currentTarget; b.setAttribute("aria-pressed", String(b.getAttribute("aria-pressed") !== "true")); applyFilters(); });
  $("#rows").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-i]"); if (tr) openPromo(+tr.dataset.i, tr); });
  $("#rows").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-i]"); if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openPromo(+tr.dataset.i, tr); } });

  // ---------- Detail sheet ----------
  const sheet = $("#sheet"), scrim = $("#sheetScrim");
  const labelOf = (r) => ({ "threat/danger": "danger", "short, punchy line": "short and punchy", "cuts right before the reply": "cuts before the reply" }[r] || r);
  function openPromo(i, trigger) {
    openIdx = i; const p = filtered[i], s = p.segments[0];
    document.querySelectorAll("#rows tr").forEach((tr) => tr.setAttribute("aria-selected", String(+tr.dataset.i === i)));
    $("#sheetTitle").textContent = `#${p.rank} · Episode ${p.episode}`;
    $("#sheetSub").textContent = `${s.start_time} → ${s.end_time} · ${p.duration_seconds.toFixed(1)} seconds` + (p.post_wave === "first wave" ? " · first 10 to post" : "");
    const meter = (k, l) => `<div class="meter"><span>${l}</span><div class="bar"><span style="width:${p.scores[k]}%"></span></div><span class="val">${Math.round(p.scores[k])}</span></div>`;
    const quote = (b, cls) => `<div class="quote ${cls}"><span class="who">${esc(b.speaker || b.kind.toUpperCase())}${b.emotion ? " · " + esc(b.emotion) : ""} · ${esc(b.time)}</span>${esc(b.text)}</div>`;
    const reasons = (rs) => rs.filter((r) => !r.startsWith("delivered")).map((r) => `<span class="status neutral">${esc(labelOf(r))}</span>`).join("");
    const lines = p.transcript.filter((b) => b.kind !== "camera").map((b) => {
      const mark = b.block_id === p.hook.block_id ? " mark-hook" : b.block_id === p.cliffhanger.block_id ? " mark-cliff" : "";
      return `<div class="line${mark}${b.kind !== "dialogue" ? " action" : ""}"><span class="t">${esc(b.time)}</span><div>${b.kind === "dialogue" ? `<div class="who">${esc(b.speaker)}</div>` : ""}<div class="txt">${esc(b.text)}</div></div></div>`;
    }).join("");
    $("#sheetBody").innerHTML = `
      <p class="body-lg">${esc(p.why_it_works)}</p>
      <div class="sheet-section"><p class="title-sm">Hook: the first 3 seconds</p>${quote(p.hook, "")}<div class="reasons">${reasons(p.hook_reasons)}</div></div>
      <div class="sheet-section"><p class="title-sm">Cliffhanger: the last line before the cut</p>${quote(p.cliffhanger, "cliff")}<div class="reasons">${reasons(p.cliffhanger_reasons)}</div></div>
      <div class="sheet-section"><p class="title-sm">Clip</p><dl class="kv body-md">
        <dt>Episode</dt><dd>${p.episode} <span class="muted">(${esc(p.episode_file)})</span></dd>
        <dt>Segment</dt><dd class="num">${s.start_time} → ${s.end_time}</dd>
        <dt>Script cues</dt><dd class="mono">${esc(s.first_block)} → ${esc(s.last_block)}</dd>
        <dt>Clarity notes</dt><dd>${p.clarity_notes.length ? esc(p.clarity_notes.join("; ")) : "None"}</dd></dl></div>
      <details class="disclosure sheet-section"><summary>Scores</summary><div class="content">
        ${meter("hook", "Hook")}${meter("cliffhanger", "Cliffhanger")}${meter("standalone", "Standalone")}${meter("tension_arc", "Tension arc")}${meter("pacing", "Pacing")}
        <p class="body-sm muted" style="margin-top:12px">Overall ${p.final_score} (${esc(p.score_source)}). Scores rank clips within this show; they are not predictions of ad performance.</p></div></details>
      <details class="disclosure"><summary>Screenplay excerpt (${p.transcript.filter((b) => b.kind !== "camera").length} lines)</summary><div class="content">
        <div class="legend body-sm"><span class="h">Hook</span><span class="c">Cliffhanger</span></div><div class="transcript">${lines}</div></div></details>`;
    $("#prevBtn").disabled = i <= 0; $("#nextBtn").disabled = i >= filtered.length - 1;
    if (!sheet.classList.contains("open")) openSheet(sheet, scrim, trigger);
    $("#sheetBody").scrollTop = 0;
  }
  $("#sheetClose").addEventListener("click", () => closeSheet(sheet, scrim));
  scrim.addEventListener("click", () => closeSheet(sheet, scrim));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sheet.classList.contains("open")) closeSheet(sheet, scrim); trapTab(sheet, e); });
  $("#prevBtn").addEventListener("click", () => openIdx > 0 && openPromo(openIdx - 1));
  $("#nextBtn").addEventListener("click", () => openIdx < filtered.length - 1 && openPromo(openIdx + 1));
  $("#copyBtn").addEventListener("click", () => {
    const p = filtered[openIdx], s = p.segments[0];
    copyText(`Episode ${p.episode} (${p.episode_file}): ${s.start_time} - ${s.end_time}`, "Timestamps copied");
  });

  route(); loadShows();
})();
