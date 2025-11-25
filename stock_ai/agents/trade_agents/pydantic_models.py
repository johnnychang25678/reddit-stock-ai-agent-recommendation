"""Pydantic models for TradeAgent."""

from pydantic import BaseModel, Field
from typing import Literal


class TradeDecision(BaseModel):
    """A single trade decision made by the agent."""
    ticker: str = Field(..., description="Stock ticker symbol")
    action: Literal["BUY", "SELL", "HOLD"] = Field(..., description="Trading action")
    quantity: int = Field(..., ge=0, description="Number of shares (0 for HOLD)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reasoning for this decision")


class TradeDecisions(BaseModel):
    """List of trade decisions."""
    decisions: list[TradeDecision] = Field(..., min_length=0, description="All trade decisions for this run")
