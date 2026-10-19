# decktation.com hosting

Use the existing **Cloudflare Worker** as the public entry point for the
Astro product landing, custom store, and download URLs. **Cloudflare Pages is not needed.**
Keep the existing GitHub Pages deployment as the origin for generated pages,
catalogs, and a bounded set of branch ZIP files. Stable ZIPs live in GitHub Releases.

| Purpose | Public URL | Worker behavior |
| --- | --- | --- |
| Product landing (English / Spanish) | `https://decktation.com/` and `/es/` | Serve Astro static assets |
| Release / test-build list | `https://decktation.com/downloads/` | Fetch generated download index from GitHub Pages |
| Latest stable plugin ZIP | `https://decktation.com/Decktation.zip` | Redirect download to GitHub Releases |
| Custom Decky store | `https://decktation.com/plugins.json` | Fetch catalog and add Decky's CORS headers |
| Branch / versioned builds | `https://decktation.com/branches/…` and `/releases/…` | Fetch pages and metadata; redirect ZIPs to their artifact host |

The landing page links to both the ZIP and custom store, and to the full
download list. It builds from `site/` using Astro; the Worker bundles that
small static output alongside its catalog/download routing. The older `homebrew.imsilverfoxy.com/plugins.json` endpoint was left on its
existing hosting. The new custom-store endpoint uses `/plugins.json` on the
root domain.

ZIP requests receive temporary redirects, so clients download the files
directly from the original artifact host. Workers static assets have a
[25 MiB per-file limit](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/),
which the plugin ZIP exceeds. Stable aliases (`/Decktation.zip`, `/latest.zip`, and `/releases/latest/…`)
redirect to GitHub's latest `Decktation.zip` release asset. Versioned release downloads redirect
to that tag's asset. Release metadata and the store catalog also use GitHub URLs,
which the built-in updater already accepts. The catalog uses the lowercase
`decktation.zip` URL for compatibility with already-installed updaters. GitHub
resolves that URL to the same `Decktation.zip` asset; public links and the saved
filename retain the capital D. Release ZIPs are removed from Pages.

Branch previews retain one `Decktation.zip` per branch. The Worker maps legacy
lowercase branch filenames to it. Publishing retains at most 512 MiB of branch
files, keeping master and the current branch, then the newest previews by metadata
timestamp. Older previews expire and disappear from the generated download index.
Rebuild an expired branch to restore its preview. Git history may retain old ZIP
blobs; only the current checkout is uploaded to Pages.

## Configure and deploy

1. Ensure `decktation.com` is an active DNS zone in the same Cloudflare account
   as the existing `decktation` Worker.
2. In GitHub → `silverfoxy/decktation` → **Settings → Pages**, keep the source
   set to **GitHub Actions** and **leave Custom domain empty**. The origin must
   remain `https://silverfoxy.github.io/decktation`. Assigning `decktation.com`
   to GitHub Pages would redirect requests back to the Worker and break the
   origin fetches and ZIP downloads. Do not add a `CNAME` file to `gh-pages`.
3. Install the landing dependencies and deploy using the commands in
   [Worker setup](CLOUDFLARE_WORKER.md#wrangler-deployment). The initial
   deployment uses Wrangler; GitHub Actions handles subsequent deployments.
4. Wrangler applies the custom-domain routes declared in `wrangler.jsonc`:
   `decktation.com` and `www.decktation.com`. Cloudflare creates their DNS
   records and HTTPS certificates. Leave the older homebrew hostname on its
   existing hosting. No new homebrew subdomain is required.
5. In GitHub → **Settings → Secrets and variables → Actions → Variables**,
   set `DECKTATION_PAGES_BASE_URL` to `https://decktation.com`.
   Despite its name, this is the **public URL**, not the upstream hostname.
   The workflow uses it for generated page links, catalog artifact URLs, and
   build summaries. Without it, links use the repository's GitHub Pages URL,
   including in forks.
6. Run the build workflow on `master` to refresh the download index, branch links,
   and custom-store catalog. Future tagged releases publish stable download
   links with the same public base URL. Historical release pages and metadata
   are migrated to GitHub Release asset links during publishing.

Deployment completed on 2026-10-10 using Wrangler and the Cloudflare API.
Both domain bindings were verified, the Astro landing and catalog returned
`200`, Decky preflight returned `204`, and the ZIP redirect reached a packaged
download. The GitHub Actions public-URL variable is configured. Editing the
repository now deploys website changes on pushes to `master` through
`.github/workflows/website.yml` after the `CLOUDFLARE_API_TOKEN` secret is set.

## Verify after deployment

```sh
curl -fI https://decktation.com/
curl -fI https://decktation.com/es/
curl -fI https://decktation.com/downloads/
curl -fI https://decktation.com/Decktation.zip
curl -fIL https://decktation.com/Decktation.zip
curl -fI https://github.com/silverfoxy/decktation/releases/latest/download/decktation.zip
curl -fi https://decktation.com/plugins.json
curl -fi https://homebrew.imsilverfoxy.com/plugins.json
```

The ZIP's first response should be `302` with a `Location` under
`https://github.com/silverfoxy/decktation/releases/`; following it should reach a ZIP
response. The original GitHub Pages URL must not redirect to `decktation.com`.
Run the [Worker CORS checks](CLOUDFLARE_WORKER.md#verification) as well.
Confirm a packaged ZIP installs through Decky's **Install Plugin from URL**
and that the Custom Store loads in Decky.

Reference: [Cloudflare Worker custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/).
