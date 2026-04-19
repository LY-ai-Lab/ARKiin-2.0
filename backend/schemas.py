"""ARKiin v2.0 — Core Pydantic Schemas
Defines all global data structures shared across backend services.
All schemas produce/consume strict structured JSON.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class BehavioralMetrics(BaseModel):
    rating_variance: float
    mean_rating_time_ms: float
    decisiveness_score: float


class TasteVector(BaseModel):
    """User aesthetic latent embedding — output of Step 1."""
    embedding: List[float] = Field(..., min_length=128, max_length=128)
    entropy: float
    confidence: float
    dominant_style_label: str
    behavioral_metrics: BehavioralMetrics
    model_version: str


class NodeAttribute(BaseModel):
    area: Optional[float] = None
    thickness: Optional[float] = None
    load_bearing_prob: Optional[float] = None


class FloorPlanNode(BaseModel):
    id: str
    type: Literal["ROOM", "WALL", "DOOR", "WINDOW", "COLUMN", "STAIR"]
    geometry: List[List[float]]  # Polygons or lines as [x, y] pairs
    attributes: NodeAttribute


class FloorPlanEdge(BaseModel):
    source_id: str
    target_id: str
    relation: Literal["adjacent", "contains", "opens_into"]


class FloorPlanGraph(BaseModel):
    """Structured spatial graph — output of Step 2."""
    nodes: List[FloorPlanNode]
    edges: List[FloorPlanEdge]
    scale_factor: float
    structural_confidence: float
    model_version: str


class Placement(BaseModel):
    item_id: str
    room_id: str
    position: List[float]  # [x, y, z]
    rotation: List[float]  # [rx, ry, rz] in degrees
    clearance_score: float


class FurniturePlacementGraph(BaseModel):
    """Optimized furniture layout — output of Step 3."""
    placements: List[Placement]
    layout_score: float


class BOQItem(BaseModel):
    sku: str
    description: str
    unit_cost: float
    supplier: str
    carbon_score: float
    lead_time_days: int


class BillOfQuantities(BaseModel):
    """Multi-objective optimized procurement — output of Step 5."""
    items: List[BOQItem]
    optimization_score: float


class StepCompletedEvent(BaseModel):
    """Pub/Sub event published after each step completion."""
    event_type: Literal["STEP_COMPLETED"] = "STEP_COMPLETED"
    step_id: str
    session_id: str
    payload: dict = {}
