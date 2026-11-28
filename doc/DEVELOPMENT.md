# Development

Decktation has a TypeScript/React Decky panel and a Python backend. The backend records audio, runs a resident whisper.cpp server with Vulkan or CPU inference, parses game-channel prefixes, and starts a controller listener. The packaged plugin includes its runtime dependencies and keyboard helper.

## Build the frontend

Install the Node dependencies and build the panel:

```bash
npm install
npm run build
```

The build writes the compiled panel to `dist/index.js`. Use `npm run watch` while editing the frontend.

## Run the Python tests

Use Python 3.11, matching the bundled backend runtime. The exact version is in
`.python-version`; backend and integration CI read this same pin. Install that
version with your Python version manager before creating the test environment.
The separate Decky loader bridge also retains Python 3.14 compatibility checks.

Install the test dependencies in a virtual environment, then run the unit tests:

```bash
make test-setup
make test
```

`requirements-test.txt` includes both pytest and the Sentry SDK used by the
telemetry tests, so this command runs the complete Python suite without test
exclusions. Re-run `make test-setup` after the test requirements change.

The CI workflow also runs the Cloudflare worker tests, Python compile checks, and the Decky package build. See [`.github/workflows/build.yml`](../.github/workflows/build.yml) for the current commands and artifact validation.

## Build an installable package

The GitHub Actions workflow builds the installable `decktation.zip` with the Decky CLI and validates that the bundled Python runtime, speech-recognition dependencies, configuration, and keyboard helper are present. To install a development build, download the ZIP artifact from the workflow run and use Decky’s **Install Plugin from ZIP** option. For public branch URLs and artifact notes, see the [installation guide](INSTALLATION.md).
