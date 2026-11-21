/* Kuku AI Workspace: small shared UI helpers (no dependencies). Copied identically into each app's web folder. */
(function () {
  const P = {
    menu: "M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z",
    close: "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    search: "M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
    send: "M2.01 21 23 12 2.01 3 2 10l15 2-15 2z",
    mic: "M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z",
    error: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
    warning: "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    info: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z",
    check: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
    copy: "M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z",
    download: "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    add: "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z",
    play: "M8 5v14l11-7z",
    chevron: "M10 6 8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z",
    back: "M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z",
    movie: "M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z",
    list: "M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z",
    checklist: "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-9 14-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
    scale: "M12 3c-1.27 0-2.4.8-2.82 2H3v2h1.95L2 14c-.47 2 1 3 3.5 3s4.06-1 3.5-3L6.05 7h3.12c.33.85.98 1.5 1.83 1.83V20H2v2h20v-2h-9V8.82c.85-.32 1.5-.97 1.82-1.82h3.13L15 14c-.47 2 1 3 3.5 3s4.06-1 3.5-3l-2.95-7H21V5h-6.17C14.4 3.8 13.27 3 12 3zM4.25 14l1.25-3 1.25 3h-2.5zm13 0 1.25-3 1.25 3h-2.5z",
    doc: "M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
    shield: "M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z",
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (name, label) =>
    `<svg viewBox="0 0 24 24" fill="currentColor" ${label ? `role="img" aria-label="${esc(label)}"` : 'aria-hidden="true"'}><path d="${P[name]}"/></svg>`;

  // Side sheet / drawer with Escape, scrim click, focus move-in and focus return.
  let lastTrigger = null;
  function openSheet(sheet, scrim, trigger) {
    lastTrigger = trigger || document.activeElement;
    sheet.classList.add("open"); sheet.removeAttribute("inert"); sheet.setAttribute("aria-hidden", "false");
    scrim && scrim.classList.add("show");
    const f = sheet.querySelector("[data-autofocus], button, a[href], input, select, textarea");
    setTimeout(() => f && f.focus(), 50);
  }
  function closeSheet(sheet, scrim) {
    sheet.classList.remove("open"); sheet.setAttribute("inert", ""); sheet.setAttribute("aria-hidden", "true");
    scrim && scrim.classList.remove("show");
    if (lastTrigger && document.contains(lastTrigger)) lastTrigger.focus();
  }
  function trapTab(sheet, e) {
    if (e.key !== "Tab" || !sheet.classList.contains("open")) return;
    const items = [...sheet.querySelectorAll("button, a[href], input, select, textarea, summary, [tabindex='0']")].filter((x) => x.offsetParent);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
    else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
  }

  // Mobile navigation drawer
  function wireNav(app) {
    const side = app.querySelector(".sidebar"), btn = app.querySelector("[data-nav-toggle]"), scrim = document.querySelector("[data-nav-scrim]");
    if (!side || !btn) return;
    const close = () => { side.classList.remove("open"); scrim && scrim.classList.remove("show"); btn.setAttribute("aria-expanded", "false"); };
    btn.addEventListener("click", () => { const o = !side.classList.contains("open"); side.classList.toggle("open", o); scrim && scrim.classList.toggle("show", o); btn.setAttribute("aria-expanded", String(o)); if (o) side.querySelector("a, button").focus(); });
    scrim && scrim.addEventListener("click", close);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && side.classList.contains("open")) { close(); btn.focus(); } });
    side.addEventListener("click", (e) => { if (e.target.closest(".nav-item") && window.innerWidth <= 840) close(); });
  }

  let snackTimer;
  function snackbar(msg) {
    let s = document.querySelector(".snackbar");
    if (!s) { s = document.createElement("div"); s.className = "snackbar"; s.setAttribute("role", "status"); s.setAttribute("aria-live", "polite"); document.body.appendChild(s); }
    s.textContent = msg; s.classList.add("show"); clearTimeout(snackTimer); snackTimer = setTimeout(() => s.classList.remove("show"), 3200);
  }
  async function copyText(text, msg) {
    try { await navigator.clipboard.writeText(text); snackbar(msg || "Copied"); }
    catch (e) { const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove(); snackbar(msg || "Copied"); }
  }
  function downloadText(name, text) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 100);
    snackbar("Downloaded " + name);
  }
  async function api(path, opts) {
    const res = await fetch(path, opts && opts.body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(opts.body) } : undefined);
    const data = await res.json().catch(() => ({ error: "Unexpected response from the server." }));
    if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ").");
    return data;
  }
  window.UI = { esc, icon, openSheet, closeSheet, trapTab, wireNav, snackbar, copyText, downloadText, api };
})();
