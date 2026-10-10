# Decktation product landing

Astro builds the English `/` and Spanish `/es/` landing pages into `dist/`.
The existing Cloudflare Worker serves those static assets and handles the
custom store and downloads. No Astro server adapter is needed.

```sh
npm ci --prefix site
npm --prefix site run build
npm --prefix site test
npm --prefix site run dev
```

Use Node 24 (minimum 22.12). `src/components/Landing.astro` contains the shared
page, `src/layouts/Page.astro` its metadata and document shell, and
`src/i18n/*.json` the complete translations. Styles, browser behavior, images,
and locally vendored Font Awesome assets live in `public/`.
`SITE_BASE_URL` configures canonical, social, and sitemap URLs and defaults
to `https://decktation.com`. The custom Worker handles `/downloads/`,
`/latest.zip`, release and branch URLs, and `/plugins.json` in production;
Astro's development server only previews the landing pages and their assets.
See [domain and deployment setup](../doc/DOMAIN_SETUP.md).
GitHub Actions validates pull requests and deploys website changes pushed to
`master`; see [deployment credentials](../doc/CLOUDFLARE_WORKER.md#automatic-deployment-from-github).

Browser language detection, a saved language preference, light/dark themes,
installation guidance, FAQ toggles, copy-install-URL, and animated game demos
are retained from the contributed page. Animations stop offscreen and in
background tabs; reduced motion displays completed examples.

## Attribution

Imported from [nukeador's landing contribution in issue #60](https://github.com/silverfoxy/decktation/issues/60),
branch [`codex/landing-first-implementation`](https://github.com/nukeador/decktation/tree/codex/landing-first-implementation),
commit `0b9af13e2386928e1579bfe81c55dabe22e582be`, and migrated to Astro.
The contribution's rendered public media are included; its raw compositing
inputs and Python generator are available in that source branch.

Hero and WoW chat visuals are illustrative/edited demos, labeled on the page.
The WoW example uses GameStar's Forever beta gameplay with edited native chat:
- [Gameplay gallery](https://www.gamestar.de/galerien/world_of_warcraft_forever,137281.html)
- [Original screenshot](https://images.cgames.de/images/gamestar/287/world-of-warcraft-forever_6441900.jpg)

Additional retained media and game marks come from:
- [Valve Steam Deck render](https://cdn.fastly.steamstatic.com/steamdeck/images/overview_steamDeck_heroCrop.png)
- [PC Gamer gameplay source](https://www.pcgamer.com/games/world-of-warcraft/world-of-warcraft-the-war-within-review/)
- [Blizzard UI/HUD article](https://news.blizzard.com/en-us/article/23837944/get-into-the-grid-of-things-with-the-updated-ui-and-hud)
- [World of Warcraft logo](https://blz-contentstack-images.akamaized.net/v3/assets/bltf408a0557f4e4998/bltb7c1db49cad77069/60a81b45b078b00d8a909fce/world-of-warcraft.svg)
- [Guild Wars 2 logo](https://guildwars2.staticwars.com/wp-content/themes/guildwars2.com-live/img/gw2-logotype.723cc563.svg)

Font Awesome Free 6.7.2 is vendored locally with its
[license](public/vendor/fontawesome/LICENSE.txt). No CDN or analytics are used.
`public/assets/og-image.png` is the contributed English social-preview capture.
Regenerate it when the hero's appearance changes materially.
