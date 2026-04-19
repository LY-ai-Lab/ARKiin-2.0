"""ARKiin v2.0 — Cloud Run FastAPI Orchestrator
Handles Pub/Sub event pushes for all 6 pipeline steps.
Structured logging to Cloud Logging. Stateless per request.
"""
import base64
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import logging as cloud_logging, firestore

from schemas import TasteVector, StepCompletedEvent
from taste_engine import update_taste_embedding, expected_information_gain
from layout_engine import optimize_layout
from procurement_engine import optimize_bill_of_quantities

import numpy as np

# Setup Cloud Logging
cl_client = cloud_logging.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "arkiin"))
cl_client.setup_logging()
logger = logging.getLogger("arkiin.orchestrator")

db = firestore.Client()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ARKiin API starting", extra={"version": "2.0"})
    yield
    logger.info("ARKiin API shutting down")


app = FastAPI(title="ARKiin v2.0 Orchestrator", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://arkiin.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def decode_pubsub(envelope: dict) -> dict:
    """Decode base64-encoded Pub/Sub message data."""
    try:
        data = envelope["message"]["data"]
        return json.loads(base64.b64decode(data).decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Pub/Sub envelope: {e}")


def publish_step_completed(step_id: str, session_id: str, payload: dict = {}):
    """Writes step completion event to Firestore (triggers next step via Pub/Sub)."""
    event = StepCompletedEvent(
        step_id=step_id, session_id=session_id, payload=payload
    )
    db.collection("events").add(event.model_dump())
    logger.info("Step completed", extra={"step_id": step_id, "session_id": session_id})


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/events/taste_updated")
async def handle_taste_updated(request: Request):
    """Step 1: User rated an image — update taste embedding."""
    msg = decode_pubsub(await request.json())
    session_id = msg["session_id"]
    image_embedding = np.array(msg["image_embedding"], dtype=float)
    rating = int(msg["rating"])

    # Load prior from Firestore
    doc = db.collection("sessions").document(session_id).get()
    prior_emb = np.array(doc.to_dict().get("embedding", [0.0] * 128), dtype=float)

    # Update embedding
    posterior = update_taste_embedding(prior_emb, rating, image_embedding)
    db.collection("sessions").document(session_id).set(
        {"embedding": posterior.tolist()}, merge=True
    )

    publish_step_completed("taste_updated", session_id)
    logger.info("Taste updated", extra={"session_id": session_id, "rating": rating})
    return {"status": "ok"}


@app.post("/events/spatial_analyzed")
async def handle_spatial_analyzed(request: Request):
    """Step 2: Floor plan analyzed — trigger layout optimization."""
    msg = decode_pubsub(await request.json())
    session_id = msg["session_id"]
    publish_step_completed("spatial_analyzed", session_id)
    logger.info("Spatial analyzed", extra={"session_id": session_id})
    return {"status": "ok"}


@app.post("/events/layout_generated")
async def handle_layout_generated(request: Request):
    """Step 3: Layout optimized — store FurniturePlacementGraph."""
    msg = decode_pubsub(await request.json())
    session_id = msg["session_id"]
    publish_step_completed("layout_generated", session_id)
    logger.info("Layout generated", extra={"session_id": session_id})
    return {"status": "ok"}


@app.post("/events/render_generated")
async def handle_render_generated(request: Request):
    """Step 4: Imagen render complete."""
    msg = decode_pubsub(await request.json())
    session_id = msg["session_id"]
    publish_step_completed("render_generated", session_id)
    return {"status": "ok"}


@app.post("/events/procurement_optimized")
async def handle_procurement_optimized(request: Request):
    """Step 5: BOQ optimization complete."""
    msg = decode_pubsub(await request.json())
    session_id = msg["session_id"]
    publish_step_completed("procurement_optimized", session_id)
    return {"status": "ok"}


@app.post("/events/pack_generated")
async def handle_pack_generated(request: Request):
    """Step 6: Contractor PDF pack generated — pipeline complete."""
    msg = decode_pubsub(await request.json())
    session_id = msg["session_id"]
    logger.info("Pipeline complete", extra={"session_id": session_id})
    return {"status": "ok", "pipeline": "complete"}
