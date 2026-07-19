# Decky Plugin Store readiness

Decktation is a Decky plugin, but its current GitHub release packaging is not
the same build path used by the Decky Plugin Database. The store runs
`decky plugin build -b` against the submitted repository commit. It does not
run this repository's `.github/workflows/build.yml` first.

## Completed in the repository

- `plugin.json` declares Decky API version 1 and has release-safe flags.
- Store metadata includes a public HTTPS image.
- `package.json` contains the canonical plugin version.
- A root MIT `LICENSE` is included.
- Runtime Python dependencies are pinned in `backend/src/requirements.txt`.
- Decky's Holo backend builds the Python runtime directory and ydotool 1.0.4.
- The ydotool source revision, build recipe, and AGPL license are included.
- The plugin owns a private `0600` ydotool socket and cleans up its process.
- `_root` is declared for `/dev/uinput` and raw Steam Deck HID access.
- A frozen `pnpm-lock.yaml` is committed for the marketplace frontend build.
- Decky CLI 0.0.7 produces a valid 82.7 MB zip (274 MB installed).
- Frontend source and the generated `dist/index.js` are present.

## Blocking work before submission

### 1. Validate native dependencies on every target channel

The Decky backend hook now produces all native output under `backend/out`,
which Decky's builder copies into the packaged plugin's `bin/` directory.

The Python extension ABI must also match every Decky/SteamOS channel claimed
as supported. Loading CPython 3.11 or 3.13 extension modules into the other
runtime is not compatible. Hardware-test the built artifact on each required
channel. If their Python ABIs differ, move transcription into a self-contained
worker executable and leave `main.py` as a thin Decky API bridge.

PortAudio is a dynamically linked third-party dependency used by
`sounddevice`; answer **Yes** to the corresponding backend question in the
submission template and verify it on Stable and Beta.

### 2. Test the actual store artifact

Build with the same CLI invocation as the Plugin Database:

```sh
decky plugin build -b -o /tmp/decktation-output -s directory .
```

Inspect the resulting zip, install that zip on hardware, and verify:

- clean installation with no terminal setup;
- model download, restart, and offline model reuse;
- microphone selection and recording;
- button handling in Game Mode;
- text injection in at least one game and one non-game text field;
- clean disable, Decky reload, uninstall, and Steam Deck reboot;
- useful UI errors when the model download or microphone is unavailable.

The submission checklist currently requires author testing on SteamOS Stable
and Beta, third-party testing, and feedback on two other open plugin PRs. Check
the live pull-request template immediately before submitting because these
requirements can change.

## Submission

Once the blockers above are complete:

1. Run `make version-set VERSION=X.Y.Z`, then commit the synchronized
   `package.json` and `plugin.json` changes.
2. Run `make release-tag`; it refuses to tag a dirty tree or mismatched
   manifests. Push the printed `vX.Y.Z` tag after reviewing it.
3. Push the exact public repository commit to submit.
4. Fork `SteamDeckHomebrew/decky-plugin-database`.
5. Add this repository as `plugins/decktation` at that exact commit.
6. Open a pull request using the **Plugin addition** template.
