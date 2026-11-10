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

## PR test builds

Configure the [opt-in testing catalog](TESTING_STORE.md) at `https://decktation.com/testing/plugins.json`. It lists successful builds of **open PRs, including forks, without approval**; select a PR version deliberately. These packages have not been reviewed for safety. Master and branch builds are not included.

PR packages stay in Actions artifacts for 30 days. Their public URLs use the Worker, so Decky does not need a GitHub login. Expired builds require a new successful build. Stable ZIPs stay in GitHub Releases; Pages stores no plugin packages.

For manual testing, CI still uploads `decktation.zip` artifacts for builds. Open the run and use its summary download link. Direct Actions downloads require signing in and are subject to artifact retention. Old public `/branches/…/Decktation.zip` URLs are retired.

## Install a local development build

See [Development](DEVELOPMENT.md) for the source build and contributor workflow. For a local plugin package, use the Decky plugin builder and install the resulting ZIP through **Install Plugin from ZIP**.

## Consistent test installs

Select the intended PR version in Decky's testing-store dropdown. For a manual ZIP install, keep the filename `Decktation.zip` so Decky recognizes and unloads the existing plugin. Return to the latest stable release at `https://decktation.com/Decktation.zip` when finished.
