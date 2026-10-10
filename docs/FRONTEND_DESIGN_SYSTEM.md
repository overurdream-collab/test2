# MCIAS enterprise interface design system

The local enterprise workspace retains the repository’s same-origin FastAPI +
vanilla ES module architecture. It does not introduce a second application,
bundler, CDN or browser-side financial engine. Modules are separated into
`app.js` (shell/session/routes), `api.js` (typed JSDoc contracts and transport),
`ui.js` (reusable components), `views.js` (feature workspaces), `routes.json`
(bilingual coverage registry), `workspace.css` (tokens/themes/responsiveness).

## Visual tokens

| Purpose | Light direction | Dark direction |
|---|---|---|
| Executive navy / hero | `#102A43` | Same navy hero, `#BFD8EE` foreground |
| Primary action blue | `#2563EB` | `#82ACFF` text; solid blue primary buttons |
| Healthcare teal / charts | `#0D9488` | `#66D7C7` |
| Accessible small teal text | `#08756C` | `#66D7C7` |
| Sky / focus indicator | `#38BDF8` | `#38BDF8` |
| Background / surface | `#F5F8FC` / white | `#0C1524` / `#132136` |
| Body / secondary text | `#172B4D` / `#52647B` | `#E5EDF8` / `#A7B7CC` |
| Success / warning / critical text | `#13773B` / `#985800` / `#B91C1C` | `#72DBA0` / `#F7BD64` / `#FF9B9B` |
| AI accent | `#7C3AED` | `#BC99FF` |

Semantic colors do not imply accepted gates or approved financial outcomes.
Status always includes text. Small teal, warning and success labels use darker
light-theme values to satisfy contrast; raw chart/icon materials retain the
requested creative colors. Glass effects are restrained to modal backdrops;
primary cards use opaque readable surfaces.

## Typography and layout

IBM Plex Sans Arabic and Inter are self-hosted WOFF2, with their SIL Open Font
Licenses included in the package. Arabic defaults to RTL and the right sidebar;
English uses LTR and the left sidebar. Logical CSS properties handle boundaries,
spacing and alignment. Financial values and identifiers use isolated LTR text;
amounts remain backend Decimal strings and are not reformatted or rounded.

Page title 30px (25px mobile), section 20px, card 16–17px, body 14px, dense tables
12–13px, KPI 30px. Cards use an 18px radius, subtle navy shadow, 18px grid gaps and
22px inner spacing. Main workspace padding is 32px desktop / 15px mobile.

Desktop uses a 258px collapsible sidebar; tablet uses a compact 218px sidebar and
two-column metrics; mobile at 760px uses an inert closed drawer, focused open/close
controls and keyboard focus containment. Tables scroll inside their own named
regions; the application viewport does not scroll horizontally.

## Components and interactions

- Application shell, sidebar, topbar, breadcrumb, module search, current-institution
  display, effective profile, language/theme controls and sign-out.
- Page header, semantic badges, scope selector, KPI, chart, accessible record table,
  filters, pagination, backend evidence panel, eight-agent finding cards,
  governance timeline and governed task/policy forms.
- Loading skeletons, empty/error/unauthorized/unavailable states, success feedback,
  native form validation, destructive/consequential confirmation and accessible
  evidence dialogs. No empty-state button claims an unavailable backend action.
- Server-backed pagination and explicit loaded-page sorting/filtering. Excel/PDF
  are authenticated server downloads. No arbitrary protected-table export.
- Currency-separated financial bars, review counts, grouped summaries and recorded
  monthly plots. Focusable points/bars expose exact backend values and evidence
  drill-down. Visualization geometry uses approximate JavaScript ratios only;
  payable, deductions and decision amounts never come from JavaScript arithmetic.

## Icon assets

13 handcrafted transparent SVG assets cover dashboard, claims, beneficiaries,
hospitals, laboratories, pharmacies, audit, intelligence, reports, security,
ingestion, policy and settings. Each uses the same upper-left light, blue/teal
materials, soft shadow and offset depth; violet is confined to intelligence.
They are resolution independent, lightweight and do not require WebGL. Dense
controls use a small consistent stroked SVG family. No emojis are used.

## Accessibility and localization

Skip link, landmarks, explicit labels, named table regions/captions, sortable
header semantics, native buttons, focus rings, live feedback, native dialogs,
Escape handling, reduced-motion support and keyboard-operable chart evidence.
Arabic/English navigation, forms, status descriptions and state messages are
localized. Immutable backend reason codes and evidence text remain preserved as
returned, with localized headings; the frontend does not rewrite evidence.
Automated WCAG 2 A/AA and 2.1 AA checks complement keyboard/layout E2E tests;
manual assistive-technology and institutional usability review remain necessary.
