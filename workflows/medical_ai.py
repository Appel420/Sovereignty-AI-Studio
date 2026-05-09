"""
Sovereignty AI Studio — Medical AI Workflow.

Provides a self-contained pipeline for training and evaluating a medical
image classification model using the ``medicalai`` library.  The workflow
covers:

1. Dataset download and extraction
2. Numpy-based dataset loading (``datasetFromFolder``)
3. Model selection from the Sovereignty AI model registry
4. Training via ``TRAIN_ENGINE``
5. Evaluation and basic performance reporting
6. Grad-CAM explainability (optional, requires medicalai extras)

The workflow is designed to run standalone or be imported and driven
programmatically from another module.

Usage (CLI)::

    python -m workflows.medical_ai

Usage (programmatic)::

    from workflows.medical_ai import MedicalAIWorkflow

    wf = MedicalAIWorkflow(
        dataset_url="https://example.com/my_dataset.zip",
        model_name="tinyMedNet",
        epochs=10,
    )
    results = wf.run()
    print(results)
"""

from __future__ import annotations

import logging
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Workflow configuration dataclass
# ---------------------------------------------------------------------------

_DEFAULT_DATASET_URL = (
    "https://github.com/aibharata/covid19-dataset/archive/v1.0.zip"
)
_DEFAULT_DATASET_SUBDIR = "dataset"
_DEFAULT_DATASET_INNER = "covid19-dataset-1.0/chest-xray-pnumonia-covid19"


@dataclass
class MedicalAIConfig:
    """Hyperparameters and paths for :class:`MedicalAIWorkflow`."""

    # Dataset
    dataset_url: str = _DEFAULT_DATASET_URL
    dataset_subdir: str = _DEFAULT_DATASET_SUBDIR
    dataset_inner_path: str = _DEFAULT_DATASET_INNER

    # Image dimensions
    img_height: int = 64
    img_width: int = 64

    # Classes (e.g., normal / pneumonia / covid)
    output_classes: int = 3

    # Training hyperparameters
    batch_size: int = 32
    epochs: int = 10
    learning_rate: float = 1e-4

    # Model
    model_name: str = "tinyMedNet"
    model_save_name: str = "sovereignty_medical_model"
    retrain: bool = True
    save_best: bool = True
    show_model_summary: bool = False

    # Paths
    output_dir: str = field(
        default_factory=lambda: str(
            pathlib.Path(__file__).parent.parent / "data" / "medical_ai"
        )
    )


# ---------------------------------------------------------------------------
# Workflow class
# ---------------------------------------------------------------------------

