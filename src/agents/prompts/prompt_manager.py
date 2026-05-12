from pathlib import Path


class PromptManager:
    """Lazy-load markdown prompts from the agent prompt directory."""

    def __init__(self, prompt_base_path: str | Path | None = None) -> None:
        self.prompt_base_path = (
            Path(prompt_base_path)
            if prompt_base_path is not None
            else Path(__file__).resolve().parent
        )
        self._sample_agent: str | None = None

    @property
    def sample_agent(self) -> str:
        if self._sample_agent is None:
            self._sample_agent = self._load_prompt("agents/agent_sample.md")
        return self._sample_agent

    def _load_prompt(self, filename: str) -> str:
        return (self.prompt_base_path / filename).read_text(encoding="utf-8")


prompt_manager = PromptManager()
