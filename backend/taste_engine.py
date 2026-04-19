"""ARKiin v2.0 — Step 1: Adaptive Taste Discovery Engine
Implements Bayesian-like embedding updates and Expected Information Gain
for active learning of user aesthetic preferences.
"""
import numpy as np
import logging
from schemas import TasteVector, BehavioralMetrics

logger = logging.getLogger("arkiin.taste")

MODEL_VERSION = "taste-v1.0"


def update_taste_embedding(
    prior_emb: np.ndarray,
    rating: int,
    img_emb: np.ndarray
) -> np.ndarray:
    """Bayesian-like posterior update in embedding space.
    rating: 1–5 scale, mapped to [0, 1] weight.
    """
    rating_weight = (rating - 1) / 4.0
    posterior = prior_emb + rating_weight * (img_emb - prior_emb)
    norm = np.linalg.norm(posterior)
    return posterior / norm if norm > 0 else posterior


def calculate_entropy(embedding: np.ndarray) -> float:
    """Shannon entropy over normalized embedding magnitude."""
    p = np.abs(embedding)
    total = np.sum(p)
    if total == 0:
        return 1.0
    p = p / total
    return float(-np.sum(p * np.log(p + 1e-10)))


def calculate_decisiveness_score(variance: float, mean_time_ms: float) -> float:
    """Decisiveness: fast + consistent raters score higher."""
    time_factor = max(0.0, 1.0 - mean_time_ms / 10000.0)
    variance_factor = max(0.0, 1.0 - variance / 4.0)
    return float((time_factor + variance_factor) / 2.0)


def expected_information_gain(
    current_emb: np.ndarray,
    candidate_embs: np.ndarray
) -> int:
    """Select the candidate image with maximum Expected Information Gain.
    Simulates all possible ratings (1–5) to estimate entropy reduction.
    Returns index of best candidate.
    """
    best_idx = 0
    max_eig = -float('inf')
    current_entropy = calculate_entropy(current_emb)

    for i, candidate in enumerate(candidate_embs):
        expected_entropy = 0.0
        for r in range(1, 6):
            prob_r = 0.2  # Uniform prior; refine with usage data
            simulated_post = update_taste_embedding(current_emb, r, candidate)
            expected_entropy += prob_r * calculate_entropy(simulated_post)
        eig = current_entropy - expected_entropy
        if eig > max_eig:
            max_eig = eig
            best_idx = i

    logger.info("EIG selection", extra={"best_idx": best_idx, "max_eig": max_eig})
    return best_idx


def build_taste_vector(
    embedding: np.ndarray,
    ratings: list[int],
    response_times_ms: list[float]
) -> TasteVector:
    """Constructs a fully-populated TasteVector from accumulated session data."""
    entropy = calculate_entropy(embedding)
    variance = float(np.var(ratings)) if ratings else 0.0
    mean_time = float(np.mean(response_times_ms)) if response_times_ms else 0.0
    decisiveness = calculate_decisiveness_score(variance, mean_time)
    confidence = max(0.0, 1.0 - entropy / np.log(len(embedding) + 1e-10))

    return TasteVector(
        embedding=embedding.tolist(),
        entropy=entropy,
        confidence=confidence,
        dominant_style_label="pending_gemini_summary",
        behavioral_metrics=BehavioralMetrics(
            rating_variance=variance,
            mean_rating_time_ms=mean_time,
            decisiveness_score=decisiveness
        ),
        model_version=MODEL_VERSION
    )


def summarize_style_with_gemini(taste_vector: TasteVector) -> dict:
    """Calls Gemini 1.5 Pro to generate structured style summary JSON."""
    from vertexai.generative_models import GenerativeModel
    model = GenerativeModel("gemini-1.5-pro")
    prompt = (
        f"User aesthetic profile: entropy={taste_vector.entropy:.3f}, "
        f"confidence={taste_vector.confidence:.3f}. "
        "Output strict JSON: {dominant_style_label, descriptive_summary, "
        "complementary_style_axes, confidence}"
    )
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    return response.text
