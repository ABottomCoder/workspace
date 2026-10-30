"""LLM providers. Selected by LLM_PROVIDER (default: anthropic)."""
import os

import anthropic
import httpx


class AnthropicProvider:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = os.getenv("LLM_MODEL", "claude-sonnet-4-5")

    def complete(self, system, user, max_tokens=800):
        r = self.client.messages.create(model=self.model, system=system, max_tokens=max_tokens,
                                        messages=[{"role": "user", "content": user}])
        return r.content[0].text


class OpenAICompatProvider:
    """Any endpoint that speaks the OpenAI chat-completions format. Written, not enabled."""

    def __init__(self):
        self.base = os.environ["LLM_BASE_URL"].rstrip("/")
        self.key = os.environ["LLM_API_KEY"]
        self.model = os.environ["LLM_MODEL"]

    def complete(self, system, user, max_tokens=800):
        r = httpx.post(f"{self.base}/chat/completions", timeout=60,
                       headers={"Authorization": f"Bearer {self.key}"},
                       json={"model": self.model, "max_tokens": max_tokens,
                             "messages": [{"role": "system", "content": system},
                                          {"role": "user", "content": user}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def get_provider():
    return {"anthropic": AnthropicProvider, "openai_compat": OpenAICompatProvider}[
        os.getenv("LLM_PROVIDER", "anthropic")]()
