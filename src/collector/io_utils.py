import json
import pathlib
import csv
from datetime import datetime
import cv2 as cv
from typing import Tuple, Dict, Any
from loguru import logger


def ensure_date_dir(root="dataset") -> pathlib.Path:
    """Create date-based directory structure without sessions."""
    today = datetime.now().strftime("%Y%m%d")
    date_dir = pathlib.Path(root) / today
    (date_dir / "images").mkdir(parents=True, exist_ok=True)
    (date_dir / "meta").mkdir(parents=True, exist_ok=True)
    return date_dir


def save_sample(
    date_dir: pathlib.Path, frame_bgr, meta: Dict[str, Any]
) -> Tuple[pathlib.Path, pathlib.Path]:
    """Save image and metadata to date directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    img_path = date_dir / "images" / f"{ts}.jpg"
    json_path = date_dir / "meta" / f"{ts}.json"
    cv.imwrite(str(img_path), frame_bgr, [cv.IMWRITE_JPEG_QUALITY, 95])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return img_path, json_path


def append_to_csv(
    export_dir: pathlib.Path,
    image_filename: str,
    meta: Dict[str, Any],
    delimiter: str = ",",
    encoding: str = "utf-8-sig"
) -> bool:
    """
    Append a single record to the daily CSV file.
    Creates the file with headers if it doesn't exist.
    """
    try:
        # Ensure export directory exists
        export_dir.mkdir(parents=True, exist_ok=True)

        # CSV file for today
        today = datetime.now().strftime("%Y%m%d")
        csv_path = export_dir / f"export_{today}.csv"

        # Prepare record
        record = {
            "image_file": image_filename,
            "class": meta.get("class", ""),
            "timestamp": meta.get("timestamp", ""),
        }

        # Add all attributes
        attributes = meta.get("attributes", {})
        for attr_name, attr_value in attributes.items():
            # Convert boolean to readable format
            if isinstance(attr_value, bool):
                attr_value = "да" if attr_value else "нет"
            record[f"attr_{attr_name}"] = attr_value

        # Add capture metadata
        capture = meta.get("capture", {})
        record["capture_width"] = capture.get("width", "")
        record["capture_height"] = capture.get("height", "")
        record["capture_fps"] = capture.get("fps", "")

        # Check if file exists to determine if we need to write headers
        file_exists = csv_path.exists()

        # Write to CSV
        with open(csv_path, 'a', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=record.keys(), delimiter=delimiter)

            if not file_exists:
                writer.writeheader()
                logger.info(f"Created new CSV: {csv_path.name}")

            writer.writerow(record)

        logger.debug(f"Added record to {csv_path.name}")
        return True

    except Exception as e:
        logger.error(f"Error appending to CSV: {e}")
        return False
