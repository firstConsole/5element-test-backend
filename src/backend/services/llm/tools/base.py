from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Инструмент, который LLM может вызвать через tool calling"""

    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> str:
        """Выполнить инструмент и вернуть результат строкой (чтобы LLM могла его прочитать)"""

    def to_schema(self) -> dict[str, Any]:
        """Описание инструмента в формате function-calling"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Реестр доступных инструментов"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]
