/* Promo Finder site. Talks to GET /api/shows, POST /api/analyse, GET /api/status, GET /api/results (unchanged). */
(function () {
  const { esc, icon, art, icons, meta, $, $$, router, header, api, copyText } = window.UI;
  const view = $("#view");
  const state = { shows: [], show: null, data: null, job: null, poll: null, q: "", ep: "", wave: false };

  icons(document); header();
  const tickMeta = () => meta($("#identMeta"), state.show && state.show.name);
  setInterval(tickMeta, 30000);

  // ---------- Data ----------
  async function boot() {
    try { state.shows = (await api("/api/shows")).shows; }
    catch (e) { state.error = "Couldn't load the shows: " + e.message; }
    let saved = null; try { saved = sessionStorage.getItem("pf-show"); } catch (e) { /* storage unavailable */ }
    state.show = state.shows.find((s) => s.id === saved) || state.shows[0] || null;
    tickMeta();
    if (state.show && state.show.has_results) await loadResults();
    if (state.show) { const st = await api("/api/status?show=" + encodeURIComponent(state.show.id)).catch(() => null); if (st && st.state === "running") track(); }
    go();
  }
  async function loadResults() {
    try { state.data = await api("/api/results?show=" + encodeURIComponent(state.show.id)); prep(); }
    catch (e) { state.data = null; }
  }
  function prep() {
    const sc = state.data.promos.map((p) => p.final_score).sort((a, b) => a - b);
    state.bands = [sc[Math.floor(sc.length / 3)], sc[Math.floor((2 * sc.length) / 3)]];
  }
  async function pickShow(id) {
    state.show = state.shows.find((s) => s.id === id); state.data = null; state.job = null;
    try { sessionStorage.setItem("pf-show", id); } catch (e) { /* ignore */ }
    tickMeta();
    if (state.show.has_results) await loadResults();
    renderLive();
  }
  async function analyse() {
    try { await api("/api/analyse", { body: { show: state.show.id } }); track(); }
    catch (e) { state.job = { state: "error", message: e.message }; renderLive(); }
  }
  function track() {
    clearInterval(state.poll);
    const tick = async () => {
      const st = await api("/api/status?show=" + encodeURIComponent(state.show.id)).catch(() => ({ state: "error", message: "Lost contact with the server." }));
      state.job = st;
      if (st.state !== "running") {
        clearInterval(state.poll);
        if (st.state === "done") { state.show.has_results = true; state.show.analysed_at = "just now"; await loadResults(); }
      }
      renderLive();
    };
    tick(); state.poll = setInterval(tick, 800);
  }

  // ---------- Helpers ----------
  const strength = (p) => p.final_score >= state.bands[1] ? ["strong", "Strong"] : p.final_score >= state.bands[0] ? ["", "Solid"] : ["quiet", "Weaker"];
  const seg = (p) => p.segments[0];
  const span = (p) => `${seg(p).start_time}–${seg(p).end_time}`;
  const pad = (n) => String(n).padStart(2, "0");
  const LABEL = { "threat/danger": "danger", "short, punchy line": "short and punchy", "cuts right before the reply": "cuts before the reply" };

  // ---------- Home ----------
  function home() {
    view.innerHTML = `
      <section class="hero">
        <div class="rise">
          <h1 class="display">Find the thirty seconds that <span class="soft">sell a show.</span></h1>
          <p class="lead">Promo Finder reads every episode of a microdrama script, checks every 20 to 60 second window, and ranks the clips with the strongest opening and an unresolved ending. You decide what gets posted.</p>
          <div class="actions"><a class="btn primary" href="#/promos" id="heroCta">Review promos${icon("arrowRight")}</a><a class="text-link" href="#/method">How it chooses</a></div>
        </div>
        <div class="stage rise"><div class="live" id="live" aria-live="polite"></div></div>
      </section>

      <section class="section" aria-labelledby="how">
        <h2 class="title" id="how">How it works</h2>
        <div class="cards" style="--cols:4">
          ${[["script", "Reads the script", "Every cue, every second.", "Each line becomes a block with its speaker, timing and the writer's acting direction. Anything unreadable is reported, never skipped."],
             ["cut", "Finds clean cuts", "Never inside a line.", "A clip only starts and ends between spoken lines, and snaps to the nearest camera cut within a second and a half."],
             ["wave", "Scores both ends", "The first three seconds and the last line.", "Every window is scored on its hook, its cliffhanger, whether it makes sense alone, its tension and its pace."],
             ["person", "Leaves you the call", "Ranked, explained, yours to choose.", "At most two clips per episode, each with a one-line reason, so an editor can accept or reject it in seconds."]]
            .map(([a, t, o, m], i) => `<article class="card"><p class="no">${String(i + 1).padStart(3, "0")}</p><div class="art">${art(a)}</div><h3 class="h3">${t}</h3><p class="one">${o}</p><p class="more">${m}</p></article>`).join("")}
        </div>
      </section>

      <section class="section" aria-labelledby="gates">
        <div class="stage"><div class="showcase">
          <div>
            <h2 class="h2" id="gates">A strong ending can't rescue a weak opening.</h2>
            <p>Adding scores together let great cliffhangers hide dull first lines. So each part has its own minimum, and a clip has to clear every one. The minimums adjust to the show, so a quieter series still gets promos.</p>
          </div>
          <div class="live"><ul class="spec" aria-label="Default minimums">
            <li><span class="k">Hook, first three seconds</span><span class="v">at least 45</span></li>
            <li><span class="k">Cliffhanger, the last line</span><span class="v">at least 45</span></li>
            <li><span class="k">Makes sense to a stranger</span><span class="v">at least 40</span></li>
            <li><span class="k">Clips per episode</span><span class="v">at most 2</span></li>
            <li><span class="k">Overlap between two clips</span><span class="v">under 30%</span></li>
          </ul></div>
        </div></div>
      </section>`;
    renderLive();
  }

  function renderLive() {
    const el = $("#live"); if (!el) return;
    const s = state.show, d = state.data, j = state.job;
    if (state.error) { el.innerHTML = `<div class="note bad">${icon("alertCircle")}<div>${esc(state.error)}</div></div>`; return; }
    if (!s) { el.innerHTML = `<p class="h3">No shows found</p><p class="sub">Start the app with <span class="mono">--shows</span> pointing at a folder of episode files.</p>`; return; }
    const picker = state.shows.length > 1 ? `<div class="field show-pick"><label for="showPick">Show</label><select class="select" id="showPick">${state.shows.map((x) => `<option value="${esc(x.id)}" ${x.id === s.id ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></div>` : "";
    let body;
    if (j && j.state === "running") {
      const pct = j.total ? Math.round((100 * j.done) / j.total) : 0;
      body = `<div class="top"><span>Analysing ${esc(s.name)}</span><span class="num">${pct}%</span></div>
        <div class="figure-row"><span class="figure">${j.done}</span><span class="unit">of ${j.total} episodes</span></div>
        <div class="status-line"><div class="progress" role="progressbar" aria-label="Analysis progress" aria-valuemin="0" aria-valuemax="${j.total}" aria-valuenow="${j.done}"><span style="width:${Math.max(2, pct)}%"></span></div>${esc(j.message)}</div>`;
    } else if (d) {
      const r = d.run, top = d.promos.slice(0, 3), covered = new Set(d.promos.map((p) => p.episode)).size;
      body = `<div class="top"><span>${esc(s.name)}</span><span>${s.analysed_at ? "Analysed " + esc(s.analysed_at) : ""}</span></div>
        <div class="figure-row"><span class="figure">${d.promos.length}</span><span class="unit">promos ready to review</span></div>
        <p class="sub">From ${r.windows_scored.toLocaleString("en-IN")} clip windows, with at least one promo in ${covered} of ${r.episode_count} episodes.</p>
        <div class="meter" aria-hidden="true"><span style="width:${(100 * covered) / r.episode_count}%"></span></div>
        <ul class="mini" aria-label="Top three promos">${top.map((p) => `<li><span class="k">${pad(p.rank)}</span><span class="t">“${esc(p.hook.text)}”</span><span class="m">Ep. ${p.episode}</span></li>`).join("")}</ul>
        <div class="actions"><a class="btn primary" href="#/promos">See all ${d.promos.length}</a><button class="btn secondary" id="runBtn" type="button">Analyse again</button></div>`;
    } else {
      body = `<div class="top"><span>${esc(s.name)}</span><span>${s.episodes} episodes</span></div>
        <div class="figure-row"><span class="figure">0</span><span class="unit">promos yet</span></div>
        <p class="sub">Analysis reads all ${s.episodes} episodes; fifty take about a minute.</p>
        <div class="actions"><button class="btn primary" id="runBtn" type="button">${icon("play")}Analyse the script</button></div>`;
    }
    if (j && j.state === "error") body += `<div class="note bad" style="margin-top:20px">${icon("alertCircle")}<div>${esc(j.message)} Check the show folder and try again.</div></div>`;
    el.innerHTML = body + picker;
    const run = $("#runBtn"); run && run.addEventListener("click", analyse);
    const pk = $("#showPick"); pk && pk.addEventListener("change", (e) => pickShow(e.target.value));
    const cta = $("#heroCta"); if (cta) cta.toggleAttribute("hidden", !d);
  }

  // ---------- Promos ----------
  function filtered() {
    const q = state.q.trim().toLowerCase();
    return state.data.promos.filter((p) => (!state.ep || String(p.episode) === state.ep) && (!state.wave || p.post_wave === "first wave") &&
      (!q || (p.hook.text + " " + p.cliffhanger.text + " " + p.why_it_works).toLowerCase().includes(q)));
  }
  function noData() {
    view.innerHTML = `<div class="view"><h1 class="h1">No promos yet</h1><div class="empty"><p>Run an analysis first. It reads every episode of the script and ranks the best clips.</p><div class="actions"><a class="btn primary" href="#/">Go to analysis</a></div></div></div>`;
  }
  function list() {
    if (!state.data) return noData();
    const d = state.data, r = d.run, eps = [...new Set(d.promos.map((p) => p.episode))].sort((a, b) => a - b);
    const wave = d.promos.filter((p) => p.post_wave === "first wave").length;
    view.innerHTML = `
      <div class="view">
        <div class="view-head"><div><h1 class="h1">Promos</h1>
          <p class="lead">${d.promos.length} clips from ${esc(r.show)}, ranked. Strength compares each clip with the others in this show: the top, middle and bottom third.</p></div></div>
        <div class="stats">
          <div><div class="v">${d.promos.length}</div><div class="k">Ranked promos</div></div>
          <div><div class="v">${eps.length}<span class="muted" style="font-size:22px"> / ${r.episode_count}</span></div><div class="k">Episodes with a promo</div></div>
          <div><div class="v">${r.windows_scored.toLocaleString("en-IN")}</div><div class="k">Clip windows checked</div></div>
          <div><div class="v">${r.episodes_without_promo.length}</div><div class="k">Episodes with nothing strong enough</div></div>
        </div>
        <div class="toolbar" role="search">
          <div class="search">${icon("search")}<label class="sr-only" for="q">Search promos</label><input class="input" id="q" type="search" placeholder="Search the opening or closing line" value="${esc(state.q)}"></div>
          <label class="sr-only" for="ep">Episode</label>
          <select class="select" id="ep"><option value="">All episodes</option>${eps.map((e) => `<option value="${e}" ${String(e) === state.ep ? "selected" : ""}>Episode ${e}</option>`).join("")}</select>
          <div class="segmented" role="group" aria-label="Which promos">
            <button type="button" data-wave="0" aria-pressed="${!state.wave}">All<span class="count">${d.promos.length}</span></button>
            <button type="button" data-wave="1" aria-pressed="${state.wave}">First to post<span class="count">${wave}</span></button>
          </div>
        </div>
        <ul class="rows" id="rows"></ul>
        <p class="result-count" id="count" aria-live="polite"></p>
      </div>`;
    const draw = () => {
      const f = filtered();
      $("#rows").innerHTML = f.map((p) => {
        const [cls, lbl] = strength(p);
        return `<li><a class="row" href="#/promos/${p.rank}">
          <span class="lead-col">${pad(p.rank)}</span>
          <span><span class="title clamp-2">“${esc(p.hook.text)}”</span>
            <span class="meta" style="display:block">Episode ${p.episode} · ${span(p)} · ${Math.round(p.duration_seconds)} s${p.post_wave === "first wave" ? ` · <span class="first10">First to post</span>` : ""}</span>
            <span class="meta clamp-2">Cuts on “${esc(p.cliffhanger.text)}”</span></span>
          <span class="end"><span class="badge ${cls}">${lbl}</span>${icon("chevron").replace("<svg", '<svg class="chev"')}</span></a></li>`;
      }).join("") || `<li><div class="empty"><p class="h3">Nothing matches</p><p>Try another word, or clear the filters.</p><div class="actions"><button class="btn secondary" type="button" id="clear">Clear filters</button></div></div></li>`;
      $("#count").textContent = `Showing ${f.length} of ${d.promos.length}.`;
      const c = $("#clear"); c && c.addEventListener("click", () => { state.q = ""; state.ep = ""; state.wave = false; list(); });
    };
    $("#q").addEventListener("input", (e) => { state.q = e.target.value; draw(); });
    $("#ep").addEventListener("change", (e) => { state.ep = e.target.value; draw(); });
    $$("[data-wave]").forEach((b) => b.addEventListener("click", () => { state.wave = b.dataset.wave === "1"; $$("[data-wave]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); draw(); }));
    draw();
  }

  // ---------- One promo ----------
  function detail(m) {
    if (!state.data) return noData();
    const f = filtered().length ? filtered() : state.data.promos;
    const i = f.findIndex((p) => p.rank === +m[1]);
    const p = i >= 0 ? f[i] : state.data.promos.find((x) => x.rank === +m[1]);
    if (!p) { location.hash = "#/promos"; return false; }
    const prev = i > 0 ? f[i - 1] : null, next = i >= 0 && i < f.length - 1 ? f[i + 1] : null;
    const [cls, lbl] = strength(p), s = seg(p);
    const reasons = (rs) => rs.filter((r) => !r.startsWith("delivered")).map((r) => `<span class="tag">${esc(LABEL[r] || r)}</span>`).join("");
    const lines = p.transcript.filter((b) => b.kind !== "camera");
    const quote = (b, kind, title) => `<figure class="quote ${kind}"><figcaption class="who"><i></i>${title} · ${esc(b.speaker || b.kind)}${b.emotion ? ", " + esc(b.emotion.toLowerCase()) : ""} · ${esc(b.time)}</figcaption>
      <blockquote class="text">${esc(b.text)}</blockquote><div class="tags">${reasons(kind === "hook" ? p.hook_reasons : p.cliffhanger_reasons)}</div></figure>`;
    const nav = (q, label, ic) => q ? `<a class="icon-btn bordered" href="#/promos/${q.rank}" aria-label="${label}">${icon(ic)}</a>` : `<span class="icon-btn bordered" aria-hidden="true" style="opacity:.35">${icon(ic)}</span>`;
    view.innerHTML = `
      <div class="view">
        <a class="back" href="#/promos">${icon("arrowLeft")}All promos</a>
        <div class="detail-head">
          <div><p class="kicker">Promo ${p.rank} of ${state.data.promos.length}</p>
            <h1 class="h1" style="margin-top:12px">Episode ${p.episode}, ${span(p)}</h1>
            <p class="lead">${esc(p.why_it_works)}</p></div>
          <div class="detail-tools">
            <span class="badge ${cls}">${lbl}</span>
            <button class="btn secondary sm" type="button" id="copy">${icon("copy")}Copy timestamps</button>
            ${nav(prev, "Previous promo", "chevronLeft")}${nav(next, "Next promo", "chevron")}
          </div>
        </div>
        <div class="split">${quote(p.hook, "hook", "Opens with")}${quote(p.cliffhanger, "cliff", "Cuts on")}</div>

        <div class="block" style="margin-top:56px"><span class="kicker">Scores</span>
          <div class="split" style="gap:48px">
            <div class="bars">${[["hook", "Hook"], ["cliffhanger", "Cliffhanger"], ["standalone", "Stands alone"], ["tension_arc", "Tension"], ["pacing", "Pacing"]]
              .map(([k, l]) => `<div class="bar"><span>${l}</span><span class="track"><span style="width:${p.scores[k]}%"></span></span><span class="val">${Math.round(p.scores[k])}</span></div>`).join("")}</div>
            <dl class="kv">
              <dt>Overall</dt><dd>${p.final_score} <span class="muted">(${esc(p.score_source)})</span></dd>
              <dt>Duration</dt><dd>${p.duration_seconds.toFixed(1)} seconds</dd>
              <dt>File</dt><dd>${esc(p.episode_file)}</dd>
              <dt>Script cues</dt><dd class="mono">${esc(s.first_block)} to ${esc(s.last_block)}</dd>
              <dt>Clarity notes</dt><dd>${p.clarity_notes.length ? esc(p.clarity_notes.join("; ")) : "None"}</dd>
            </dl>
          </div>
          <p class="small muted" style="margin-top:20px">Scores rank clips within this show. They are not predictions of how an ad will perform.</p>
        </div>

        <div class="block">
          <details class="more"><summary>Screenplay, ${lines.length} lines${icon("chevron")}</summary><div class="content">
            <div class="legend"><span class="hook">Opening line</span><span class="cliff">Last line</span></div>
            <div class="transcript">${lines.map((b) => `<div class="line${b.block_id === p.hook.block_id ? " hook" : b.block_id === p.cliffhanger.block_id ? " cliff" : ""}${b.kind !== "dialogue" ? " action" : ""}">
              <span class="t">${esc(b.time)}</span><div>${b.kind === "dialogue" ? `<div class="who">${esc(b.speaker)}</div>` : ""}<div class="txt">${esc(b.text)}</div></div></div>`).join("")}</div>
          </div></details>
        </div>
      </div>`;
    $("#copy").addEventListener("click", () => copyText(`Episode ${p.episode} (${p.episode_file}): ${s.start_time} - ${s.end_time}`, "Timestamps copied"));
  }

  // ---------- Method ----------
  function method() {
    view.innerHTML = `
      <div class="view"><article class="prose">
        <h1 class="h1">How Promo Finder chooses a clip.</h1>
        <p class="lead">The editor's time is the scarce thing, so the tool aims for clips that work as cut, don't repeat each other, and come with a reason that can be checked in seconds.</p>
        <h2>What a good promo is</h2>
        <p>A promo is shown to someone who has never seen the show. It has to grab them in the first three seconds, make sense without context, and stop just before something is answered, so the only way to find out is to watch episode one.</p>
        <h2>What the tool does</h2>
        <ol>
          <li><strong>Reads every cue</strong> with its speaker, timing, scene and the writer's acting direction, such as “Menacing” or “Tender”.</li>
          <li><strong>Lists every legal clip</strong> between 20 and 60 seconds. A cut never falls inside a spoken line or between two halves of a sentence.</li>
          <li><strong>Scores each clip</strong> on its hook (30%), cliffhanger (30%), whether it stands alone (20%), tension (12%) and pacing (8%).</li>
          <li><strong>Applies minimums</strong> to the hook, cliffhanger and stand-alone scores separately, adjusted to the show's own range.</li>
          <li><strong>Chooses</strong> at most two clips per episode, under 30% overlap, and puts ten different episodes first, including the opening ones.</li>
        </ol>
        <h2>What it can't do</h2>
        <p>It reads text, not footage, so performance and picture quality are unknown. Rhetorical questions can look like cliffhangers, and it favours conflict over romance. Every pick still needs an editor to watch it.</p>
        <h2>Optional model review</h2>
        <p>Any OpenAI-compatible model can re-rate the finalists from the command line. It has to cite the script lines it relied on, never sees a timestamp, and the rules take over if it fails. It is off by default.</p>
      </article></div>`;
  }

  const go = router([
    [/^\/$/, home],
    [/^\/promos$/, list],
    [/^\/promos\/(\d+)$/, detail],
    [/^\/method$/, method],
  ], { titleSuffix: "Promo Finder", nav: (p) => (p.startsWith("/promos") ? "promos" : p === "/method" ? "method" : "home") });

  view.innerHTML = `<div class="view"><h1 class="h1">Loading…</h1></div>`;
  boot();
})();
