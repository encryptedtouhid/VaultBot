"""Calculator plugin — evaluates simple math expressions using safe AST parsing.

This does NOT use eval(). It parses the expression into an AST and only
evaluates nodes that correspond to numeric constants and basic arithmetic
operators (+, -, *, /, //, %, **). No function calls, imports, or attribute
access are permitted.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

from vaultbot.plugins.base import (
    PluginBase,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginResultStatus,
)

# Safe operators for math — whitelist only
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

# Maximum exponent to prevent DoS (e.g., 10**10000000)
_MAX_POWER = 1000


def _ast_evaluate(node: ast.expr) -> Any:
    """Recursively evaluate an AST node using only whitelisted operators."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _ast_evaluate(node.left)
        right = _ast_evaluate(node.right)
        # Prevent dangerous power operations
        if op_type is ast.Pow and isinstance(right, (int, float)) and right > _MAX_POWER:
            raise ValueError(f"Exponent too large: {right} (max {_MAX_POWER})")
        return _OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _OPERATORS[op_type](_ast_evaluate(node.operand))

    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def safe_math(expr: str) -> float:
    """Safely compute a math expression using AST parsing (no code execution)."""
    tree = ast.parse(expr, mode="eval")  # "eval" mode parses a single expression
    return _ast_evaluate(tree.body)


class CalculatorPlugin(PluginBase):
    """A simple calculator plugin using safe AST-based math parsing."""

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="calculator",
            version="1.0.0",
            description="Compute simple math expressions safely",
            author="zenbot-team",
        )

    async def handle(self, ctx: PluginContext) -> PluginResult:
        expr = ctx.user_input.strip()
        try:
            result = safe_math(expr)
            return PluginResult(
                status=PluginResultStatus.SUCCESS,
                output=f"{expr} = {result}",
                data={"expression": expr, "result": result},
            )
        except (ValueError, ZeroDivisionError, SyntaxError) as e:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=f"Cannot compute '{expr}': {e}",
            )
