"""
services/metrics.py
Telemetry and performance metrics collection.
"""

import logging
from typing import Dict, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects performance metrics for AI requests and general operations."""

    def __init__(self):
        self.ai_requests: int = 0
        self.ai_errors: int = 0
        self.ai_timeouts: int = 0
        self.ai_latencies: List[float] = []
        self.groq_requests: int = 0
        self.gemini_requests: int = 0
        self.groq_errors: int = 0
        self.gemini_errors: int = 0
        self.last_reset = datetime.now(timezone.utc)

    def record_ai_request(self, latency_ms: float, provider: str = "unknown"):
        """Record an AI request with latency."""
        self.ai_requests += 1
        self.ai_latencies.append(latency_ms)
        
        if provider == "groq":
            self.groq_requests += 1
        elif provider == "gemini":
            self.gemini_requests += 1
        
        # Keep only last 100 latencies to avoid memory bloat
        if len(self.ai_latencies) > 100:
            self.ai_latencies = self.ai_latencies[-100:]

    def record_ai_error(self, provider: str = "unknown"):
        """Record an AI request error."""
        self.ai_errors += 1
        if provider == "groq":
            self.groq_errors += 1
        elif provider == "gemini":
            self.gemini_errors += 1

    def record_ai_timeout(self):
        """Record an AI request timeout."""
        self.ai_timeouts += 1
        self.ai_errors += 1

    def get_stats(self) -> Dict:
        """Get current statistics."""
        if self.ai_latencies:
            avg_latency = sum(self.ai_latencies) / len(self.ai_latencies)
            min_latency = min(self.ai_latencies)
            max_latency = max(self.ai_latencies)
        else:
            avg_latency = min_latency = max_latency = 0

        error_rate = (
            self.ai_errors / max(self.ai_requests, 1) * 100
        )
        groq_success_rate = (
            (self.groq_requests - self.groq_errors) / max(self.groq_requests, 1) * 100
        )
        gemini_success_rate = (
            (self.gemini_requests - self.gemini_errors) / max(self.gemini_requests, 1) * 100
        )

        return {
            "total_ai_requests": self.ai_requests,
            "ai_errors": self.ai_errors,
            "ai_timeouts": self.ai_timeouts,
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "groq_requests": self.groq_requests,
            "groq_errors": self.groq_errors,
            "groq_success_rate_percent": round(groq_success_rate, 2),
            "gemini_requests": self.gemini_requests,
            "gemini_errors": self.gemini_errors,
            "gemini_success_rate_percent": round(gemini_success_rate, 2),
            "uptime_since": self.last_reset.isoformat(),
        }

    def reset(self):
        """Reset all metrics."""
        self.ai_requests = 0
        self.ai_errors = 0
        self.ai_timeouts = 0
        self.ai_latencies = []
        self.groq_requests = 0
        self.gemini_requests = 0
        self.groq_errors = 0
        self.gemini_errors = 0
        self.last_reset = datetime.now(timezone.utc)
        logger.info("Metrics reset")


# Global metrics instance
metrics = MetricsCollector()
