"""In-memory prompt registry."""

from contentos_prompts.domain.prompt_version import PromptDefinition


class PromptRegistry:
    def __init__(self) -> None:
        self._prompts: dict[str, PromptDefinition] = {}

    def register(self, prompt: PromptDefinition) -> None:
        self._prompts[prompt.id] = prompt

    def get(self, prompt_id: str) -> PromptDefinition | None:
        return self._prompts.get(prompt_id)

    def list_all(self) -> list[PromptDefinition]:
        return sorted(self._prompts.values(), key=lambda p: p.id)

    def clear(self) -> None:
        self._prompts.clear()
