# Cloudflare Worker setup

The existing `decktation` Worker serves the public site at
`https://decktation.com/`, exposes the CORS-capable Decky custom store at
`https://decktation.com/plugins.json`, and handles public download URLs.

Astro builds `site/` into static landing assets bundled with the Worker.
The Worker fetches the download list at `/downloads/`, branch/release pages,
metadata, and catalogs from the existing GitHub Pages origin. Stable ZIP URLs
redirect to GitHub Releases; branch ZIPs redirect to Pages. Pages retains at most
512 MiB of content, primarily branch previews, and removes release/PR ZIP copies.
PR ZIPs use Actions artifacts through the [download route](#pr-artifact-downloads).
The GitHub Pages custom-domain setting must remain empty to prevent redirects
back to the Worker. Cloudflare Pages is not required. See the complete
[domain setup and deployment order](DOMAIN_SETUP.md).

## Wrangler deployment

The account and custom domains are declared in `cloudflare/wrangler.jsonc`.
Wrangler creates the `decktation` Worker, DNS bindings, and managed certificates.
The active domains are `decktation.com` and `www.decktation.com`; the store is
served at `/plugins.json` on the root domain. workers.dev and preview URLs are
disabled because this deployment uses the custom domains directly.
Cloudflare manages the HTTPS certificates. The Worker permanently redirects
HTTP requests to HTTPS with status `308`, preserving the host, path, query,
and request method before serving assets or handling the catalog.

From the repository root:

```sh
npm ci --prefix site
npm ci --prefix cloudflare
cd cloudflare
npx wrangler login --device --browser=false
npm run deploy
```

Use Node 24 (Astro requires Node 22.12+). Wrangler's custom build runs the
Astro build and landing checks before uploading assets.

## Automatic deployment from GitHub

`.github/workflows/website.yml` checks website changes in pull requests and
publishes successful changes to `master` with the pinned Wrangler dependency.
It watches `site/`, `cloudflare/`, and its own workflow. Plugin-only changes do
not redeploy the website. Website-only changes skip the plugin build workflow.
Production deployments are serialized; pull requests and non-master manual
runs only validate and package the site.

Configure the repository secret `CLOUDFLARE_API_TOKEN` with a long-lived,
scoped Cloudflare API token. The interactive Wrangler OAuth login is local and
is not used by GitHub Actions. Create a custom token in
[Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens) with:

- Account → Workers Scripts → Edit, restricted to this Worker's account.
- Account → Account Settings → Read, restricted to the same account.
- Zone → Workers Routes → Edit, restricted to `decktation.com`.
- Zone → Zone → Read, restricted to `decktation.com`.

The account ID and custom domains are already declared in `wrangler.jsonc`;
no account-ID secret is required. Add the API token directly to GitHub, without
putting it in repository files or a shell command argument:

```sh
gh secret set CLOUDFLARE_API_TOKEN --repo silverfoxy/decktation
```

After adding the secret, run the workflow once to confirm deployment:

```sh
gh workflow run website.yml --repo silverfoxy/decktation --ref master
```

The check job runs without Cloudflare credentials and validates Worker routes,
localized pages, install links, and Wrangler packaging. The deploy job fails
with a setup message if the secret is missing and never publishes a PR build.
Use this workflow as the production deployment path; a separate Cloudflare
repository-build integration is not required.

Reference: [Cloudflare's GitHub Actions deployment guide](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/).

The older `homebrew.imsilverfoxy.com` hostname was left on its existing hosting;
it is not a binding on this new Worker. If migrating it later, add it explicitly
to Wrangler's custom-domain routes after checking its Cloudflare zone/account.

## Verification

Use `decktation.com` as `<worker-host>` below:

```sh
curl -i -X OPTIONS \
  -H 'Origin: https://steamloopback.host' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: X-Decky-Version' \
  https://<worker-host>/plugins.json

curl -i \
  -H 'Origin: https://steamloopback.host' \
  -H 'X-Decky-Version: test' \
  https://<worker-host>/plugins.json
```

The preflight must return `204` with all three `Access-Control-Allow-*`
headers. The GET must return `200`, the same CORS headers, and catalog JSON.
`/store/plugins.json` remains available as an alias with the same CORS behavior.
Both catalog and site routes support `HEAD`.

```sh
curl -fI https://<worker-host>/
curl -fI https://<worker-host>/es/
curl -fI https://<worker-host>/downloads/
curl -fI https://<worker-host>/latest.zip
curl -fIL https://<worker-host>/latest.zip
```

The homepage should return `200`; the ZIP should redirect to the original
GitHub Pages host and then return the download. Test a branch page and its
ZIP as well. A `502` for download pages or catalogs can indicate an unreachable origin
or a misconfigured GitHub Pages custom domain.

## PR artifact downloads

PR ZIPs remain in GitHub Actions (30-day retention). The trusted publisher checks
package structure, PR/head identity, raw ZIP SHA-256, artifact digest, source run,
size and expiration, then writes only metadata to Pages. Stable and branch
hosting are unchanged. The public PR URL redirects to a short-lived signed
GitHub blob URL, so download bytes, HEAD and Range requests go directly to GitHub.
The Worker never forwards its GitHub token to the blob host.

Create a **fine-grained personal access token**, restricted to
`silverfoxy/decktation`, with only **Actions: read** (and GitHub's mandatory
Metadata: read). Give it an expiration and rotate it before expiration. No
repository write permission, classic `repo` scope, or pull-request permission is
needed. Store it as a Worker **secret**, not a plaintext variable, repository
file, URL, or frontend setting:

```sh
cd cloudflare
npx wrangler secret put GITHUB_ARTIFACT_TOKEN
```

Enter the token at Wrangler's prompt; do not paste it into chat. Alternatively,
use the Worker's dashboard Settings → Variables and Secrets → Add → Secret.
The website deployment credential `CLOUDFLARE_API_TOKEN` is separate; the download
token does not need to be a GitHub Actions secret. Deploy the Worker with this
secret before merging the publisher change. During this deployment order, the
Worker continues to redirect catalog-pinned legacy PR packages to Pages until
the publisher replaces them with Actions-backed metadata. Until configured, PR downloads fail
closed with 503; stable downloads and the website keep working.

The Worker only resolves paths in the trusted testing catalog, verifies the
matching Pages metadata, and checks GitHub's artifact identity/digest before
requesting its download URL. Closed/moved PRs leave the catalog, expired builds
are omitted during the daily catalog refresh, and deleted/expired artifacts
return an unavailable response. A successful new build restores the listing.
Initial migration retires old Pages-hosted PR ZIPs; rerun each desired PR build
to publish Actions-backed metadata. Pages retains no PR ZIP copies.

Abuse is still possible: anonymous visitors can repeatedly download public
packages, consume Worker requests and GitHub API quota, or cause temporary
unavailability. Downloads allow 20 requests/minute per IP, and uncached GitHub
lookups allow 20/minute per Cloudflare location across all visitors. These are
approximate regional limits, **not a global spending cap**; distributed traffic
can exceed them. Public metadata caches for 60 seconds and signed links for 30
seconds. Signed links are bearer links usable by anyone holding them until
GitHub expires them; revoking catalog access is therefore not instantaneous.
Use Cloudflare traffic controls if abuse appears, and revoke the GitHub token to
disable the route. Never reuse a credential granting access to private projects.

References: [GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts),
[Worker secrets](https://developers.cloudflare.com/workers/configuration/secrets/),
[Worker rate limits](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).
