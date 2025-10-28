"""
Gradio web interface for the bottles classifier data collector.
"""

from typing import Dict, Any, Optional
import cv2 as cv
import numpy as np
from datetime import datetime
from loguru import logger

from .collector import specs_and_defaults
from .io_utils import ensure_dataset_dir, save_sample, append_to_class_csv
from .config import AppConfig
from pathlib import Path


class GradioCollectorUI:
    """Gradio-based web UI for data collection."""

    def __init__(
        self,
        pet_spec: str = "states/states_pet.json",
        can_spec: str = "states/states_can.json",
        foreign_spec: str = "states/states_non_target.json",
        output_dir: str = "dataset",
        config: AppConfig = None,
    ):
        self.specs, self.defaults = specs_and_defaults(pet_spec, can_spec, foreign_spec)
        self.output_dir = output_dir
        self.dataset_dir = None
        self.config = config or AppConfig()

        # Camera state
        self.cap: Optional[cv.VideoCapture] = None
        self.current_frame: Optional[np.ndarray] = None

        # UI state
        # Maintain per-class attribute snapshots so switching классов не теряет значения
        self.class_attributes: Dict[str, Dict[str, Any]] = {
            class_name: defaults.copy()
            for class_name, defaults in self.defaults.items()
        }
        self.current_class = (
            "PET"
            if "PET" in self.class_attributes
            else next(iter(self.class_attributes.keys()))
        )
        self.class_attribute_specs: Dict[str, Dict[str, Dict[str, Any]]] = {
            class_name: {attr["name"]: attr for attr in spec["attributes"]}
            for class_name, spec in self.specs.items()
        }

        # Statistics tracking
        self.statistics = {"PET": 0, "CAN": 0, "FOREIGN": 0, "total": 0}

        logger.info("Gradio UI initialized")

    def load_statistics_from_csv(self) -> None:
        """Load statistics from existing CSV files."""
        try:
            root_dir = Path(self.output_dir)
            for class_name in ["PET", "CAN", "FOREIGN"]:
                csv_path = root_dir / f"{class_name.lower()}.csv"
                if csv_path.exists():
                    # Count lines minus header
                    with open(csv_path, "r", encoding=self.config.csv_encoding) as f:
                        line_count = sum(1 for _ in f) - 1  # Subtract header
                        if line_count > 0:
                            self.statistics[class_name] = line_count

            # Update total
            self.statistics["total"] = sum(
                self.statistics[cls] for cls in ["PET", "CAN", "FOREIGN"]
            )

            logger.info(
                f"Loaded statistics: PET={self.statistics['PET']}, "
                f"CAN={self.statistics['CAN']}, FOREIGN={self.statistics['FOREIGN']}"
            )
        except Exception as e:
            logger.warning(f"Could not load statistics from CSV: {e}")

    def setup_camera(self, camera_id: int, width: int, height: int, fps: int) -> bool:
        """Initialize camera with specified parameters."""
        try:
            if self.cap is not None:
                self.cap.release()

            self.cap = cv.VideoCapture(camera_id)
            self.cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv.CAP_PROP_FPS, fps)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return False

            # Create dataset directory
            self.dataset_dir = ensure_dataset_dir(self.output_dir)

            # Load statistics from existing CSV files
            self.load_statistics_from_csv()

            logger.success(
                f"Camera {camera_id} initialized: {width}x{height} @ {fps} FPS"
            )
            logger.success(f"Dataset directory: {self.dataset_dir}")
            return True
        except Exception as e:
            logger.error(f"Error setting up camera: {e}")
            return False

    def get_video_frame(self):
        """Capture and return current video frame."""
        if self.cap is None or not self.cap.isOpened():
            # Return placeholder image
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv.putText(
                placeholder,
                "No camera",
                (200, 240),
                cv.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            return placeholder

        ret, frame = self.cap.read()
        if ret:
            # Store in original BGR format from camera
            self.current_frame = frame
            # Convert BGR to RGB for Gradio display only
            return cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        else:
            # Return last frame converted to RGB
            if self.current_frame is not None:
                return cv.cvtColor(self.current_frame, cv.COLOR_BGR2RGB)
            return np.zeros((480, 640, 3), dtype=np.uint8)

    def update_class(self, selected_class: str) -> None:
        """Update current class."""
        if selected_class not in self.class_attributes:
            self.class_attributes[selected_class] = self.defaults[selected_class].copy()

        self.current_class = selected_class
        logger.info(f"Class changed to: {selected_class}")

    def update_attribute(self, class_name: str, attr_name: str, value: Any) -> None:
        """Update a single attribute value for the provided class."""
        if class_name not in self.class_attributes:
            self.class_attributes[class_name] = self.defaults[class_name].copy()

        self.class_attributes[class_name][attr_name] = value
        logger.debug(f"Attribute updated ({class_name}): {attr_name} = {value}")

    def reset_attributes(self, class_name: Optional[str] = None) -> None:
        """Reset attributes for the specified class (or current class)."""
        target_class = class_name or self.current_class
        self.class_attributes[target_class] = self.defaults[target_class].copy()
        self.current_class = target_class
        logger.info(f"Attributes reset for class: {target_class}")

    def save_current_frame(self) -> str:
        """Save current frame with metadata and auto-export to class CSV."""
        if self.current_frame is None:
            return "❌ Нет данных камеры для сохранения"

        if self.dataset_dir is None:
            return "❌ Рабочая директория не инициализирована"

        try:
            meta = {
                "timestamp": datetime.now().isoformat(),
                "class": self.current_class,
                "attributes": self.class_attributes.get(self.current_class, {}),
                "capture": {
                    "width": int(self.cap.get(cv.CAP_PROP_FRAME_WIDTH)),
                    "height": int(self.cap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                    "fps": self.cap.get(cv.CAP_PROP_FPS),
                },
            }

            # Save image and metadata
            img_path, json_path = save_sample(
                self.dataset_dir, self.current_frame, meta
            )

            # Auto-export to class-specific CSV (pet.csv, can.csv, foreign.csv)
            append_to_class_csv(
                Path(self.output_dir),
                self.current_class,
                img_path.name,
                meta,
                delimiter=self.config.csv_delimiter,
                encoding=self.config.csv_encoding,
            )

            # Update statistics
            self.statistics[self.current_class] += 1
            self.statistics["total"] += 1

            logger.success(
                f"Saved: {img_path.name} + {json_path.name} -> {self.current_class.lower()}.csv"
            )
            return f"✅ Сохранено: {img_path.name}"
        except Exception as e:
            logger.error(f"Error saving frame: {e}")
            return f"❌ Ошибка: {str(e)}"

    def get_statistics(self) -> str:
        """Get formatted statistics for display."""
        stats_text = f"""### 📊 Общая статистика

🔵 **PET:** {self.statistics['PET']}
🟢 **CAN:** {self.statistics['CAN']}
🟡 **FOREIGN:** {self.statistics['FOREIGN']}
"""
        return stats_text

    def cleanup(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            logger.info("Camera released")