class MedicalAIWorkflow:
    """
    End-to-end medical image classification workflow.

    :param config: A :class:`MedicalAIConfig` instance.  All constructor
                   keyword arguments are forwarded to ``MedicalAIConfig``
                   if *config* is omitted.
    """

    def __init__(
        self,
        config: Optional[MedicalAIConfig] = None,
        **kwargs: Any,
    ) -> None:
        self.config = config or MedicalAIConfig(**kwargs)
        self._medai: Any = None  # lazy import
        os.makedirs(self.config.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        Execute the full training pipeline.

        :returns: A result dict with ``status``, ``accuracy``, ``loss``,
                  and ``model_path`` keys.
        :raises RuntimeError: When the ``medicalai`` package is not installed.
        """
        self._load_medicalai()

        log.info("=== Medical AI Workflow — START ===")
        log.info("Model: %s  |  Epochs: %d  |  Classes: %d",
                 self.config.model_name, self.config.epochs, self.config.output_classes)

        dataset_path = self._download_dataset()
        train_set, test_set, label_names = self._load_dataset(dataset_path)

        log.info(
            "Dataset loaded — train: %s, test: %s, labels: %s",
            train_set.data.shape,
            test_set.data.shape,
            label_names,
        )

        trainer = self._train(train_set, test_set)
        results = self._evaluate(trainer, test_set, label_names)

        log.info("=== Medical AI Workflow — DONE ===")
        log.info("Results: %s", results)
        return results

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def _download_dataset(self) -> str:
        """Download and extract the dataset, returning the folder path."""
        cfg = self.config
        log.info("Downloading dataset from %s", cfg.dataset_url)
        download_root = self._medai.getFile(
            cfg.dataset_url,
            subDir=os.path.join(cfg.output_dir, cfg.dataset_subdir),
        )
        folder = os.path.join(download_root, cfg.dataset_inner_path)
        if not os.path.isdir(folder):
            raise FileNotFoundError(
                f"Expected dataset folder not found after download: {folder}"
            )
        log.info("Dataset ready at: %s", folder)
        return folder

    def _load_dataset(
        self, folder: str
    ) -> Tuple[Any, Any, Any]:
        """Load train/test splits from *folder*."""
        cfg = self.config
        target_dim = (cfg.img_width, cfg.img_height)
        train_set, test_set, label_names = (
            self._medai
            .datasetFromFolder(folder, targetDim=target_dim)
            .load_dataset()
        )
        return train_set, test_set, label_names

    def _train(self, train_set: Any, test_set: Any) -> Any:
        """Run the training loop and return the trainer."""
        cfg = self.config
        trainer = self._medai.TRAIN_ENGINE()

        # Convert raw numpy datasets to generators to avoid memory issues
        train_gen = train_set.as_generator()
        test_gen = test_set.as_generator()

        trainer.train_and_save_model(
            AI_NAME=cfg.model_name,
            MODEL_SAVE_NAME=os.path.join(cfg.output_dir, cfg.model_save_name),
            trainSet=train_gen,
            testSet=test_gen,
            OUTPUT_CLASSES=cfg.output_classes,
            RETRAIN_MODEL=cfg.retrain,
            BATCH_SIZE=cfg.batch_size,
            EPOCHS=cfg.epochs,
            LEARNING_RATE=cfg.learning_rate,
            SAVE_BEST_MODEL=cfg.save_best,
            showModel=cfg.show_model_summary,
        )
        return trainer

    def _evaluate(
        self, trainer: Any, test_set: Any, label_names: Any
    ) -> Dict[str, Any]:
        """Evaluate the trained model and return metrics."""
        results: Dict[str, Any] = {
            "status": "success",
            "model_name": self.config.model_name,
            "model_save_name": self.config.model_save_name,
            "epochs": self.config.epochs,
            "output_classes": self.config.output_classes,
            "label_names": list(label_names) if label_names is not None else [],
        }

        # Attempt to extract final training metrics if available
        try:
            history = getattr(trainer, "history", None)
            if history and hasattr(history, "history"):
                hist = history.history
                accuracy = hist.get("val_accuracy") or hist.get("accuracy") or []
                loss = hist.get("val_loss") or hist.get("loss") or []
                results["accuracy"] = float(accuracy[-1]) if accuracy else None
                results["loss"] = float(loss[-1]) if loss else None
        except Exception as exc:  # noqa: BLE001
            log.debug("Could not extract training history metrics: %s", exc)

        # Optional: Grad-CAM explainability
        try:
            if hasattr(self._medai, "gradcam_explainer"):
                log.info("Running Grad-CAM explainability pass…")
                self._medai.gradcam_explainer(
                    trainer,
                    test_set,
                    label_names=label_names,
                    output_dir=self.config.output_dir,
                )
                results["explainability"] = "gradcam_complete"
        except Exception as exc:  # noqa: BLE001
            log.debug("Grad-CAM explainability skipped: %s", exc)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_medicalai(self) -> None:
        """Lazy-import the ``medicalai`` library; raise if not installed."""
        if self._medai is not None:
            return
        try:
            import medicalai as ai  # noqa: PLC0415

            self._medai = ai
            log.info("medicalai loaded successfully")
        except ImportError as exc:
            raise RuntimeError(
                "The 'medicalai' package is required for MedicalAIWorkflow. "
                "Install it with:  pip install medicalai"
            ) from exc


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the medical AI workflow with default configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    wf = MedicalAIWorkflow()
    results = wf.run()
    print("\nWorkflow results:")
    for k, v in results.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
