/* Plain — small shared helpers for the three sites (no dependencies): stroke icons, hash router,
   header menu, toast, copy/download and a JSON fetch wrapper. */
(function () {
  // 24px stroke icons, drawn for this kit (1.6px stroke, round joins).
  const P = {
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    arrowRight: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    arrowLeft: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    arrowUp: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    chevron: '<path d="m9 6 6 6-6 6"/>',
    chevronLeft: '<path d="m15 6-6 6 6 6"/>',
    copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 19.5h14"/>',
    mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    alert: '<path d="M12 4 2.8 19.5h18.4z"/><path d="M12 10v4.5M12 17.2v.1"/>',
    alertCircle: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v5.5M12 16.2v.1"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.1"/>',
    play: '<path d="M7 5.5v13l11-6.5z"/>',
    external: '<path d="M14 4.5h5.5V10M19.5 4.5 11 13M17 13.5v4.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 5 18V9a1.5 1.5 0 0 1 1.5-1.5H11"/>',
    film: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M3.5 9.5h17M8 5v4.5M13 5v4.5"/>',
    scale: '<path d="M12 4v16M7 20h10M5 7h14M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z"/>',
    spell: '<path d="M4 18 9 6l5 12M5.8 14h6.4M15 15.5l2 2 4-4.5"/>',
    doc: '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5M9 12.5h6M9 16h6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    // Card drawings (shown at 72px with a fine stroke)
    script: '<rect x="5" y="3.5" width="14" height="17" rx="1.5"/><path d="M8 8h8M8 11h5M8 14h8M8 17h3"/>',
    cut: '<path d="M3 12h4M17 12h4M9.5 7v10M14.5 7v10"/><circle cx="9.5" cy="5" r="1"/><circle cx="14.5" cy="19" r="1"/>',
    wave: '<path d="M3 12h2l1.5-4 2 9 2-12 2 14 2-10 1.5 5 1.5-2H21"/>',
    person: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5"/>',
    gate: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    labels: '<rect x="3.5" y="5" width="9" height="5" rx="1"/><rect x="11.5" y="14" width="9" height="5" rx="1"/><path d="M8 10v6.5h3.5"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    chat: '<path d="M4.5 6.5A2 2 0 0 1 6.5 4.5h11a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H10l-4 3.5v-3.5h0a1.5 1.5 0 0 1-1.5-1.5z"/>',
    book: '<path d="M4.5 5.5A1.5 1.5 0 0 1 6 4h12.5v14H6a1.5 1.5 0 0 0-1.5 1.5zM4.5 19.5A1.5 1.5 0 0 0 6 21h12.5M8.5 8h6"/>',
    letter: '<rect x="3.5" y="5.5" width="17" height="13" rx="1.5"/><path d="m4 6.5 8 6 8-6"/>',
    shield: '<path d="M12 3.5 5 6v5.5c0 4.2 3 7.6 7 9 4-1.4 7-4.8 7-9V6z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (name, label, stroke) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${stroke || 1.6}" stroke-linecap="round" stroke-linejoin="round" ${label ? `role="img" aria-label="${esc(label)}"` : 'aria-hidden="true" focusable="false"'}>${P[name]}</svg>`;
  const art = (name) => icon(name, null, 0.9);
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => [...(el || document).querySelectorAll(s)];

  // Fill every [data-icon] placeholder once.
  function icons(root) { $$("[data-icon]", root).forEach((el) => { el.insertAdjacentHTML("afterbegin", icon(el.dataset.icon)); el.removeAttribute("data-icon"); }); }

  // Hash router: routes = [[/regex/, handler(match)], ...]. Moves focus to the new page's h1 and sets the title.
  function router(routes, { titleSuffix, nav } = {}) {
    let first = true;
    function go() {
      const path = location.hash.replace(/^#/, "") || "/";
      for (const [re, fn] of routes) {
        const m = path.match(re);
        if (!m) continue;
        const out = fn(m);
        if (out === false) return; // handler redirected
        const h1 = $$("main h1").find((h) => h.offsetParent !== null) || $("main h1");
        if (h1) document.title = h1.textContent.trim() + (titleSuffix ? " · " + titleSuffix : "");
        if (nav) $$(".nav a").forEach((a) => { if (a.dataset.nav === nav(path)) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
        if (!first && h1) { h1.setAttribute("tabindex", "-1"); h1.focus({ preventScroll: true }); window.scrollTo(0, 0); }
        first = false;
        $(".nav") && $(".nav").classList.remove("open");
        const mb = $(".menu-btn"); mb && mb.setAttribute("aria-expanded", "false");
        return;
      }
      location.hash = "#/";
    }
    window.addEventListener("hashchange", go);
    return go;
  }

  // Header: hairline once the page scrolls; menu on small screens.
  function header() {
    const bar = $(".site-header");
    if (bar) { const on = () => bar.classList.toggle("scrolled", window.scrollY > 4); window.addEventListener("scroll", on, { passive: true }); on(); }
    const btn = $(".menu-btn"), nav = $(".nav");
    if (!btn || !nav) return;
    btn.addEventListener("click", () => { const o = !nav.classList.contains("open"); nav.classList.toggle("open", o); btn.setAttribute("aria-expanded", String(o)); if (o) nav.querySelector("a").focus(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && nav.classList.contains("open")) { nav.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); btn.focus(); } });
    document.addEventListener("click", (e) => { if (nav.classList.contains("open") && !e.target.closest(".nav, .menu-btn")) { nav.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); } });
  }

  let toastTimer;
  function toast(msg) {
    let t = $(".toast");
    if (!t) { t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); t.setAttribute("aria-live", "polite"); document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 3000);
  }
  async function copyText(text, msg) {
    try { await navigator.clipboard.writeText(text); }
    catch (e) { const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove(); }
    toast(msg || "Copied");
  }
  function downloadText(name, text) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 100);
    toast("Downloaded " + name);
  }
  async function api(path, opts) {
    const res = await fetch(path, opts && opts.body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(opts.body) } : undefined);
    const data = await res.json().catch(() => ({ error: "Unexpected response from the server." }));
    if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ").");
    return data;
  }
  // "21 Nov  20:37" in the visitor's local time, for the header detail line.
  const stamp = () => { const d = new Date(); return [d.toLocaleDateString("en-GB", { day: "numeric", month: "short" }), d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })]; };
  // Fills the header detail line: date, time, then any extra text, each in its own span.
  function meta(el, extra) { if (!el) return; el.innerHTML = [...stamp(), extra].filter(Boolean).map((x) => `<span>${esc(x)}</span>`).join(""); }
  const plural = (n, word, many) => `${n.toLocaleString("en-IN")} ${n === 1 ? word : (many || word + "s")}`;

  window.UI = { esc, icon, art, stamp, meta, icons, $, $$, router, header, toast, copyText, downloadText, api, plural };
})();
