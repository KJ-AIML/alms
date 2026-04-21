# How to Publish ALMS CLI to PyPI

This guide shows you how to publish the CLI so users can install it globally with `pip install alms-cli` or run it with `uvx alms-cli`.

## Prerequisites

1. Create a PyPI account at https://pypi.org
2. Create a TestPyPI account at https://test.pypi.org (for testing)

## Method 1: Manual Publishing (Quick)

### Step 1: Install twine

```bash
cd cli
uv pip install twine
```

### Step 2: Build the package

```bash
uv pip install build
uv run python -m build
```

This creates files in `dist/`:
- `alms_cli-0.1.0-py3-none-any.whl` (wheel)
- `alms_cli-0.1.0.tar.gz` (source distribution)

### Step 3: Test on TestPyPI (Recommended first)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ alms-cli

# Run it
alms init test-project
```

### Step 4: Publish to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Users can now install globally
pip install alms-cli
uvx alms-cli
```

## Method 2: Automated with GitHub Actions (Recommended)

### Step 1: Set up PyPI Trusted Publishing

1. Go to https://pypi.org/manage/account/publishing/
2. Add a new pending publisher:
   - **Project name**: `alms-cli`
   - **Owner**: `KJ-AIML`
   - **Repository name**: `alms`
   - **Workflow name**: `publish.yml`

### Step 2: Create a GitHub Release

```bash
# Tag the release
git tag v0.1.0
git push origin v0.1.0

# Create release on GitHub
# Go to https://github.com/KJ-AIML/alms/releases/new
# Create a new release with tag v0.1.0
```

### Step 3: GitHub Actions will auto-publish

When you publish a release, the workflow in `.github/workflows/publish.yml` will:
1. Build the package
2. Upload to PyPI automatically
3. Users can install immediately

## After Publishing

Users can now use your CLI in three ways:

### 1. Install globally with pip

```bash
pip install alms-cli
alms init my-project
```

### 2. Install with uv

```bash
uv pip install alms-cli
alms init my-project
```

### 3. Run without installing (like uvx)

```bash
uvx alms-cli init my-project
```

## Updating the Package

To release a new version:

1. Update version in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. Build and upload:
   ```bash
   uv run python -m build
   twine upload dist/*
   ```

3. Or create a new GitHub release tag

## Troubleshooting

### Package name already taken

If `alms-cli` is taken, change the name in `pyproject.toml`:
```toml
name = "alms-cli-tool"
```

### Authentication error with twine

Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN
```

Or use environment variables:
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_API_TOKEN
```

### Build fails

Clean and rebuild:
```bash
rm -rf dist/ build/ *.egg-info
uv run python -m build
```
