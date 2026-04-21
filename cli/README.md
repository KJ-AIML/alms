# ALMS CLI

> **Beautiful project scaffolding tool for AI-first backends.**

## Installation

### Install via pip (Global)

```bash
pip install alms-cli
```

### Install via uv (Recommended)

```bash
uv pip install alms-cli
```

### Run without installing (like uvx)

```bash
uvx --from alms-cli alms init my-project
```

## Usage

### Create a new project

```bash
alms init my-project
```

### Create a project non-interactively

```bash
alms init my-project --no-interactive
```

### Show project information

```bash
alms info
```

## Features

- Beautiful terminal UI with Rich
- Interactive prompts with Questionary
- Complete ALMS project scaffolding
- Feature selection (Database, Redis, AI Agents, Observability, Docker, CI/CD)
- Progress indicators and status updates

## Development

### Local development

```bash
cd cli
uv sync
uv run alms
```

### Build package

```bash
cd cli
uv pip install build
uv run python -m build
```

### Publish to PyPI

```bash
# Install twine
uv pip install twine

# Upload to PyPI
twine upload dist/*
```

## License

MIT
