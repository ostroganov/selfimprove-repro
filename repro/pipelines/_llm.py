#!/usr/bin/env python3
"""Provider clients. Tier B: needs API keys and costs money."""
import os

from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {"claude": "anthropic", "gpt": "openai", "grok": "xai", "gemini": "google"}
_clients = {}


def provider_of(model_id: str) -> str:
    for prefix, name in PROVIDERS.items():
        if model_id.startswith(prefix):
            return name
    raise ValueError(f"no provider for {model_id!r}")


def client(provider: str):
    if provider not in _clients:
        if provider == "anthropic":
            import anthropic
            c = anthropic.Anthropic()
        else:
            from openai import OpenAI
            base = {"xai": ("https://api.x.ai/v1", "XAI_API_KEY"),
                    "google": ("https://generativelanguage.googleapis.com/v1beta/openai/",
                               "GOOGLE_API_KEY")}.get(provider)
            c = OpenAI() if base is None else OpenAI(base_url=base[0],
                                                     api_key=os.environ[base[1]])
        _clients[provider] = c
    return _clients[provider]


def generate(model_id, system, user, temperature, max_tokens):
    """One completion -> (text, in_tokens, out_tokens).

    A blank system prompt means the bare model (the L0 baseline), so the field
    is omitted rather than sent empty.
    """
    system = (system or "").strip()
    provider = provider_of(model_id)
    cli = client(provider)
    if provider == "anthropic":
        kw = dict(model=model_id, max_tokens=max_tokens, temperature=temperature,
                  messages=[{"role": "user", "content": user}])
        if system:
            kw["system"] = system
        r = cli.messages.create(**kw)
        return ("".join(b.text for b in r.content if getattr(b, "type", "") == "text"),
                r.usage.input_tokens, r.usage.output_tokens)

    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": user}]
    kw = dict(model=model_id, messages=msgs)
    if temperature is not None:
        kw["temperature"] = temperature
    try:
        r = cli.chat.completions.create(**kw)
    except Exception as e:
        if "temperature" not in str(e).lower():
            raise
        kw.pop("temperature", None)                  # reasoning models reject it
        r = cli.chat.completions.create(**kw)
    return r.choices[0].message.content or "", r.usage.prompt_tokens, r.usage.completion_tokens
