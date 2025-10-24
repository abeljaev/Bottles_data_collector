"""
Gradio web interface for the bottles classifier data collector.
"""
from typing import Dict, Any, List, Tuple, Optional
import cv2 as cv
import numpy as np
import gradio as gr
from datetime import datetime
from loguru import logger

from .collector import specs_and_defaults, AppState
from .io_utils import ensure_date_dir, save_sample, append_to_csv
from .export import export_all_sessions_to_csv
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
        config: AppConfig = None
    ):
        self.specs, self.defaults = specs_and_defaults(pet_spec, can_spec, foreign_spec)
        self.output_dir = output_dir
        self.date_dir = None
        self.export_dir = Path("export_data")  # Fixed export directory
        self.config = config or AppConfig()

        # Camera state
        self.cap: Optional[cv.VideoCapture] = None
        self.current_frame: Optional[np.ndarray] = None

        # UI state
        self.current_class = "PET"
        self.attributes = self.defaults["PET"].copy()

        # Statistics tracking
        self.statistics = {
            "PET": 0,
            "CAN": 0,
            "FOREIGN": 0,
            "total": 0
        }

        logger.info("Gradio UI initialized")

    def setup_camera(self, camera_id: int, width: int, height: int, fps: int) -> bool:
        """Initialize camera with specified parameters."""
        try:
            if self.cap is not None:
                self.cap.release()

            self.cap = cv.VideoCapture(camera_id)
            self.cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv.CAP_PROP_FPS, fps)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return False

            # Create date directory
            self.date_dir = ensure_date_dir(self.output_dir)
            logger.success(f"Camera {camera_id} initialized: {width}x{height} @ {fps} FPS")
            logger.success(f"Date directory: {self.date_dir}")
            return True
        except Exception as e:
            logger.error(f"Error setting up camera: {e}")
            return False

    def get_video_frame(self):
        """Capture and return current video frame."""
        if self.cap is None or not self.cap.isOpened():
            # Return placeholder image
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv.putText(placeholder, "No camera", (200, 240),
                      cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
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

    def update_class(self, selected_class: str):
        """Update current class and reset attributes."""
        self.current_class = selected_class
        self.attributes = self.defaults[selected_class].copy()
        logger.info(f"Class changed to: {selected_class}")

        # Return updated widgets for the new class
        return self.build_attribute_widgets()

    def update_attribute(self, attr_name: str, value: Any):
        """Update a single attribute value."""
        self.attributes[attr_name] = value
        logger.debug(f"Attribute updated: {attr_name} = {value}")

    def save_current_frame(self) -> str:
        """Save current frame with metadata and auto-export to CSV."""
        if self.current_frame is None:
            return "❌ No frame to save"

        if self.date_dir is None:
            return "❌ Date directory not initialized"

        try:
            meta = {
                "timestamp": datetime.now().isoformat(),
                "class": self.current_class,
                "attributes": self.attributes,
                "user_assert_one_object": True,
                "capture": {
                    "width": int(self.cap.get(cv.CAP_PROP_FRAME_WIDTH)),
                    "height": int(self.cap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                    "fps": self.cap.get(cv.CAP_PROP_FPS),
                },
                "date_dir": str(self.date_dir),
            }

            # Save image and metadata
            img_path, json_path = save_sample(self.date_dir, self.current_frame, meta)

            # Auto-export to CSV
            append_to_csv(
                self.export_dir,
                img_path.name,
                meta,
                delimiter=self.config.csv_delimiter,
                encoding=self.config.csv_encoding
            )

            # Update statistics
            self.statistics[self.current_class] += 1
            self.statistics["total"] += 1

            logger.success(f"Saved: {img_path.name} + {json_path.name}")
            return f"✅ Saved: {img_path.name}"
        except Exception as e:
            logger.error(f"Error saving frame: {e}")
            return f"❌ Error: {str(e)}"

    def get_statistics(self) -> str:
        """Get formatted statistics for display."""
        stats_text = f"""### 📊 Статистика сохранений

**По классам:**
- 🔵 PET: {self.statistics['PET']}
- 🟢 CAN: {self.statistics['CAN']}
- 🟡 FOREIGN: {self.statistics['FOREIGN']}

**Всего кадров:** {self.statistics['total']}
"""
        return stats_text

    def export_all_data_csv(self) -> str:
        """Export all data from dataset to a single CSV file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = self.export_dir / f"full_export_{timestamp}.csv"

            success = export_all_sessions_to_csv(
                Path(self.output_dir),
                csv_file,
                delimiter=self.config.csv_delimiter,
                encoding=self.config.csv_encoding,
                include_timestamp=self.config.csv_include_timestamp
            )

            if success:
                return f"✅ Полный экспорт: {csv_file.name}"
            else:
                return "❌ Ошибка экспорта"

        except Exception as e:
            logger.error(f"Full CSV export error: {e}")
            return f"❌ Ошибка: {str(e)}"

    def build_attribute_widgets(self) -> List[gr.Component]:
        """Build Gradio widgets for current class attributes."""
        spec = self.specs[self.current_class]
        widgets = []

        for attr in spec["attributes"]:
            attr_name = attr["name"]
            attr_label = attr.get("label", attr_name)
            attr_type = attr["type"]

            if attr_type == "enum":
                widget = gr.Radio(
                    choices=attr["options"],
                    value=self.attributes.get(attr_name, attr.get("default", attr["options"][0])),
                    label=attr_label,
                    interactive=True
                )
            elif attr_type == "bool":
                widget = gr.Checkbox(
                    value=self.attributes.get(attr_name, attr.get("default", False)),
                    label=attr_label,
                    interactive=True
                )
            elif attr_type == "text":
                widget = gr.Textbox(
                    value=self.attributes.get(attr_name, attr.get("default", "")),
                    label=attr_label,
                    interactive=True,
                    placeholder="Введите текст..."
                )
            else:
                continue

            widgets.append(widget)

        return widgets

    def cleanup(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            logger.info("Camera released")
