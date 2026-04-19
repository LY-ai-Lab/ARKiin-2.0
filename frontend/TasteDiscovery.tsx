/**
 * ARKiin v2.0 — Step 1: Adaptive Taste Discovery Component
 * Displays style images for rating. On each rating, calls backend API
 * which updates TasteVector via Bayesian-EIG active learning.
 * Discovery ends when entropy drops below threshold.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { TasteVector, CandidateImage, RateImageResponse } from './types';

const API_BASE = import.meta.env.VITE_API_URL ?? 'https://api.arkiin.com';

interface Props {
  sessionId: string;
  onComplete: (taste: TasteVector) => void;
}

const RATING_LABELS: Record<number, string> = {
  1: 'Dislike',
  2: 'Neutral-',
  3: 'Neutral',
  4: 'Like',
  5: 'Love',
};

export const TasteDiscovery: React.FC<Props> = ({ sessionId, onComplete }) => {
  const [currentImage, setCurrentImage] = useState<CandidateImage | null>(null);
  const [entropy, setEntropy] = useState<number>(1.0);
  const [confidence, setConfidence] = useState<number>(0.0);
  const [ratingCount, setRatingCount] = useState<number>(0);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFirstImage = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/taste/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data: { image: CandidateImage } = await res.json();
      setCurrentImage(data.image);
      setStartTime(Date.now());
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => { fetchFirstImage(); }, [fetchFirstImage]);

  const handleRating = async (rating: number) => {
    if (!currentImage || isLoading) return;
    const ratingTimeMs = Date.now() - startTime;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/taste/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          image_id: currentImage.id,
          rating,
          rating_time_ms: ratingTimeMs,
        }),
      });
      if (!res.ok) throw new Error(`Rating API error: ${res.status}`);
      const data: RateImageResponse = await res.json();
      setEntropy(data.entropy);
      setConfidence(data.confidence);
      setRatingCount((c) => c + 1);
      if (data.discovery_complete) {
        // Fetch final TasteVector
        const tvRes = await fetch(`${API_BASE}/api/taste/vector/${sessionId}`);
        const tv: TasteVector = await tvRes.json();
        onComplete(tv);
      } else {
        setCurrentImage(data.next_image);
        setStartTime(Date.now());
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  };

  const entropyPct = Math.round((1 - entropy) * 100);

  return (
    <div className="flex flex-col items-center gap-6 p-8 max-w-2xl mx-auto">
      <h2 className="text-2xl font-semibold text-neutral-900">Taste Discovery</h2>
      {/* Progress */}
      <div className="w-full">
        <div className="flex justify-between text-sm text-neutral-500 mb-1">
          <span>Aesthetic Clarity</span>
          <span>{entropyPct}% defined</span>
        </div>
        <div className="w-full bg-neutral-200 rounded-full h-2">
          <div
            className="bg-amber-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${entropyPct}%` }}
          />
        </div>
        <p className="text-xs text-neutral-400 mt-1">
          Images rated: {ratingCount} • Confidence: {(confidence * 100).toFixed(0)}%
        </p>
      </div>
      {/* Image */}
      {isLoading && !currentImage && (
        <div className="w-full h-80 bg-neutral-100 animate-pulse rounded-xl" />
      )}
      {currentImage && (
        <div className="relative w-full">
          <img
            src={currentImage.url}
            alt="Style evaluation"
            className="w-full h-80 object-cover rounded-xl shadow-md"
            loading="eager"
          />
          {isLoading && (
            <div className="absolute inset-0 bg-white/50 rounded-xl flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      )}
      {/* Rating Buttons */}
      {currentImage && (
        <div className="flex gap-3">
          {[1, 2, 3, 4, 5].map((r) => (
            <button
              key={r}
              onClick={() => handleRating(r)}
              disabled={isLoading}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${ r <= 2 ? 'bg-neutral-100 hover:bg-neutral-200 text-neutral-700'
                  : r === 3 ? 'bg-amber-50 hover:bg-amber-100 text-amber-800'
                  : 'bg-amber-500 hover:bg-amber-600 text-white'
                } disabled:opacity-40`}
            >
              {RATING_LABELS[r]}
            </button>
          ))}
        </div>
      )}
      {error && (
        <p className="text-red-500 text-sm">{error}</p>
      )}
    </div>
  );
};
