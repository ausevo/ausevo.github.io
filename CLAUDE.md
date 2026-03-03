# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About

Website for the **Australasian Evolution Society (AES)** at ausevo.github.io. Jekyll static site, custom theme (v2, `redesign` branch), deployed to GitHub Pages via Actions.

## Local Development

```bash
bundle install
bundle exec jekyll serve        # http://localhost:4000
bundle update github-pages      # update GH Pages gem
```

No tests. Work on the `redesign` branch; do **not** push directly to `master` until approved.

## Architecture (v2 Theme)

**No Bootstrap or jQuery.** The new theme uses custom CSS + vanilla JS only.

### Key files

| File | Role |
|------|------|
| `_config.yml` | Nav structure, conference season dates, GA4 ID, site metadata |
| `_data/conference.yml` | Current conference data driving homepage hero, stats, cards |
| `css/aes-theme.css` | **All** styles — CSS custom properties, layout, components |
| `js/site.js` | Nav toggle, hero rotation, countdown, GA4 tracking — no dependencies |
| `_layouts/base.html` | Root HTML shell (includes head, nav, footer, site.js) |
| `_layouts/home.html` | Homepage: conference-season logic, hero, stats, cards, social bar |
| `_layouts/page.html` | Standard content page with optional bigimg page-hero |
| `_layouts/post.html` | Blog post with header, pagination, optional Disqus |
| `_includes/head.html` | `<head>`: Inter font, Font Awesome 6, aes-theme.css, OG tags |
| `_includes/nav.html` | Accessible navbar driven by `site.navbar-links` in `_config.yml` |
| `_includes/footer.html` | Footer with social icons (Bluesky, X, Facebook, Email) |
| `_includes/google_analytics.html` | GA4 snippet — active only when `google_analytics_4` is set |

### Conference season toggle

The homepage switches between **conference season** (hero with registration CTAs, countdown) and **off-season** (society branding, upcoming conference banner) automatically:

1. Today is compared against `conference_season_start` / `conference_season_end` in `_config.yml`
2. Set `conference_season_override: true` to force season-mode on regardless of date
3. Set `conference_season_override: false` to force off
4. Leave the key absent to use the date range only

### CSS design tokens

All colours, sizes, and shadows are CSS custom properties on `:root` in `aes-theme.css`:
- `--c-navy` `--c-teal` `--c-coral` `--c-amber` — brand palette
- `--container` `--nav-h` `--radius` `--shadow-*` — layout

### Analytics tracking

Add `data-track="event-name"` to any element to fire a GA4 event on click.
Add `data-track-category="category"` for the event category (default: `"engagement"`).

Tracked events to wire up when GA4 ID is added:
- `registration` — Register buttons
- `programme-view` — Programme links/downloads
- `grants-visit` — ECR grants page links

## Content Pages

Root `.md` files rendered with `layout: page` by default. Key files:

| File | Purpose |
|------|---------|
| `index.md` | Homepage — uses `layout: home`, body is empty (layout generates all content) |
| `about.md` | Society overview (new) |
| `conference.md` | Current year conference overview (new) |
| `contact.md` | Exec committee list — **update annually** |
| `programme.md` | Current year program |
| `registration.md` | Current year registration |
| `2025_Venue.md` | Current year venue |
| `sponsors.md` | Conference sponsors |
| `2025_ECR_grants.md` | ECR travel grants |
| `2025_research_awards.md` | Research excellence awards |
| `past-conf.md` | Historical conference list |
| `previous_winners.md` | Past ECR award winners |
| `talk_awards.md` | Past talk award winners |
| `requestMins.md` | AGM minutes |
| `_mds/` | **Archive only** — past year pages, not served |

## Annual Conference Update Checklist

Each year:
1. **`_data/conference.yml`** — Update year, university, city, dates, registration/programme URLs, hero images
2. **`_config.yml`** — Update `conference_season_start/end`, update nav `Venue:` slug to new year
3. **`contact.md`** — New exec committee + year heading
4. **`programme.md`** — New program content
5. **`registration.md`** — New registration link, fee image, dates
6. Create `YYYY_Venue.md`, `YYYY_ECR_grants.md`, `YYYY_research_awards.md`
7. **`past-conf.md`** — Add completed conference to the list
8. Add PDFs to `docs/YYYY/`, images to `img/aesYYYY/`

## Page Front Matter

```yaml
---
layout: page           # or: home, post
title: "Page Title"
subtitle: Optional subtitle shown in hero
bigimg:
- /img/big-imgs/image.jpg: Caption text   # First image used as page hero bg
---
```

Social links are **all hardcoded** in `_includes/footer.html` and `_layouts/home.html` — the Bluesky URL is explicit, not driven by config. When social handles change, update those files directly.
