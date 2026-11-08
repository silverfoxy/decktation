# Installation guide

For the recommended install walkthrough, start with the [README](../README.md#install-decktation). This page covers the built-in updater, manual installation, alternative packaged builds, and notes for developers.

## Install a stable release

Use a packaged plugin ZIP, which includes the runtime dependencies required by Decktation:

- [Recommended short URL](https://decktation.com/Decktation.zip)
- [Full stable URL](https://decktation.com/releases/latest/Decktation.zip)
- [GitHub release asset](https://github.com/silverfoxy/decktation/releases/latest/download/Decktation.zip)

In Decky Settings, choose **Install Plugin from URL** and paste the short URL above, or download the ZIP and choose **Install Plugin from ZIP**. Enable developer options if those actions are not shown. Decky imports the archive and reloads the plugin. Decktation's built-in updater handles future stable releases independently of the selected store catalog.

Do not use GitHub’s automatically generated **Source code (zip)** or **Source code (tar.gz)** archives. They are not installable Decktation packages and do not contain the bundled dependencies. Do not extract the packaged plugin ZIP or copy its contents into Decky’s plugin directory.

## Updating Decktation

Decktation automatically checks for newer stable releases when you open the plugin. It does not install an update until you choose it and confirm Decky's installation prompt.

1. Open the update notice in Decktation, or choose **Advanced settings → Check for updates**.
2. Finish any recording, transcription, or pending draft, then select **Update to [version]**.
3. Confirm Decky's installation prompt and reopen Decktation after it reloads.

The updater checks the package before handing it to Decky's installer. Saved settings and downloaded Whisper models are preserved. It offers stable releases; use the testing catalog or direct packaged builds below to install a specific PR build.

### Manual update fallback

For an older installation without the updater, or if Decky's in-plugin installer is unavailable:

1. Install the [latest packaged ZIP](https://decktation.com/Decktation.zip) with **Install Plugin from URL**, or download it and use **Install Plugin from ZIP**.
2. Reopen Decktation.

Keep the filename `Decktation.zip` so Decky recognizes the existing plugin and unloads its code before extracting the new build. Leave Decktation settings and downloaded Whisper model files alone; deleting them is not part of a normal update.

## Branch builds

For repeated Deck testing, configure the [opt-in testing catalog](TESTING_STORE.md) once at `https://decktation.com/testing/plugins.json`. It lists successful builds of **open PRs, including forks, without approval**; select a PR version deliberately. The direct branch ZIP URLs below remain useful for one-off installs. A PR listed in the testing store has **not** been reviewed for safety.

When GitHub Pages is enabled for a repository, branch packages use this URL pattern:

```text
https://<owner>.github.io/decktation/branches/<branch-slug>/Decktation.zip
```

Branch names use readable ASCII slugs. For example, `feat/haptic-feedback` uses `feat-haptic-feedback`. Names containing other punctuation or Unicode also receive a stable hash suffix. Prefer the exact URL shown in the workflow run summary or branch page.

Every GitHub Actions build also uploads a `decktation.zip` artifact. Open the run for the branch or pull request and use the download link in its summary. This works without GitHub Pages, but downloading the artifact requires signing in and is subject to GitHub’s artifact retention period.

To publish public branch ZIPs from a fork, enable **Settings → Pages → Build and deployment → Source → GitHub Actions** in that fork. The workflow deploys through the `decktation-previews` environment.

## Install a local development build

See [Development](DEVELOPMENT.md) for the source build and contributor workflow. For a local plugin package, use the Decky plugin builder and install the resulting ZIP through **Install Plugin from ZIP**.

## Consistent branch installs

Use the branch download ending in **`Decktation.zip`**, with that capitalization.
For example, the `feat/transcription-review` branch uses:

```text
https://silverfoxy.github.io/decktation/branches/feat-transcription-review/Decktation.zip
```

Paste that URL into Decky Settings → Developer → Install Plugin from URL.
Use the same route to switch to another branch or return to the stable
`https://decktation.com/Decktation.zip` build. Branch builds do
not need a store entry. Their commit/version remains in the manifest and download
metadata; their install identity always stays `Decktation`.

Decky derives the initial plugin name from the URL filename before reading the
ZIP manifest. Matching `Decktation` lets it recognize an existing installation
and unload it before extracting the replacement. If downloading a ZIP locally (including the lowercase GitHub release asset),
rename it to `Decktation.zip` before importing it. Avoid query strings on install URLs, since
Decky includes them when deriving this name.

The lowercase `decktation.zip` and `latest.zip` addresses remain compatibility
downloads, but should not be used for Decky's URL installer. If an earlier install
has already stalled, restart Decky before trying the matching-name URL.
