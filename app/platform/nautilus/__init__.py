"""Nautilus: the tool-calling agent loop for AI Software Factory agents.

Design adapted from goose (https://github.com/aaif-goose/goose, Apache-2.0): a reply loop
with tool calls, permission judging, repetition detection, large-output offloading,
context compaction, and recipes with retry-until-checks-pass. See
docs/architecture/nautilus.md.
"""
from app.platform.nautilus.loop import AgentLoop, AgentLoopConfig, AgentRunResult, ToolCallRecord
from app.platform.nautilus.messages import ChatTurn, ToolCall
from app.platform.nautilus.permissions import PermissionPolicy, command_is_read_only
from app.platform.nautilus.recipe import Recipe, RecipeError, load_recipe, recipe_from_dict
from app.platform.nautilus.recipe_runner import RecipeRunResult, run_recipe
from app.platform.nautilus.tools import Tool, ToolRegistry

__all__ = [
    "AgentLoop", "AgentLoopConfig", "AgentRunResult", "ChatTurn", "PermissionPolicy", "Recipe",
    "RecipeError", "RecipeRunResult", "Tool", "ToolCall", "ToolCallRecord", "ToolRegistry",
    "command_is_read_only", "load_recipe", "recipe_from_dict", "run_recipe",
]
