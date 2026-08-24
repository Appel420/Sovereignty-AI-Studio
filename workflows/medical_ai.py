"""
Sovereignty AI Studio — Medical AI Workflow.

Provides a self-contained pipeline for training and evaluating a medical
image classification model using the ``medicalai`` library.
"""

from __future__ import annotations

import importlib
import logging
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger(__name__)

_DEFAULT_DATASET_URL = "https://github.com/aibharata/covid19-dataset/archive/v1.0.zip"
_DEFAULT_DATASET_SUBDIR = "dataset"
_DEFAULT_DATASET_INNER = "covid19-dataset-1.0/chest-xray-pneumonia-covid19"


@dataclass
class MedicalAIConfig:
    """Hyperparameters and paths for :class:`MedicalAIWorkflow`."""

    dataset_url: str = _DEFAULT_DATASET_URL
    dataset_subdir: str = _DEFAULT_DATASET_SUBDIR
    dataset_inner_path: str = _DEFAULT_DATASET_INNER
    img_height: int = 64
    img_width: int = 64
    output_classes: int = 3
    batch_size: int = 32
    epochs: int = 10
    learning_rate: float = 1e-4
    model_name: str = "tinyMedNet"
    model_save_name: str = "sovereignty_medical_model"
    retrain: bool = True
    save_best: bool = True
    show_model_summary: bool = False
    output_dir: str = field(
        default_factory=lambda: str(
            pathlib.Path(__file__).parent.parent / "data" / "medical_ai"
        )
    )


class MedicalAIWorkflow:
    """End-to-end medical image classification workflow."""

    def __init__(self, config: Optional[MedicalAIConfig] = None, **kwargs: Any) -> None:
        self.config = config or MedicalAIConfig(**kwargs)
        self._medai: Any = None
        os.makedirs(self.config.output_dir, exist_ok=True)

    def validate(self) -> None:
        """Validate configuration before loading optional runtime dependencies."""
        cfg = self.config
        if cfg.img_height <= 0 or cfg.img_width <= 0:
            raise ValueError("image dimensions must be positive")
        if cfg.output_classes <= 0:
            raise ValueError("output_classes must be positive")
        if cfg.batch_size <= 0 or cfg.epochs <= 0:
            raise ValueError("batch_size and epochs must be positive")
        if cfg.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if not cfg.model_name.strip() or not cfg.model_save_name.strip():
            raise ValueError("model names must not be empty")

    def run(self) -> Dict[str, Any]:
        """Execute the full training pipeline and return evaluation results."""
        self.validate()
        self._load_medicalai()
        log.info("=== Medical AI Workflow — START ===")
        log.info(
            "Model: %s | Epochs: %d | Classes: %d",
            self.config.model_name,
            self.config.epochs,
            self.config.output_classes,
        )
        dataset_path = self._download_dataset()
        train_set, test_set, label_names = self._load_dataset(dataset_path)
        trainer = self._train(train_set, test_set)
        results = self._evaluate(trainer, test_set, label_names)
        log.info("=== Medical AI Workflow — DONE ===")
        return results

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
        return folder

    def _load_dataset(self, folder: str) -> Tuple[Any, Any, Any]:
        """Load train/test splits from *folder*."""
        target_dim = (self.config.img_width, self.config.img_height)
        train_set, test_set, label_names = (
            self._medai.datasetFromFolder(folder, targetDim=target_dim).load_dataset()
        )
        return train_set, test_set, label_names

    def _train(self, train_set: Any, test_set: Any) -> Any:
        """Run the training loop and return the trainer."""
        cfg = self.config
        trainer = self._medai.TRAIN_ENGINE()
        train_input = train_set.as_generator() if hasattr(train_set, "as_generator") else train_set
        test_input = test_set.as_generator() if hasattr(test_set, "as_generator") else test_set
        trainer.train_and_save_model(
            AI_NAME=cfg.model_name,
            MODEL_SAVE_NAME=os.path.join(cfg.output_dir, cfg.model_save_name),
            trainSet=train_input,
            testSet=test_input,
            OUTPUT_CLASSES=cfg.output_classes,
            RETRAIN_MODEL=cfg.retrain,
            BATCH_SIZE=cfg.batch_size,
            EPOCHS=cfg.epochs,
            LEARNING_RATE=cfg.learning_rate,
            SAVE_BEST_MODEL=cfg.save_best,
            showModel=cfg.show_model_summary,
        )
        return trainer

    def _evaluate(self, trainer: Any, test_set: Any, label_names: Any) -> Dict[str, Any]:
        """Evaluate the trained model and return metrics."""
        results: Dict[str, Any] = {
            "status": "success",
            "model_name": self.config.model_name,
            "model_save_name": self.config.model_save_name,
            "epochs": self.config.epochs,
            "output_classes": self.config.output_classes,
            "label_names": list(label_names) if label_names is not None else [],
        }
        try:
            history = getattr(trainer, "history", None)
            if history and hasattr(history, "history"):
                hist = history.history
                accuracy = hist.get("val_accuracy") or hist.get("accuracy") or []
                loss = hist.get("val_loss") or hist.get("loss") or []
                results["accuracy"] = float(accuracy[-1]) if accuracy else None
                results["loss"] = float(loss[-1]) if loss else None
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            log.debug("Could not extract training history metrics: %s", exc)

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
        except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            log.debug("Grad-CAM explainability skipped: %s", exc)
        return results

    def _load_medicalai(self) -> None:
        """Load the optional ``medicalai`` library or raise a clear error."""
        if self._medai is not None:
            return
        try:
            self._medai = importlib.import_module("medicalai")
            log.info("medicalai loaded successfully")
        except ImportError as exc:
            raise RuntimeError(
                "The 'medicalai' package is required for MedicalAIWorkflow. "
                "Install it with: pip install medicalai"
            ) from exc


def main() -> None:
    """Run the medical AI workflow with default configuration."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    workflow = MedicalAIWorkflow()
    results = workflow.run()
    print("\nWorkflow results:")
    for key, value in results.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
