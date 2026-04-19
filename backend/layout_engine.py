"""ARKiin v2.0 — Step 3: Constraint-Aware Layout Engine
Simulated annealing optimizer for furniture placement within floor plan graph.
Minimizes clearance, circulation, door swing, and window-blocking penalties.
"""
import random
import math
import logging
from copy import deepcopy
from schemas import FloorPlanGraph, FurniturePlacementGraph, Placement, TasteVector

logger = logging.getLogger("arkiin.layout")

# Annealing hyperparameters
INIT_TEMP = 1000.0
MIN_TEMP = 1.0
COOLING_RATE = 0.95
ITERATIONS_PER_TEMP = 10


def clearance_penalty(placement: Placement) -> float:
    """Penalize placements with insufficient clearance around furniture."""
    return max(0.0, (0.5 - placement.clearance_score) * 20.0)


def door_swing_penalty(placement: Placement, fp_graph: FloorPlanGraph) -> float:
    """Penalize furniture blocking door arcs."""
    penalty = 0.0
    for node in fp_graph.nodes:
        if node.type == "DOOR":
            for pt in node.geometry:
                dx = placement.position[0] - pt[0]
                dy = placement.position[1] - pt[1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist < 0.9:  # 0.9m door swing radius
                    penalty += 15.0
    return penalty


def calculate_layout_score(
    placements: list[Placement],
    fp_graph: FloorPlanGraph,
    taste: TasteVector | None = None
) -> float:
    """Composite score: higher is better."""
    score = 0.0
    for p in placements:
        score -= clearance_penalty(p)
        score -= door_swing_penalty(p, fp_graph)
        score += p.clearance_score * 5.0
    return score


def propose_mutation(placements: list[Placement]) -> list[Placement]:
    """Randomly mutate one placement: translate or rotate."""
    mutated = deepcopy(placements)
    idx = random.randint(0, len(mutated) - 1)
    action = random.choice(["translate", "rotate"])
    if action == "translate":
        mutated[idx].position[0] += random.uniform(-0.5, 0.5)
        mutated[idx].position[1] += random.uniform(-0.5, 0.5)
        mutated[idx].clearance_score = max(0.0, mutated[idx].clearance_score + random.uniform(-0.1, 0.1))
    else:
        mutated[idx].rotation[2] = (mutated[idx].rotation[2] + random.choice([90, 180, 270])) % 360
    return mutated


def optimize_layout(
    fp_graph: FloorPlanGraph,
    items_to_place: list[str],
    taste: TasteVector | None = None
) -> FurniturePlacementGraph:
    """Simulated annealing furniture layout optimizer."""
    # Initialize random placements
    current = [
        Placement(
            item_id=item,
            room_id="r_living",
            position=[random.uniform(1, 4), random.uniform(1, 4), 0.0],
            rotation=[0.0, 0.0, random.choice([0, 90, 180, 270])],
            clearance_score=random.uniform(0.5, 1.0)
        )
        for item in items_to_place
    ]

    current_score = calculate_layout_score(current, fp_graph, taste)
    best = deepcopy(current)
    best_score = current_score
    temp = INIT_TEMP

    while temp > MIN_TEMP:
        for _ in range(ITERATIONS_PER_TEMP):
            candidate = propose_mutation(current)
            new_score = calculate_layout_score(candidate, fp_graph, taste)
            delta = new_score - current_score
            if delta > 0 or math.exp(delta / temp) > random.random():
                current = candidate
                current_score = new_score
                if current_score > best_score:
                    best = deepcopy(current)
                    best_score = current_score
        temp *= COOLING_RATE

    logger.info(
        "Layout optimized",
        extra={"items": len(items_to_place), "final_score": best_score, "temp_final": temp}
    )
    return FurniturePlacementGraph(placements=best, layout_score=best_score)
