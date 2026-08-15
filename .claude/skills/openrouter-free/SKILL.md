---
name: openrouter-free
description: Use this to write code to call an LLM using LiteLLM and OpenRouter with a free-tier OpenRouter model
---

# Calling an LLM via a free OpenRouter model

These instructions allow you to write code to call an LLM using one of OpenRouter's free-tier models (no separate inference-provider account needed, no per-token cost).
This method uses LiteLLM and OpenRouter.

## Setup

The OPENROUTER_API_KEY must be set in the .env file and loaded in as an environment variable.

The uv project must include litellm and pydantic.
`uv add litellm pydantic`

## Code snippets

Use code like these examples in order to use a free OpenRouter model.

### Imports and constants

```python
from litellm import completion
MODEL = "openrouter/deepseek/deepseek-chat-v3.1:free"
```

### Code to call for a text response

```python
response = completion(model=MODEL, messages=messages)
result = response.choices[0].message.content
```

### Code to call for a Structured Outputs response

```python
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass)
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```

## Notes

- Free OpenRouter models (suffixed `:free`) have low rate limits and may queue under load — acceptable for this project's single-user, simulated-money use case.
- If the model changes, keep the `:free` suffix so no billing is incurred.
