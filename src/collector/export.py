"""
CSV export functionality for collected data.
"""
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from loguru import logger


def export_session_to_csv(
    session_dir: Path,
    output_file: Path,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    include_timestamp: bool = True
) -> bool:
    """
    Export all samples from a session directory to CSV.

    Args:
        session_dir: Path to session directory containing JSON metadata files
        output_file: Path where CSV file will be saved
        delimiter: CSV delimiter character
        encoding: File encoding (utf-8-sig includes BOM for Excel)
        include_timestamp: Include timestamp column in export

    Returns:
        True if export successful, False otherwise
    """
    try:
        # Find all JSON metadata files in meta/ subdirectory
        meta_dir = session_dir / "meta"
        if not meta_dir.exists():
            logger.warning(f"Meta directory not found: {meta_dir}")
            return False

        json_files = list(meta_dir.glob("*.json"))

        if not json_files:
            logger.warning(f"No JSON files found in {meta_dir}")
            return False

        logger.info(f"Found {len(json_files)} metadata files")

        # Load all metadata
        records = []
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Flatten the structure for CSV
                record = {
                    "image_file": json_file.stem + ".jpg",
                    "class": data.get("class", ""),
                }

                # Add timestamp if requested
                if include_timestamp:
                    record["timestamp"] = data.get("timestamp", "")

                # Add all attributes as separate columns
                attributes = data.get("attributes", {})
                for attr_name, attr_value in attributes.items():
                    # Convert boolean values to readable format
                    if isinstance(attr_value, bool):
                        attr_value = "да" if attr_value else "нет"
                    record[f"attr_{attr_name}"] = attr_value

                # Add capture metadata
                capture = data.get("capture", {})
                record["capture_width"] = capture.get("width", "")
                record["capture_height"] = capture.get("height", "")
                record["capture_fps"] = capture.get("fps", "")

                records.append(record)

            except Exception as e:
                logger.warning(f"Error reading {json_file.name}: {e}")
                continue

        if not records:
            logger.error("No valid records found")
            return False

        # Create DataFrame
        df = pd.DataFrame(records)

        # Save to CSV
        df.to_csv(
            output_file,
            sep=delimiter,
            encoding=encoding,
            index=False
        )

        logger.success(f"Exported {len(records)} records to {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return False


def export_all_sessions_to_csv(
    output_dir: Path,
    csv_file: Path,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    include_timestamp: bool = True
) -> bool:
    """
    Export all data from output directory to a single CSV file.

    Args:
        output_dir: Root dataset directory
        csv_file: Path where CSV file will be saved
        delimiter: CSV delimiter character
        encoding: File encoding
        include_timestamp: Include timestamp column

    Returns:
        True if export successful, False otherwise
    """
    try:
        # Find all date directories (format: YYYYMMDD)
        all_records = []
        date_count = 0

        for date_dir in sorted(output_dir.glob("*")):
            if not date_dir.is_dir():
                continue

            # Look for JSON files in meta/ subdirectory
            meta_dir = date_dir / "meta"
            if not meta_dir.exists():
                continue

            date_count += 1
            json_files = list(meta_dir.glob("*.json"))

            for json_file in sorted(json_files):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Flatten the structure
                    record = {
                        "date": date_dir.name,
                        "image_file": json_file.stem + ".jpg",
                        "class": data.get("class", ""),
                    }

                    if include_timestamp:
                        record["timestamp"] = data.get("timestamp", "")

                    # Add attributes
                    attributes = data.get("attributes", {})
                    for attr_name, attr_value in attributes.items():
                        if isinstance(attr_value, bool):
                            attr_value = "да" if attr_value else "нет"
                        record[f"attr_{attr_name}"] = attr_value

                    # Add capture metadata
                    capture = data.get("capture", {})
                    record["capture_width"] = capture.get("width", "")
                    record["capture_height"] = capture.get("height", "")
                    record["capture_fps"] = capture.get("fps", "")

                    all_records.append(record)

                except Exception as e:
                    logger.warning(f"Error reading {json_file}: {e}")
                    continue

        if not all_records:
            logger.error("No records found")
            return False

        # Create DataFrame and export
        df = pd.DataFrame(all_records)
        df.to_csv(csv_file, sep=delimiter, encoding=encoding, index=False)

        logger.success(
            f"Exported {len(all_records)} records from {date_count} date(s) to {csv_file}"
        )
        return True

    except Exception as e:
        logger.error(f"Error exporting all data: {e}")
        return False
