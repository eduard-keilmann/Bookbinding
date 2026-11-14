"""Arrange PDF pages into folded signatures for bookbinding."""

from .layout import ImpositionPlan, SheetSide, Signature, make_plan

__all__ = ["ImpositionPlan", "SheetSide", "Signature", "make_plan"]
