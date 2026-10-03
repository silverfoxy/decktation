# Installation guide

For the recommended install walkthrough, start with the [README](../README.md#install-decktation). This page covers manual updates, alternative packaged builds, and notes for developers.

## Install a stable release

Use a packaged plugin ZIP, which includes the runtime dependencies required by Decktation:

- [Recommended short URL](https://silverfoxy.github.io/decktation/latest.zip)
- [Full stable URL](https://silverfoxy.github.io/decktation/releases/latest/decktation.zip)
- [GitHub release asset](https://github.com/silverfoxy/decktation/releases/latest/download/decktation.zip)

Keep Decky's **Store Channel** set to **Default** for the recommended install. In Decky Settings, choose **Install Plugin from URL** and paste the short URL above, or download the ZIP and choose **Install Plugin from ZIP**. Enable developer options if those actions are not shown. Decky imports the archive and reloads the plugin.

Decky uses an **Install Plugin from URL** address to download that ZIP; it does not save the address as an update feed. Until Decktation appears in the currently selected catalog, Decky will not discover new Decktation releases automatically. Keep **Default** selected so other plugins continue to receive their normal official catalog update checks.

Do not use GitHub’s automatically generated **Source code (zip)** or **Source code (tar.gz)** archives. They are not installable Decktation packages and do not contain the bundled dependencies. Do not extract the packaged plugin ZIP or copy its contents into Decky’s plugin directory.

## Updating Decktation before it reaches the official store

Until Decktation is available in Decky's official store, update it manually when you want a newer release:

1. Open Decky and uninstall the current Decktation plugin using Decky's normal uninstall action.
2. Install the [latest packaged ZIP](https://silverfoxy.github.io/decktation/latest.zip) with **Install Plugin from URL**, or download it and use **Install Plugin from ZIP**.
3. Reopen Decktation.

For manual updates, uninstall the current plugin before installing the latest ZIP. This gives Decky a clean plugin-code replacement and removes files left behind by an older release. Leave Decktation settings and downloaded Whisper model files alone; deleting them is not part of a normal update.

Once Decktation is available in Decky's official **Default** store, that will be the preferred install and update route. Existing manual installations with the same plugin name and an older valid version should normally become eligible for official store updates without a fresh install. This describes current Decky behavior and is not a permanent API guarantee.

For details about the optional Decktation Custom Store and its effect on the selected catalog, see [Decky Store notes](DECKY_STORE.md).

## Branch builds

When GitHub Pages is enabled for a repository, branch packages use this URL pattern:

```text
https://<owner>.github.io/decktation/branches/<branch-slug>/decktation.zip
```

Branch names use readable ASCII slugs. For example, `feat/haptic-feedback` uses `feat-haptic-feedback`. Names containing other punctuation or Unicode also receive a stable hash suffix. Prefer the exact URL shown in the workflow run summary or branch page.

Every GitHub Actions build also uploads a `decktation.zip` artifact. Open the run for the branch or pull request and use the download link in its summary. This works without GitHub Pages, but downloading the artifact requires signing in and is subject to GitHub’s artifact retention period.

To publish public branch ZIPs from a fork, enable **Settings → Pages → Build and deployment → Source → GitHub Actions** in that fork. The workflow deploys through the `decktation-previews` environment.

## Install a local development build

See [Development](DEVELOPMENT.md) for the source build and contributor workflow. For a local plugin package, use the Decky plugin builder and install the resulting ZIP through **Install Plugin from ZIP**.
