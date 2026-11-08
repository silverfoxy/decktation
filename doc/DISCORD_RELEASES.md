# Discord release announcements

Stable releases are announced after the trusted publisher has uploaded
`Decktation.zip` to GitHub Releases. The message includes the tagged version's
`CHANGELOG.md` notes, an installable download link, website release notes, and the
feature walkthrough. Drafts, prereleases, branches, and PR test builds are not
announced. Mentions are disabled, including `@everyone` and role pings.

## One-time setup

1. In Discord, create an incoming webhook for the destination channel under
   **Edit Channel → Integrations → Webhooks** (requires Manage Webhooks).
2. Save its URL as the GitHub Actions repository secret
   `DISCORD_RELEASE_WEBHOOK_URL` under **Settings → Secrets and variables → Actions**.
   The webhook selects the channel; no channel ID or bot token is needed.

If the secret is absent, publishing still succeeds and the announcement step
reports that it was skipped. Invalid credentials or delivery failures fail the
announcement step so the maintainer can fix the secret and retry.

## Retry or announce a release that already exists

Run **Actions → Announce release on Discord → Run workflow** on `master` and enter
the release tag, such as `v0.3.22`. The archive must already be uploaded. The script
reads the notes from that tag, even if `master` has newer changes.

After Discord confirms a saved message, a hidden HTML comment in the GitHub
release body stores its message ID. Reruns skip an already announced release.
The publisher preserves this marker before its release uploader rewrites the
body, then restores it afterward. Do not remove the comment unless an announcement
should be sent again. If delivery succeeds but writing the marker fails, preserve
the message ID shown in the job log before retrying to avoid a duplicate.

Automatic notifications run directly in the publisher because GitHub does not
start new workflows for release events generated with `GITHUB_TOKEN`. The
standalone workflow also supports stable releases published by a maintainer.
Only trusted `master` scripts run with the webhook secret; candidate PR code
never receives it.

References: [GitHub token event behavior](https://docs.github.com/en/actions/concepts/security/github_token),
[Discord webhook API](https://github.com/discord/discord-api-docs/blob/main/developers/resources/webhook.mdx).
