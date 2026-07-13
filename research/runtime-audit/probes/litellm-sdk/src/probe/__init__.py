"""ALMS Phase 0 LiteLLM SDK abstraction audit probe (litellm.completion).

Research/audit infrastructure ONLY. Implements Probe Process Protocol v0 (DevSpec
Section 23) which is NOT the future ModelRuntime contract. The LiteLLM Python SDK is used
only inside this isolated probe; the central harness never imports it.

BOUNDARY: this lane audits the LiteLLM Python SDK (`litellm.completion`), NOT the LiteLLM
Proxy Server, virtual keys, gateway auth, router, fallbacks, or spend tracking. LiteLLM
presents unlike providers through an OpenAI-Chat-Completions-shaped abstraction; that
abstraction is the audit subject, and its output is framework-owned (framework_native),
never provider-native merely because the field names resemble OpenAI's.
"""

import os

# CRITICAL (offline safety): force LiteLLM to use its bundled local model-cost map. Without this,
# `import litellm` fetches a remote cost map from GitHub at import time, which would trip the
# offline network tripwire. Set BEFORE any submodule imports litellm; setdefault so an operator
# override still wins.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

__version__ = "0.0.0"
PROBE_ID = "litellm-sdk"
PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"
