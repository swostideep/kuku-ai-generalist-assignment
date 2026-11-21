# Kuku AI Workspace design system

One Material Design 3 system shared by the three web apps: Promo Finder, Nyaya Sahayak and Continuity Checker. It is plain CSS and JavaScript, with no framework, build step or npm.

| File | What it is |
|---|---|
| [`design-system/m3.css`](design-system/m3.css) | Tokens and every shared component (about 330 lines) |
| [`design-system/ui.js`](design-system/ui.js) | Small helpers: icons, side sheet, focus trap, nav drawer, snackbar, copy, download, JSON fetch |

`design-system/` is the source of truth. Each app keeps a copy in its own `web/` folder, so each project still runs on its own. After changing the source, re-copy it:

```bash
for d in problem-1-promo-finder problem-2-nyaya-sahayak problem-3-continuity-checker; do cp design-system/m3.css design-system/ui.js $d/web/; done
```

## Principles

1. **One primary action per screen.** It is a filled button: "Analyse screenplay", "Run checks" or "Send". Once results exist, "View results" becomes the filled button and running again drops to an outlined button.
2. **Progressive disclosure.**
   - Lists show the decision-making fields only.
   - Detail lives in a side sheet, and the raw evidence (scores, screenplay lines, surrounding cues) sits behind a collapsed disclosure inside it.
   - Method explanations ("How promos are chosen") are collapsed by default.
3. **Plain language first, codes second.**
   - Findings lead with "Name spelled differently"; the rule code `NAME_DRIFT` is a quiet monospace column on desktop only.
   - Promo strength is shown as Strong / Solid / Weaker: the top, middle and bottom third of scores within the show. Raw scores are one click away.
4. **Nothing decorative that could be mistaken for data.** There are no charts, gradients or invented metrics. Every number on screen comes from the backend's output.
5. **Status is never colour alone.** Errors and warnings carry an icon and a word, and the first-wave promos carry a "First 10" label.

## Tokens

### Colour (M3 light scheme, seed indigo `#4355B9`)

| Role | Value | Used for |
|---|---|---|
| `--md-primary` / `--md-on-primary` | `#4355B9` / `#FFFFFF` | Filled buttons, links, active progress, focus ring |
| `--md-primary-container` | `#DEE0FF` | User chat bubbles, hook highlight, progress track |
| `--md-secondary-container` | `#E0E1F9` | Active nav item, selected chip, "info" status, suggested fix |
| `--md-tertiary` / `-container` | `#77536D` / `#FFD7F1` | Cliffhanger highlight (distinct from the hook) |
| `--md-error-container` / `on-` | `#FFDAD6` / `#410002` | Error status, error banner |
| `--md-warning-container` / `on-` | `#FFDF9E` / `#261A00` | Warning status (extension: M3 has no warning role) |
| `--md-success-container` / `on-` | `#C9EFD3` / `#00210D` | Success banner, "Strong" (extension) |
| `--md-surface` … `-container-highest` | `#FBF8FF` → `#E4E1E9` | Page, cards, sidebar, stats, input fills |
| `--md-on-surface` / `-variant` | `#1B1B21` / `#46464F` | Body text / secondary text |
| `--md-outline` / `-variant` | `#767680` / `#C6C5D0` | Field borders / dividers |

**Why indigo:**
- All three tools are about trust: a legal assistant, QA and editorial ranking.
- A calm, desaturated indigo reads as serious without the "alert" connotation of red or the "marketing" feel of saturated purple.
- Hook and cliffhanger need two clearly different highlight colours, which the indigo/mauve primary/tertiary pair gives.

**Contrast** (WCAG 2.2, computed from the token values):

| Pair | Ratio | Requirement |
|---|---|---|
| Body text on background | 16.3:1 | 4.5:1 |
| Secondary text on background | 8.9:1 | 4.5:1 |
| Secondary text on high container | 7.6:1 | 4.5:1 |
| Primary links / text buttons on background | 6.2:1 | 4.5:1 |
| White on primary (filled buttons) | 6.5:1 | 4.5:1 |
| Status badges (error / warning / success / info) | 13.3–13.7:1 | 4.5:1 |
| Field outline on background | 4.3:1 | 3:1 (non-text) |

### Typography (Roboto, Roboto Mono)

| Class | Size / line | Use |
|---|---|---|
| `.headline` | 28/36, 400 | Page title (one per view) |
| `.title-lg` | 22/28, 400 | Side-sheet title |
| `.title-md` | 16/24, 500 | Top-bar title, empty-state title |
| `.title-sm` | 14/20, 500 | Section labels, row titles |
| `.body-lg` | 16/24 | Page description, lead paragraph |
| `.body-md` | 14/20 | Default text |
| `.body-sm` | 12/16 | Hints, footnotes |
| `.label-lg` / `.label-md` | 14/20, 12/16, 500 | Buttons, chips, field labels |
| `.mono` | 13 px Roboto Mono | Timestamps, cue IDs, rule codes |

