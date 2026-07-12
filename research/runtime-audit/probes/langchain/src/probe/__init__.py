"""ALMS Phase 0 LangChain compatibility audit probe (langchain-openai / ChatOpenAI).

Research/audit infrastructure ONLY. Implements Probe Process Protocol v0 (DevSpec
Section 23) which is NOT the future ModelRuntime contract. LangChain is used only inside
this isolated probe; the central harness never imports it. This lane runs the SAME control
provider/model as the openai-native lane so framework transformations are the only variable
(DevSpec Section 48).
"""

__version__ = "0.0.0"
PROBE_ID = "langchain"
PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"
