"""
Medical AI Workflow Watcher

Monitors medical AI workflow events for training, evaluation, and inference.
Tracks model performance, data processing, and compliance with medical standards.
"""

import asyncio
import logging
from typing import Optional

log = logging.getLogger("watchers.medical_ai")


class MedicalAIWatcher:
    """
    Watches medical AI workflow events including training, evaluation, and inference.
    Ensures compliance with medical data standards (HIPAA, etc.).
    """

    def __init__(self, bus):
        self._bus = bus
        self._task: Optional[asyncio.Task] = None

        # Workflow statistics
        self._training_runs = 0
        self._evaluation_runs = 0
        self._inference_requests = 0
        self._data_processing_events = 0

        # Model performance tracking
        self._model_metrics: dict[str, dict] = {}

        # Compliance tracking
        self._hipaa_violations = 0
        self._data_anonymization_events = 0

    async def start(self) -> None:
        """Start the medical AI watcher."""
        if self._task and not self._task.done():
            return

        # Subscribe to medical AI events
        self._bus.subscribe("medical_training_start", self._on_training_start)
        self._bus.subscribe("medical_training_complete", self._on_training_complete)
        self._bus.subscribe("medical_evaluation", self._on_evaluation)
        self._bus.subscribe("medical_inference", self._on_inference)
        self._bus.subscribe("medical_data_processed", self._on_data_processed)
        self._bus.subscribe("hipaa_check", self._on_hipaa_check)

        log.info("MedicalAIWatcher started")

    async def stop(self) -> None:
        """Stop the medical AI watcher."""
        # Unsubscribe from events
        self._bus.unsubscribe("medical_training_start", self._on_training_start)
        self._bus.unsubscribe("medical_training_complete", self._on_training_complete)
        self._bus.unsubscribe("medical_evaluation", self._on_evaluation)
        self._bus.unsubscribe("medical_inference", self._on_inference)
        self._bus.unsubscribe("medical_data_processed", self._on_data_processed)
        self._bus.unsubscribe("hipaa_check", self._on_hipaa_check)

        log.info("MedicalAIWatcher stopped")

    async def _on_training_start(self, event: dict) -> None:
        """Handle medical training start events."""
        self._training_runs += 1
        model_name = event.get("model", "unknown")
        dataset = event.get("dataset", "unknown")

        log.info("Medical training started: model=%s, dataset=%s", model_name, dataset)

        # Initialize metrics for this model if needed
        if model_name not in self._model_metrics:
            self._model_metrics[model_name] = {
                "training_runs": 0,
                "best_accuracy": 0.0,
                "best_f1": 0.0,
                "training_time_ms": [],
            }

        self._model_metrics[model_name]["training_runs"] += 1

    async def _on_training_complete(self, event: dict) -> None:
        """Handle medical training completion events."""
        model_name = event.get("model", "unknown")
        accuracy = event.get("accuracy", 0.0)
        f1_score = event.get("f1_score", 0.0)
        training_time = event.get("training_time_ms", 0)

        log.info(
            "Medical training complete: model=%s, accuracy=%.2f%%, f1=%.2f",
            model_name,
            accuracy * 100,
            f1_score,
        )

        # Update metrics
        if model_name in self._model_metrics:
            metrics = self._model_metrics[model_name]
            metrics["best_accuracy"] = max(metrics["best_accuracy"], accuracy)
            metrics["best_f1"] = max(metrics["best_f1"], f1_score)
            metrics["training_time_ms"].append(training_time)

            # Keep only last 10 training times
            if len(metrics["training_time_ms"]) > 10:
                metrics["training_time_ms"].pop(0)

    async def _on_evaluation(self, event: dict) -> None:
        """Handle medical model evaluation events."""
        self._evaluation_runs += 1
        model_name = event.get("model", "unknown")
        metrics = event.get("metrics", {})

        log.info("Medical model evaluation: model=%s, metrics=%s", model_name, metrics)

        # Publish evaluation results
        await self._bus.publish("medical_evaluation_complete", {
            "model": model_name,
            "metrics": metrics,
            "timestamp": event.get("ts"),
        })

    async def _on_inference(self, event: dict) -> None:
        """Handle medical inference events."""
        self._inference_requests += 1
        model_name = event.get("model", "unknown")

        log.debug("Medical inference request: model=%s", model_name)

    async def _on_data_processed(self, event: dict) -> None:
        """Handle medical data processing events."""
        self._data_processing_events += 1
        dataset = event.get("dataset", "unknown")
        samples = event.get("samples", 0)
        anonymized = event.get("anonymized", False)

        if anonymized:
            self._data_anonymization_events += 1

        log.info(
            "Medical data processed: dataset=%s, samples=%d, anonymized=%s",
            dataset,
            samples,
            anonymized,
        )

    async def _on_hipaa_check(self, event: dict) -> None:
        """Handle HIPAA compliance check events."""
        compliant = event.get("compliant", True)

        if not compliant:
            self._hipaa_violations += 1
            violation_type = event.get("violation_type", "unknown")
            log.error("HIPAA violation detected: type=%s", violation_type)

            # Publish alert
            await self._bus.publish("medical_compliance_alert", {
                "violation_type": violation_type,
                "severity": "high",
                "details": event.get("details", {}),
            })
        else:
            log.debug("HIPAA compliance check passed")

    def get_model_performance(self, model_name: str) -> Optional[dict]:
        """
        Get performance metrics for a specific medical model.

        Args:
            model_name: Name of the model

        Returns:
            Performance metrics dictionary or None
        """
        return self._model_metrics.get(model_name)

    def get_compliance_summary(self) -> dict:
        """
        Get medical compliance summary.

        Returns:
            Compliance summary dictionary
        """
        total_checks = self._hipaa_violations + self._data_anonymization_events
        compliance_rate = 1.0 - (self._hipaa_violations / total_checks) if total_checks > 0 else 1.0

        return {
            "hipaa_violations": self._hipaa_violations,
            "data_anonymization_events": self._data_anonymization_events,
            "total_compliance_checks": total_checks,
            "compliance_rate": compliance_rate,
        }

    def status(self) -> dict:
        """Get current medical AI watcher status."""
        return {
            "training_runs": self._training_runs,
            "evaluation_runs": self._evaluation_runs,
            "inference_requests": self._inference_requests,
            "data_processing_events": self._data_processing_events,
            "models_tracked": list(self._model_metrics.keys()),
            "compliance": self.get_compliance_summary(),
        }
