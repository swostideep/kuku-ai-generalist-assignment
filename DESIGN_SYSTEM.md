# Plain: the design system behind the three sites

Promo Finder, Nyaya Sahayak and the Continuity Checker share one small design system. It is plain CSS and JavaScript,
with no framework and no build step.

| File | What it is |
|---|---|
| [`design-system/base.css`](design-system/base.css) | Tokens, layout, and every shared component |
| [`design-system/kit.js`](design-system/kit.js) | Stroke icons and line drawings, a hash router, the header menu, toast, copy and download, a JSON fetch helper |

`design-system/` is the source. Each app keeps a copy in its own `web/` folder so each project still runs on its own;
after changing the source, copy it across:

```bash
for d in problem-1-promo-finder problem-2-nyaya-sahayak problem-3-continuity-checker; do cp design-system/base.css design-system/kit.js $d/web/; done
```

## Direction

The look is monochrome and quiet, like a well-made portfolio or a good money app: white paper, near-black ink, greys,
and a lot of space. Two references shaped it. One showed light, large type, small left-aligned section titles,
numbered cards with line drawings, and a dotted grey "stage" holding a white card. The other showed pill buttons and a
hero card built around one big live number.

Rules I held to:

1. **One colour per site, used sparingly.** Each site has its own accent, chosen for what it does: warm orange for
   Promo Finder (attention, entertainment), deep green for Nyaya Sahayak (money recovered, trust) and deep blue for
   the Continuity Checker (an editor's accuracy tool). It appears in the logo mark, main buttons, the second half of
   the headline, the current-page underline, card drawings, progress bars and one solid statement block. Everything
   else is white and grey; red and amber are kept for errors and warnings.
2. **One big number per home page.** Each site opens with the figure that matters: promos ready to review, or errors
   to fix. The rest of the page explains it.
3. **Real pages, real addresses.** Every list item has its own URL (`#/promos/12`, `#/findings/3`), so the back button
   works and a link can be shared.
4. **Plain words first.** “Name spelled differently” leads, and the rule code `NAME_DRIFT` appears only on the Checks
   page.
5. **Nothing invented.** Every number comes from the tool's own output.

## Tokens

### Colour

Shared neutrals and status colours live in `base.css`. Each site sets its own accent at the top of its `app.css`:

| Site | `--accent` | Text on white | Statement block | White on accent |
|---|---|---|---|---|
| Promo Finder | `#b8430f` orange | `#b03d0c`, 6.0:1 | `#8f350c` | 5.5:1 |
| Nyaya Sahayak | `#004437` green | `#0f6a52`, 6.5:1 | `#004437` | 11.2:1 |
| Continuity Checker | `#163f7a` blue | `#1f4f94`, 8.1:1 | `#102a52` | 10.4:1 |


| Token | Light | Dark | Used for |
|---|---|---|---|
| `--bg` | `#ffffff` | `#0e0e0e` | Page and cards |
| `--soft` | `#f3f4f6` | `#1a1a1a` | Segmented controls, tags, notes |
| `--stage` | `#ebebe9` | `#161616` | Showcase panels (with a dot grid) |
| `--line` | `#ececec` | `#232323` | Card borders and dividers |
| `--control` | `#8a8f96` | `#6a6e75` | Borders of inputs and outlined buttons |
| `--ink` | `#111111` | `#f2f2f2` | Text, primary buttons |
| `--ink-2` | `#5f6570` | `#a3a7ae` | Secondary text |
| `--ink-3` | `#8a8f98` | `#80858d` | Large display text only (the grey half of a headline) |
| `--red` / `--red-soft` | `#b3261e` / `#fbeceb` | `#f1958d` / `#2c1615` | Errors |
| `--amber` / `--amber-soft` | `#8a5a00` / `#fbf1df` | `#e5b35f` / `#2a2213` | Warnings, blanks in a notice |
| `--green` / `--green-soft` | `#1f6f4a` / `#e8f2ec` | `#7fcfa4` / `#142319` | Proof the user has, official sources |
| `--mark-hook` / `--mark-cliff` | `#e7efe9` / `#f6ecd9` | `#18271e` / `#2a2214` | Opening and closing lines in a script |

Dark mode follows the operating system.

**Contrast** (WCAG 2.2, computed from the token values):

| Pair | Ratio | Requirement |
|---|---|---|
| Body text on white | 18.9:1 | 4.5:1 |
| Secondary text on white / on fills / on the stage | 5.9 / 5.3 / 4.9:1 | 4.5:1 |
| Grey half of headlines (64 px) | 3.3:1 | 3:1 for large text |
| Error, warning and success badges | 5.3 to 5.7:1 | 4.5:1 |
| Input and button borders | 3.3:1 | 3:1 for controls |

### Type

One typeface: **Geist**, loaded from Google Fonts (the system sans-serif is used offline). Large sizes are set light,
which gives the calm, editorial feel; small text stays at regular weight so it remains easy to read.

| Class | Size and weight | Use |
|---|---|---|
| `.display` | 64 px, 300 | Home page headline (38 px on phones) |
| `.h1` | 48 px, 300 | Page titles |
| `.h2` | 28 px, 400 | Showcase headlines |
| `.title` | 24 px, 500 | Section titles, left aligned |
| `.h3` | 20 px, 400 | Card titles, quotes |
| `.lead` | 20 px, 300 | Introductions |
| body | 15 px, 400 | Everything else |
| `.kicker` | 13 px, spaced capitals | Small labels such as SCORES |
| `.figure` | 72 px, 300, tabular | The big number |

### Space and shape

- **Spacing:** a 4-pixel scale (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128). Sections are 96 px apart.
- **Page width:** 1,328 px, with 56 px side margins on desktop, 24 px on tablets and 16 px on phones.
- **Radii:** 12–14 px for fields and cards, 20 px for stages. Buttons, search fields and segmented controls are pills.
- **Elevation:** one soft shadow, used only for the white card on a stage and for menus. Everything else is flat, with
  hairline borders.
- **Motion:** 160 ms with a gentle ease, and a short rise as the hero appears. All of it switches off when the
  visitor asks for reduced motion.

## Components

| Component | Class | Notes |
|---|---|---|
| Header | `.site-header`, `.ident`, `.nav` | Name with a live date, time and context line on the left; text links on the right, with a thin underline for the current page. On phones, a menu button opens a small panel. |
| Hero | `.hero` | Headline with a grey second half, a lead, one primary button and one text link; the live card on the right. |
| Stage and live card | `.stage`, `.live` | Dotted grey panel with a white card: the big number, a one-line explanation, a thin meter, a short list and the actions. |
| Numbered cards | `.cards`, `.card` | 001, a line drawing, a title, one bold line and a short grey description. |
| Showcase | `.showcase` | A principle on the left, a white card of facts (`.spec`) on the right. |
| Buttons | `.btn.primary / .secondary / .ghost`, `.icon-btn`, `.text-link` | Black pill for the main action; outlined pill for the second; underlined text link for a third. |
| Fields | `.field`, `.input`, `.select`, `.textarea`, `.search` | Visible labels, a 3:1 border, and a black border with a soft ring on focus. |
| Segmented control | `.segmented` | Few-option filters such as All, Errors, Warnings, with counts. |
| Stats | `.stats` | Four figures divided by hairlines; two by two on phones. |
| Rows | `.rows`, `.row` | The main list: a large number, a title, grey details and a badge. The whole row is a link. |
| Badges and tags | `.badge`, `.tag` | Dot plus word; never colour alone. |
| Notes | `.note` | Soft fill with an icon, for warnings, errors and tips. |
| Quotes and transcript | `.quote`, `.transcript`, `.line` | Script lines with time, speaker and highlight. |
| Tabs | `.tabs`, `.tab` | Pill tabs with arrow-key navigation (Nyaya's case panel). |
| Toast | `.toast` | Short confirmations such as “Timestamps copied”. |
| Footer | `.site-footer` | A large underlined link, small links, and one line of fine print. |

## Accessibility (WCAG 2.2 AA)

- A skip link, landmarks, one `h1` per page, and visible labels on every control.
- Moving between pages puts focus on the new heading and updates the page title.
- A visible 2 px focus outline everywhere.
- Every control is at least 24 × 24 px; most are 36–46 px. This is checked automatically at four screen sizes.
- No sideways scrolling at 390 px wide, also checked automatically.
- Status is always a word plus colour. Reduced motion is respected.
- Not done: testing with a real screen reader.

## Screen sizes

| Name | Size | Layout |
|---|---|---|
| Desktop | 1440 × 900 | Two-column hero, four cards in a row, chat beside the case panel |
| Laptop | 1280 × 800 | Same |
| Tablet | 768 × 1024 | Hero stacks, two cards per row, filters wrap, the case panel moves behind a switch |
| Phone | 390 × 844 | Menu button, one card per row, list rows stack, full-width filters |
