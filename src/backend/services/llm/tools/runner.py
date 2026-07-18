from __future__ import annotations

from typing import Any

from backend.services.llm.base import LLMProvider
from backend.services.llm.tools.base import ToolRegistry


async def run_with_tools(
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    registry: ToolRegistry,
    model: str | None = None,
    max_iterations: int = 5,
) -> str:
    """Провести диалог с моделью, обрабатывая вызовы инструментов (tool calling) через реестр registry"""

    conversation: list[dict[str, Any]] = list(messages)
    tool_schemas = registry.schemas()

    for _ in range(max_iterations):
        result = await provider.chat(conversation, model=model, tools=tool_schemas)

        if not result.tool_calls:
            return result.content

        conversation.append(provider.format_assistant_tool_calls(result))

        for call in result.tool_calls:
            tool = registry.get(call.name)

            if tool is None:
                output = f"Ошибка: инструмент '{call.name}' не найден"
            else:
                output = await tool.run(call.arguments)

            conversation.append(provider.format_tool_result(call, output))

    final = await provider.chat(conversation, model=model)
    
    return final.content
