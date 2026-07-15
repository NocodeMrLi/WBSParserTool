import json
import re

import requests

from config.config_manager import ApiConfig
from core.result_validator import validate_result


class AiClientError(RuntimeError):
    pass


SYSTEM_PROMPT = (
    "\u4f60\u662f\u8d44\u6df1\u9879\u76ee\u7ecf\u7406\u548c\u4e1a\u52a1\u5206\u6790\u5e08\u3002"
    "\u4f60\u9700\u8981\u628a\u9700\u6c42\u6587\u6863\u62c6\u89e3\u4e3a\u53ef\u6267\u884c\u7684 WBS \u548c\u4efb\u52a1\u6e05\u5355\u3002"
    "\u5fc5\u987b\u53ea\u8fd4\u56de\u5408\u6cd5 JSON\uff0c\u4e0d\u8981\u8fd4\u56de Markdown\uff0c\u4e0d\u8981\u89e3\u91ca\u3002"
)


def parse_online(text: str, config: ApiConfig, source_name: str = "") -> dict:
    if not config.is_complete:
        raise AiClientError("\u0041\u0050\u0049 \u914d\u7f6e\u4e0d\u5b8c\u6574\u3002")

    user_prompt = _build_prompt(text, source_name)
    data = _chat_completion(config, user_prompt, timeout=180, max_tokens=12000)
    content = _extract_message_content(data)

    try:
        result = _parse_json_content(content)
    except AiClientError as first_error:
        repaired = _repair_json_with_model(content, str(first_error), config)
        try:
            result = _parse_json_content(repaired)
        except AiClientError as second_error:
            raise AiClientError(
                "\u0041\u0049 \u8fd4\u56de\u5185\u5bb9\u4e0d\u662f\u5408\u6cd5 JSON\uff0c"
                "\u5df2\u5c1d\u8bd5\u81ea\u52a8\u4fee\u590d\u4f46\u4ecd\u5931\u8d25\u3002\n"
                f"\u539f\u59cb\u9519\u8bef\uff1a{first_error}\n"
                f"\u4fee\u590d\u540e\u9519\u8bef\uff1a{second_error}"
            ) from second_error

    return validate_result(result)


def test_connection(config: ApiConfig) -> None:
    if not config.is_complete:
        raise AiClientError("\u8bf7\u586b\u5199 API Base URL\u3001API Key \u548c\u6a21\u578b\u540d\u79f0\u3002")

    prompt = "\u8bf7\u53ea\u8fd4\u56de\u4e00\u4e2a JSON\uff1a{\"ok\": true}"
    data = _chat_completion(config, prompt, timeout=30, max_tokens=120)
    content = _extract_message_content(data)
    if "ok" not in content.lower() and "true" not in content.lower():
        raise AiClientError("\u0041\u0050\u0049 \u5df2\u54cd\u5e94\uff0c\u4f46\u8fd4\u56de\u5185\u5bb9\u4e0d\u7b26\u5408\u9884\u671f\u3002")


