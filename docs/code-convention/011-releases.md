# Convention 011: Releases

> Workflow: [`.github/workflows/release.yml`](../../.github/workflows/release.yml) · Check: [`scripts/release_check/`](../../scripts/release_check)

## Versions

- **The engine image follows Semantic Versioning, `MAJOR.MINOR.PATCH`,** taken from `core/pyproject.toml` ([semver.org](https://semver.org/)). A patch fixes without changing behaviour consumers rely on; a minor release adds; a major one breaks.
- **The image version is not the API version.** `Diplex-Api-Version` changes only when the contract breaks, and a release keeps serving the previous API version for at least one more release ([ADR 012](../adr/012-api-key-and-version.md)).
- **Images are tagged `1.2.3` and `1.2`,** never `latest`, so a self-hoster always knows what runs. The `1.2` tag moves to each patch, which is how security fixes reach those who follow it.

## Releasing

1. **Bump the version** in `core/pyproject.toml`, run `cd core && uv lock` and `uv run python -m diplex.openapi_export ../docs/openapi.json`, and merge that through a pull request with CI green.
2. **Tag the merge commit on `main`** with `v` and the version, and push the tag: `git tag v1.2.3 && git push origin v1.2.3`.
3. **The release workflow checks and publishes:** `python -m scripts.release_check v1.2.3` must find the same version in `core/pyproject.toml` and `docs/openapi.json`, then the root Dockerfile is built and pushed to `ghcr.io/<owner>/diplex-core:1.2.3` and `:1.2`, with build provenance.
4. **The first time only,** make the `diplex-core` package public in the repository owner's GitHub package settings, so self-hosters can pull it without logging in.

## Security Releases

- **A fix to how untrusted documents are handled ships as a patch release as soon as it is merged,** without waiting for other work.
- **Only the latest minor version gets fixes;** the self-hosting guide tells operators to follow its `MAJOR.MINOR` tag.
