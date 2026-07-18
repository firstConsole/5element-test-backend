from __future__ import annotations

import ast
import operator
from datetime import UTC, datetime
from typing import Any

from backend.services.llm.tools.base import Tool, ToolRegistry

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    """Рекурсивно вычислить арифметическое выражение без eval()."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.operand))
    
    raise ValueError("Недопустимое выражение")


class CurrentTimeTool(Tool):
    """Демо-инструмент: текущее время (без внешних зависимостей)"""

    name = "get_current_time"
    description = "Вернуть текущие дату и время в UTC (ISO 8601)."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def run(self, arguments: dict[str, Any]) -> str:
        return datetime.now(UTC).isoformat()


class CalculateTool(Tool):
    """Демо-инструмент: безопасный калькулятор арифметики."""

    name = "calculate"
    description = "Вычислить арифметическое выражение, например '2 + 2 * 10'."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Арифметическое выражение, напр. '(3 + 4) * 2'",
            }
        },
        "required": ["expression"],
    }

    async def run(self, arguments: dict[str, Any]) -> str:
        expression = str(arguments.get("expression", "")).strip()
        try:
            result = _safe_eval(ast.parse(expression, mode="eval"))
        except (ValueError, SyntaxError, TypeError, ZeroDivisionError) as exc:
            return f"Ошибка вычисления: {exc}"
        return str(result)


def default_registry() -> ToolRegistry:
    """Реестр с демо-инструментами по умолчанию."""
    registry = ToolRegistry()
    registry.register(CurrentTimeTool())
    registry.register(CalculateTool())
    return registry
