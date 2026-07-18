from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.services.llm.base import LLMProvider
from backend.services.llm.tools.base import ToolRegistry


@dataclass
class ToolRunResult:
    """Результат диалога с tool calling: финальный ответ и список
    фактически вызванных инструментов (для отображения в UI)."""

    content: str
    tools_used: list[str] = field(default_factory=list)


async def run_with_tools(
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    registry: ToolRegistry,
    model: str | None = None,
    max_iterations: int = 5,
) -> ToolRunResult:
    conversation: list[dict[str, Any]] = list(messages)
    tool_schemas = registry.schemas()
    tools_used: list[str] = []

    for _ in range(max_iterations):
        result = await provider.chat(conversation, model=model, tools=tool_schemas)

        if not result.tool_calls:
            return ToolRunResult(
                content=result.content,
                tools_used=list(dict.fromkeys(tools_used)),
            )

        conversation.append(provider.format_assistant_tool_calls(result))

        for call in result.tool_calls:
            tool = registry.get(call.name)

            if tool is None:
                output = f"Ошибка: инструмент '{call.name}' не найден"
            else:
                output = await tool.run(call.arguments)
                tools_used.append(call.name)

            conversation.append(provider.format_tool_result(call, output))

    final = await provider.chat(conversation, model=model)

    return ToolRunResult(
        content=final.content,
        tools_used=list(dict.fromkeys(tools_used)),
    )