def _chat_completion(config: ApiConfig, user_prompt: str, timeout: int, max_tokens: int = 4096) -> dict:
    url = _completion_url(config.base_url)
    headers = {
        "Authorization": f"Bearer {config.api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model.strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise AiClientError(f"\u0041\u0050\u0049 \u8bf7\u6c42\u5931\u8d25\uff1a{exc}") from exc

    if response.status_code >= 400:
        raise AiClientError(f"\u0041\u0050\u0049 \u8fd4\u56de\u9519\u8bef {response.status_code}\uff1a{response.text[:800]}")

    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise AiClientError("\u0041\u0050\u0049 \u8fd4\u56de\u5185\u5bb9\u4e0d\u662f\u6709\u6548 JSON\u3002") from exc


def _completion_url(base_url: str) -> str:
    clean = base_url.strip().rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    return f"{clean}/chat/completions"


def _extract_message_content(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AiClientError("\u0041\u0050\u0049 \u8fd4\u56de\u7ed3\u6784\u4e0d\u7b26\u5408 OpenAI Chat Completions \u683c\u5f0f\u3002") from exc


def _parse_json_content(content: str) -> dict:
    candidates = _json_candidates(content)
    last_error = None
    for candidate in candidates:
        for clean in _cleanup_variants(candidate):
            try:
                return json.loads(clean)
            except json.JSONDecodeError as exc:
                last_error = exc

    if last_error:
        raise AiClientError(f"\u65e0\u6cd5\u89e3\u6790 JSON\uff1a{last_error}")
    raise AiClientError("\u672a\u627e\u5230 JSON \u5bf9\u8c61\u3002")


def _json_candidates(content: str) -> list[str]:
    clean = content.strip().lstrip("\ufeff")
    clean = re.sub(r"^```(?:json)?", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"```$", "", clean).strip()

    candidates = []
    block = _extract_balanced_json(clean)
    if block:
        candidates.append(block)

    greedy = re.search(r"\{.*\}", clean, re.DOTALL)
    if greedy:
        candidates.append(greedy.group(0))

    candidates.append(clean)
    return _dedupe(candidates)


def _cleanup_variants(text: str) -> list[str]:
    base = text.strip()
    variants = [base]

    cleaned = base.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    variants.append(cleaned)

    escaped_controls = _escape_control_chars_in_strings(cleaned)
    variants.append(escaped_controls)

    return _dedupe(variants)


def _extract_balanced_json(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def _escape_control_chars_in_strings(text: str) -> str:
    result = []
    in_string = False
    escape = False
    for char in text:
        if in_string:
            if escape:
                result.append(char)
                escape = False
            elif char == "\\":
                result.append(char)
                escape = True
            elif char == '"':
                result.append(char)
                in_string = False
            elif char == "\n":
                result.append("\\n")
            elif char == "\r":
                result.append("\\r")
            elif char == "\t":
                result.append("\\t")
            else:
                result.append(char)
        else:
            result.append(char)
            if char == '"':
                in_string = True
    return "".join(result)


def _repair_json_with_model(content: str, error: str, config: ApiConfig) -> str:
    repair_prompt = f"""
\u4e0b\u9762\u662f\u4e00\u6bb5\u672a\u901a\u8fc7\u89e3\u6790\u7684 JSON\u3002
\u8bf7\u4fee\u590d\u5b83\u7684\u8bed\u6cd5\u9519\u8bef\uff0c\u5e76\u53ea\u8fd4\u56de\u4fee\u590d\u540e\u7684\u5408\u6cd5 JSON\u3002
\u4e0d\u8981\u6539\u53d8\u5b57\u6bb5\u542b\u4e49\uff0c\u4e0d\u8981\u8f93\u51fa Markdown\uff0c\u4e0d\u8981\u89e3\u91ca\u3002

\u89e3\u6790\u9519\u8bef\uff1a{error}

\u539f\u59cb\u5185\u5bb9\uff1a
{content[:50000]}
""".strip()
    data = _chat_completion(config, repair_prompt, timeout=120, max_tokens=12000)
    return _extract_message_content(data)


def _dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _build_prompt(text: str, source_name: str) -> str:
    clipped_text = text[:35000]
    truncated_note = "\n\u6ce8\u610f\uff1a\u539f\u6587\u8f83\u957f\uff0c\u4ee5\u4e0b\u5185\u5bb9\u5df2\u622a\u53d6\u524d 35000 \u5b57\u7b26\u3002" if len(text) > len(clipped_text) else ""
    display_source_name = source_name or "\u672a\u547d\u540d\u9700\u6c42\u6587\u6863"
    return f"""
\u8bf7\u5c06\u4e0b\u9762\u7684\u9700\u6c42\u6587\u6863\u62c6\u89e3\u4e3a\u53ef\u6267\u884c\u7684\u5de5\u4f5c\u5206\u89e3\u7ed3\u6784 WBS \u548c\u5177\u4f53\u4efb\u52a1\u6e05\u5355\u3002{truncated_note}

\u6587\u6863\u540d\u79f0\uff1a{display_source_name}

\u5fc5\u987b\u9075\u5b88\uff1a
1. \u53ea\u8fd4\u56de\u4e00\u4e2a\u5408\u6cd5 JSON \u5bf9\u8c61\u3002
2. \u4e0d\u8981 Markdown\uff0c\u4e0d\u8981 ```json \u4ee3\u7801\u5757\uff0c\u4e0d\u8981\u89e3\u91ca\u6587\u5b57\u3002
3. \u6240\u6709\u952e\u540d\u5fc5\u987b\u4f7f\u7528\u82f1\u6587\u53cc\u5f15\u53f7\u3002
4. \u6240\u6709\u5b57\u7b26\u4e32\u5fc5\u987b\u4f7f\u7528\u82f1\u6587\u53cc\u5f15\u53f7\uff0c\u5b57\u7b26\u4e32\u5185\u90e8\u4e0d\u80fd\u51fa\u73b0\u672a\u8f6c\u4e49\u7684\u6362\u884c\u3002
5. \u6570\u7ec4\u548c\u5bf9\u8c61\u7684\u6700\u540e\u4e00\u9879\u540e\u9762\u4e0d\u8981\u52a0\u9017\u53f7\u3002
6. tasks \u5efa\u8bae 8-30 \u6761\uff0c\u4e0d\u8981\u8f93\u51fa\u8fc7\u957f\u5bfc\u81f4 JSON \u88ab\u622a\u65ad\u3002

JSON \u7ed3\u6784\u5fc5\u987b\u4e25\u683c\u5982\u4e0b\uff1a
{{
  "project_summary": {{
    "name": "\u9879\u76ee\u540d\u79f0",
    "background": "\u9879\u76ee\u80cc\u666f",
    "goals": ["\u76ee\u68071"],
    "scope": ["\u8303\u56f41"],
    "assumptions": ["\u5047\u8bbe1"]
  }},
  "wbs": [
    {{
      "id": "1",
      "name": "\u9879\u76ee\u542f\u52a8",
      "children": [
        {{
          "id": "1.1",
          "name": "\u9700\u6c42\u786e\u8ba4",
          "deliverable": "\u9700\u6c42\u786e\u8ba4\u8bb0\u5f55"
        }}
      ]
    }}
  ],
  "tasks": [
    {{
      "task_id": "T001",
      "wbs_id": "1.1",
      "phase": "\u9879\u76ee\u542f\u52a8",
      "task_name": "\u786e\u8ba4\u9700\u6c42\u8303\u56f4",
      "description": "\u786e\u8ba4\u9700\u6c42\u6587\u6863\u8303\u56f4\u3001\u76ee\u6807\u548c\u5173\u952e\u5e72\u7cfb\u4eba\u3002",
      "owner_role": "\u9879\u76ee\u7ecf\u7406",
      "input": "\u9700\u6c42\u6587\u6863",
      "output": "\u9700\u6c42\u786e\u8ba4\u8bb0\u5f55",
      "priority": "\u9ad8",
      "estimated_duration": "0.5\u5929",
      "dependency": "\u65e0",
      "acceptance_criteria": "\u9700\u6c42\u8303\u56f4\u548c\u5173\u952e\u5e72\u7cfb\u4eba\u5df2\u786e\u8ba4\u3002"
    }}
  ]
}}

\u9700\u6c42\u6587\u6863\u6b63\u6587\uff1a
{clipped_text}
""".strip()
