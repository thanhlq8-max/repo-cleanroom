# Publishing to TestPyPI and PyPI

This project publishes the `repo-cleanroom` distribution to TestPyPI and PyPI.
Publication is gated by the maintainer per `docs/RELEASE_POLICY.md` §3 — it never
happens automatically without an explicit action.

Two paths are documented:

- **A. Trusted Publishing (recommended, no stored secrets)** — a GitHub Actions
  workflow (`.github/workflows/publish.yml`) uploads via OIDC. You configure a
  trusted publisher once on each index; after that, publishing is a button click.
- **B. Manual upload with an API token** — run `twine` locally. Use this if you do
  not want the CI workflow, or as a fallback.

The distribution artifacts are always the same: `python -m build` produces
`repo_cleanroom-<version>.tar.gz` (sdist) and `repo_cleanroom-<version>-py3-none-any.whl`
(wheel). Both must pass `python -m twine check dist/*`.

---

## A. Trusted Publishing via GitHub Actions (recommended)

### One-time setup — TestPyPI

1. Create an account at <https://test.pypi.org/> and verify your email.
2. Go to **Account settings → Publishing → Add a pending publisher**
   (<https://test.pypi.org/manage/account/publishing/>).
3. Fill in:
   - PyPI Project Name: `repo-cleanroom`
   - Owner: `thanhlq8-max`
   - Repository name: `repo-cleanroom`
   - Workflow name: `publish.yml`
   - Environment name: `testpypi`
4. Save. (A "pending" publisher becomes active on the first successful upload.)

### One-time setup — PyPI

Repeat the same steps at <https://pypi.org/manage/account/publishing/>, but use
**Environment name: `pypi`**.

### One-time setup — GitHub environments (optional but recommended)

In the repository: **Settings → Environments → New environment**, create `testpypi`
and `pypi`. You can add required reviewers to `pypi` so a human must approve each
production publish.

### Publish a version

Order per release policy: **TestPyPI dry run first, then PyPI.**

1. **TestPyPI dry run** — GitHub → **Actions → Publish → Run workflow**, input
   `target = testpypi`. Verify the result:
   ```powershell
   py -m venv .test-venv
   .\.test-venv\Scripts\Activate.ps1
   py -m pip install --index-url https://test.pypi.org/simple/ `
     --extra-index-url https://pypi.org/simple/ repo-cleanroom
   repo-cleanroom --help
   ```
2. **PyPI** — either:
   - publish a GitHub Release for the version tag (the workflow runs automatically
     on `release: published`), **or**
   - **Actions → Publish → Run workflow**, input `target = pypi`.

> The `v1.0.0` GitHub Release already exists, so re-publishing it will not retrigger
> the workflow. For the first `1.0.0` upload, use the manual `workflow_dispatch` run
> (`target = pypi`). Future versions publish automatically when you cut their Release.

---

## B. Manual upload with an API token

### One-time setup

1. TestPyPI token: <https://test.pypi.org/manage/account/token/> — scope it to the
   `repo-cleanroom` project once the project exists, or account-wide for the first
   upload.
2. PyPI token: <https://pypi.org/manage/account/token/>.
3. Store tokens outside the repository. A `~/.pypirc` works:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-...            # your PyPI token

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-...            # your TestPyPI token
   ```
   `.pypirc` is not in this repository and must never be committed.

### Build and upload

```powershell
# From the repository root, on the tagged commit you want to publish.
py -m pip install --upgrade build twine
py -m build
py -m twine check dist/*

# 1) TestPyPI dry run
py -m twine upload --repository testpypi dist/*

# Verify in a clean environment
py -m venv .test-venv
.\.test-venv\Scripts\Activate.ps1
py -m pip install --index-url https://test.pypi.org/simple/ `
  --extra-index-url https://pypi.org/simple/ repo-cleanroom
repo-cleanroom --help
deactivate

# 2) PyPI (only after the TestPyPI install checks out)
py -m twine upload dist/*
```

If you pass tokens inline instead of `.pypirc`:

```powershell
py -m twine upload --repository-url https://test.pypi.org/legacy/ `
  -u __token__ -p $env:TESTPYPI_TOKEN dist/*
py -m twine upload -u __token__ -p $env:PYPI_TOKEN dist/*
```

---

## Version and naming rules

- A publishable version must first go through a release PR that bumps
  `pyproject.toml`, updates `CHANGELOG.md`, and aligns docs (release policy §2).
- The git tag name equals the package version (`v1.0.0` → package `1.0.0`).
- PyPI does not allow re-uploading an existing version. A mistake needs a new PATCH
  release, never an overwrite. Test on TestPyPI first to avoid burning a version.

## Distribution surfaces

- **PyPI** — `pip install repo-cleanroom`. The canonical distribution channel.
- **GitHub Release assets** — the sdist and wheel are attached to each GitHub
  Release for users who install from a pinned URL or audit artifacts directly.
- GitHub Packages does not host a PyPI-compatible index, so it is not used for this
  Python distribution.
