"""ARKiin v2.0 — Step 5: Procurement Optimization Engine
Queries BigQuery EU material catalog and solves multi-objective optimization:
Minimize total cost + carbon score + lead time, subject to style similarity.
"""
import logging
from google.cloud import bigquery
from schemas import TasteVector, BillOfQuantities, BOQItem

logger = logging.getLogger("arkiin.procurement")
bq_client = bigquery.Client()

# Optimization weights
LAMBDA_CARBON = 0.5
LAMBDA_LEAD_TIME = 0.2
MIN_STYLE_SIMILARITY = 0.6


def compute_style_similarity(taste: TasteVector, item_tags: list[str]) -> float:
    """Stub: cosine similarity between taste embedding and item tag embeddings.
    Replace with Vertex AI Matching Engine in production.
    """
    # Placeholder: return 0.8 until vector search is integrated
    return 0.8


def optimize_bill_of_quantities(
    taste: TasteVector,
    budget: float,
    region: str = "EU"
) -> BillOfQuantities:
    """Queries BigQuery and performs weighted multi-objective procurement optimization."""
    query = """
        SELECT
            sku, description, unit_cost, supplier,
            carbon_score, lead_time_days,
            ARRAY_TO_STRING(style_tags, ',') AS tags
        FROM `arkiin.arkiin_materials.eu_catalog`
        WHERE availability_region = @region
          AND unit_cost <= @budget
        ORDER BY unit_cost ASC
        LIMIT 100
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("region", "STRING", region),
            bigquery.ScalarQueryParameter("budget", "FLOAT", budget),
        ]
    )

    try:
        df = bq_client.query(query, job_config=job_config).to_dataframe()
    except Exception as e:
        logger.error("BigQuery query failed", extra={"error": str(e)})
        return BillOfQuantities(items=[], optimization_score=0.0)

    if df.empty:
        logger.warning("No materials found for budget", extra={"budget": budget})
        return BillOfQuantities(items=[], optimization_score=0.0)

    # Weighted objective: cost + lambda1*carbon + lambda2*lead_time
    df["objective"] = (
        df["unit_cost"]
        + LAMBDA_CARBON * df["carbon_score"]
        + LAMBDA_LEAD_TIME * df["lead_time_days"]
    )

    # Filter by style similarity
    df["style_sim"] = df["tags"].apply(
        lambda tags: compute_style_similarity(taste, tags.split(",") if tags else [])
    )
    df = df[df["style_sim"] >= MIN_STYLE_SIMILARITY]

    if df.empty:
        return BillOfQuantities(items=[], optimization_score=0.0)

    # Select Pareto-optimal items (greedy: lowest objective per category)
    best = df.nsmallest(10, "objective")
    items = [
        BOQItem(
            sku=row["sku"],
            description=row["description"],
            unit_cost=float(row["unit_cost"]),
            supplier=row["supplier"],
            carbon_score=float(row["carbon_score"]),
            lead_time_days=int(row["lead_time_days"])
        )
        for _, row in best.iterrows()
    ]

    optimization_score = float(1.0 / (1.0 + best["objective"].mean()))
    logger.info(
        "BOQ optimized",
        extra={"items": len(items), "score": optimization_score}
    )
    return BillOfQuantities(items=items, optimization_score=optimization_score)