Fonts load from Google Fonts. Offline, the stack falls back to the system UI font, and the layout does not depend on the font metrics.

### Spacing, shape, elevation, motion

- **Spacing:** a 4 px grid, `--s1` 4 · `--s2` 8 · `--s3` 12 · `--s4` 16 · `--s5` 20 · `--s6` 24 · `--s8` 32 · `--s10` 40 · `--s12` 48.
- **Shape:**
  - `--r-xs` 4: fields.
  - `--r-sm` 8: chips and status badges.
  - `--r-md` 12: cards, quotes and banners.
  - `--r-lg` 16: side sheet and stats.
  - `--r-full`: buttons, nav items and search.
- **Elevation:** only for surfaces that float above the page: the side sheet, nav drawer and snackbar (`--e3`). Cards are flat with an outline, which keeps the page quiet.
- **Motion:** 200 ms, `cubic-bezier(.2,0,0,1)` (M3 "standard"). `prefers-reduced-motion` turns off all transitions and animations.

## Components

| Component | Class | Notes |
|---|---|---|
| App shell | `.app`, `.sidebar`, `.main`, `.page` | 232 px navigation sidebar on desktop. Below 840 px it becomes a modal drawer behind a top app bar (`.topbar`), with a scrim. Escape closes it |
| Nav item | `.nav-item` | `aria-current="page"` marks the active view. `aria-disabled` is set until results exist. `.count` shows the result count |
| Buttons | `.btn.filled / .tonal / .outlined / .text`, `.icon-btn` | 40 px tall. Icon buttons are 48 × 48. Disabled states lower contrast but keep the label |
| Text field / select / textarea | `.field`, `.input`, `.select`, `.textarea` | Visible `<label>`, hint text below, 2 px primary outline on focus |
| Search | `.search` | Pill field with a leading icon and a screen-reader label |
| Filter chip | `.chip[aria-pressed]` | Toggle state is exposed to assistive tech |
| Card | `.card` | Outlined, flat |
| Stats row | `.stats` > `.stat` | Up to 4 summary numbers. Wraps 2 × 2 on mobile |
| Table | `.table-wrap` > `.table` | Rows are focusable and open with Enter or Space. Below 760 px each row becomes a stacked card, using `td[data-label]` for the label |
| Status badge | `.status.error / warning / success / info / neutral` | Always icon or text plus colour |
| Banner | `.banner.error / warning / success / info` | Inline alert with an icon. Lives inside a `role="status"` live region |
| Progress | `.progress`, `.progress.determinate` | Indeterminate bar, or determinate with `role="progressbar"` and `aria-valuenow` |
| Empty state | `.empty` | Icon, title, one sentence, and one action (for example "Clear filters") |
| Side sheet | `.sheet` + `.scrim` | `role="dialog"`, `aria-modal`, focus moves in and is trapped. Escape or the scrim closes it and returns focus to the row that opened it. Full-screen on phones |
| Disclosure | `details.disclosure` | Native `<details>`, keyboard-operable without script |
| Transcript | `.transcript` > `.line` | Time, speaker, text. `.mark-hook` / `.mark-cliff` highlight lines and a legend explains the colours |
| Tabs | `.tabs` > `.tab[aria-selected]` | ARIA tabs with arrow-key navigation (Nyaya case panel) |
| Snackbar | `.snackbar` | Short confirmation ("Timestamps copied"), announced politely |
| Key–value list | `.kv` | Clip metadata, rate evidence |

## Accessibility checklist (WCAG 2.2 AA)

**Built into every app:**
- A skip link.
- Landmarks: `nav`, `main`, and `role="dialog"` for the sheet.
- One `h1` per view.
- Labels on every control.
- A visible 2 px focus ring.
- Live regions for progress and results.

**Target size (2.5.8):** every control is at least 24 × 24 px. This is checked automatically at four viewports by `tools/shots.py`, a Playwright script that sits outside this repository. Most targets are 40–48 px.

**Reflow (1.4.10):** no horizontal page scroll at 390 px wide, also checked automatically.

**Focus:**
- Not obscured (2.4.11): the sheet traps focus and returns it to the row that opened it.
- Order (2.4.3) follows the visual order.

**Not done:** testing with a real screen reader (VoiceOver or NVDA).

## Viewports

| Name | Size | Layout |
|---|---|---|
| Desktop | 1440 × 900 | Sidebar + content (max 1120 px); 560 px side sheet |
| Laptop | 1280 × 800 | Same; secondary table column hidden below 1100 px |
| Tablet | 768 × 1024 | Top app bar + drawer; table stays a table; sheet over content |
| Mobile | 390 × 844 | Drawer; table rows become cards; filters stack; sheet is full-screen |
