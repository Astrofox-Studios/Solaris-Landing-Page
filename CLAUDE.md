# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source .venv/bin/activate
python3 app.py          # starts on http://127.0.0.1:7060
```

There is no build step, test suite, or linter configured. The app runs directly from source.

## Architecture overview

**Backend:** Flask (`app.py`) — a single file that handles all routing, blog post loading, and template rendering. No database. No ORM. No blueprints. Everything is in one place by design.

**Templating:** Jinja2 via Flask. `templates/base.html` is the master layout — it loads global CSS, the header/footer partials, the Play Now modal, and `main.js`. Every page extends it via `{% extends "base.html" %}` and uses `{% block extra_css %}` / `{% block extra_js %}` to load page-specific assets.

**Frontend:** Vanilla JS and CSS only — no framework, no bundler, no TypeScript. CSS variables (defined in `main.css`) drive the entire design system. JS files are standalone per-feature modules loaded at the bottom of the page.

## Routes

| Route | Template | Notes |
|---|---|---|
| `/` | `index.html` | Main landing page, receives `posts` (latest 5 blog posts) |
| `/beta` | `beta.html` | Beta signup showcase page |
| `/blog` | `blog/listing.html` | Full post listing |
| `/blog/<slug>` | `blog/post.html` | Single post; receives `post` with related/recommended posts |
| `/roadmap` | `roadmap.html` | Static roadmap page |
| `/about` | `about.html` | Static about page |
| `/media` | `media.html` | Static media/gallery page |
| `/coming-soon` | `coming-soon.html` | Placeholder for unbuilt features |

## Blog system

Posts live in `content/blog/` as Markdown files with YAML frontmatter. Required frontmatter fields: `title`, `date`, `author`, `summary`, `tags` (list), `thumbnail`, `header_image`. Posts with `date < 2026-01-01` are flagged `is_outdated: true` in the template context.

The `[image:path]` syntax in post Markdown is converted to `<figure><img></figure>` by `process_image_tags()` before markdown rendering.

Related posts are derived by shared tags at render time — no separate data store.

## CSS architecture

All CSS variables (colours, spacing, typography, shadows, transitions, border radii) are defined in `static/css/main.css` under `:root` and `[data-theme="light"]`. Every other CSS file consumes them via `var(--...)`.

Each page or section has its own dedicated CSS file (e.g. `hero.css`, `team.css`, `beta.css`) and is loaded only on the pages that need it via `{% block extra_css %}`. `responsive.css` and `footer.css` are always loaded globally via `base.html`.

**Colour palette:**
- Primary: `#325ad3` (blue)
- Secondary: `#6929b7` (purple)
- Accent warm: `#f59e0b`, Accent green: `#10b981`
- Backgrounds: `#121218` / `#1a1a24` / `#1e1e2c` (dark theme)

**Typography:** `Paytone One` (headings, via Google Fonts) and `Nunito` (body). Both imported in `main.css`.

## JavaScript modules

Each JS file is a self-contained feature, no imports/exports:

| File | Responsibility |
|---|---|
| `main.js` | Theme toggle (persisted in `localStorage`), sticky header (`.scrolled` class), hamburger/mobile nav, `.fade-in` scroll reveal via `IntersectionObserver` |
| `beta.js` | Canvas particle system for the beta hero, beta form submit handling, `.fade-in` scroll reveal (mirrors `main.js` pattern) |
| `news-carousel.js` | Blog post carousel on the homepage with fade transitions and random-shape dot indicators |
| `play-modal.js` | "Play Now" modal — open/close and server IP copy to clipboard |
| `lightbox.js` | Image lightbox on the homepage gallery |
| `team.js` | Team member card carousel |
| `season-carousel.js` | Season preview carousel (currently hidden) |
| `gallery.js` | Media page gallery |
| `copy-ip.js` | Standalone IP copy for anywhere outside the modal |

## Scroll animations

Any element with class `fade-in` is animated in by `IntersectionObserver` adding `visible` when the element enters the viewport. The `.fade-in` / `.fade-in.visible` transition is defined in `main.css`. `main.js` handles this globally; `beta.js` runs its own instance for the beta page since `main.js`'s observer fires before beta-specific elements exist.

## Design conventions

- Buttons: `.btn` base + `.btn-primary` / `.btn-secondary` / `.btn-outline`. Primary uses a blue gradient with a glow and `translateY(-3px)` lift on hover.
- Cards use `var(--bg-card)` background, `2px solid var(--border-color)` border, `var(--border-radius)` (20px) or `var(--border-radius-lg)` (28px).
- Wave SVG dividers between sections use `fill="var(--bg-primary)"` or the section's background colour to blend seamlessly.
- Section wrappers use `<div class="section-container">` which provides `max-width: var(--max-width)` (1200px) and horizontal padding.
- The header morphs from transparent to a pill shape on scroll via the `.scrolled` class toggled in `main.js`.

## Signup / forms

All forms are currently client-side only. The beta form in `beta.js` and the old homepage signup in `main.js` both have `// TODO: Hook up to a real backend / mailing list API` — they show a success state without sending any data.

## Static assets

- `static/images/media/` — server screenshots (1–8.png) used in the homepage gallery and hero background (`1.png`)
- `static/images/media/` — team character renders (`cookie.png`, `skye.png`) and cosmetics banner (`cosmetics.png`)
- `static/images/icons/` — minigame icons for the season carousel

## Company context

Solaris is a Minecraft Java Edition minigame server operated by **Astrofox Studios Ltd** (London). The server address is `playsolaris.net`. Supported versions: 1.21.4, 1.21.5, and 1.26.1 (when released). All social links and Store/Forms/Wiki nav items currently point to `/coming-soon` or `#` placeholders.
