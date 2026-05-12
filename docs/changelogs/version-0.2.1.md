# ALMS Changelog - Version 0.2.1

**Release Date:** May 12, 2026  
**Version:** 0.2.1  
**Codename:** "Skill Alignment"

---

## Overview

This patch release aligns the ALMS starter structure with the public LangGraph agent skill. It keeps the existing sample endpoint flow intact while adding the missing agent-layer skeleton expected by AI coding assistants.

---

## Changes

- Added `src/agents/prompts/prompt_manager.py` for lazy markdown prompt loading.
- Added `src/agents/prompts/agents/agent_sample.md` as the sample prompt source.
- Added `src/agents/schemas/` for structured agent output schemas.
- Added `src/agents/workflows/sample/` with `state.py`, `nodes.py`, and `build.py`.
- Updated README examples so new agents follow `Endpoint -> UseCase -> Action -> Agent/Workflow`.
- Bumped package version to `0.2.1`.

---

## Compatibility

This release is backward compatible. Existing sample API behavior remains the same, but the starter now provides the folders and examples expected by `alms-langgraph-agent-skill`.
