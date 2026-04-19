/**
 * ARKiin v2.0 — Frontend TypeScript Types
 * Maintains strict contract parity with backend Pydantic schemas.
 * All types mirror backend/schemas.py exactly.
 */

export interface BehavioralMetrics {
  rating_variance: number;
  mean_rating_time_ms: number;
  decisiveness_score: number;
}

export interface TasteVector {
  embedding: number[];        // Float32Array length 128
  entropy: number;            // Shannon entropy, lower = more decisive
  confidence: number;         // [0, 1] confidence in style profile
  dominant_style_label: string;
  behavioral_metrics: BehavioralMetrics;
  model_version: string;
}

export interface NodeAttribute {
  area?: number;              // m2
  thickness?: number;         // meters
  load_bearing_prob?: number; // [0, 1]
}

export type NodeType = 'ROOM' | 'WALL' | 'DOOR' | 'WINDOW' | 'COLUMN' | 'STAIR';
export type EdgeRelation = 'adjacent' | 'contains' | 'opens_into';

export interface FloorPlanNode {
  id: string;
  type: NodeType;
  geometry: number[][];       // [[x, y], ...]
  attributes: NodeAttribute;
}

export interface FloorPlanEdge {
  source_id: string;
  target_id: string;
  relation: EdgeRelation;
}

export interface FloorPlanGraph {
  nodes: FloorPlanNode[];
  edges: FloorPlanEdge[];
  scale_factor: number;
  structural_confidence: number;
  model_version: string;
}

export interface Placement {
  item_id: string;
  room_id: string;
  position: [number, number, number]; // [x, y, z]
  rotation: [number, number, number]; // [rx, ry, rz] degrees
  clearance_score: number;
}

export interface FurniturePlacementGraph {
  placements: Placement[];
  layout_score: number;
}

export interface BOQItem {
  sku: string;
  description: string;
  unit_cost: number;
  supplier: string;
  carbon_score: number;
  lead_time_days: number;
}

export interface BillOfQuantities {
  items: BOQItem[];
  optimization_score: number;
}

// API Response types
export interface RateImageResponse {
  next_image: CandidateImage;
  entropy: number;
  confidence: number;
  session_id: string;
  discovery_complete: boolean;
}

export interface CandidateImage {
  id: string;
  url: string;
  cluster_id: number;
}

export interface SessionState {
  session_id: string;
  taste_vector: TasteVector | null;
  floor_plan: FloorPlanGraph | null;
  placements: FurniturePlacementGraph | null;
  boq: BillOfQuantities | null;
  current_step: 1 | 2 | 3 | 4 | 5 | 6;
  pipeline_complete: boolean;
}
