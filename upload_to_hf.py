#!/usr/bin/env python3
"""
Upload dataset to Hugging Face Hub with incremental update support.

This script uploads the collected bottle classifier dataset to Hugging Face Hub.
It supports:
- Full dataset upload
- Incremental updates (only new files)
- Automatic README generation
- Multiple upload strategies

Usage:
    export HF_TOKEN="your_token_here"
    python upload_to_hf.py --repo-id "ChilledAndRelaxed/ContainerClassification"

    # Or for incremental update
    python upload_to_hf.py --repo-id "ChilledAndRelaxed/ContainerClassification" --incremental
"""

import os
import argparse
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from loguru import logger
from huggingface_hub import HfApi, CommitOperationAdd
from huggingface_hub.utils import HfHubHTTPError


def count_dataset_stats(dataset_dir: Path) -> Dict[str, Any]:
    """Calculate dataset statistics."""
    stats = {
        "total_images": 0,
        "total_metadata": 0,
        "classes": {}
    }

    # Count images
    images_dir = dataset_dir / "images"
    if images_dir.exists():
        stats["total_images"] = len(list(images_dir.glob("*.jpg")))

    # Count metadata
    meta_dir = dataset_dir / "meta"
    if meta_dir.exists():
        stats["total_metadata"] = len(list(meta_dir.glob("*.json")))

    # Count by class from CSV files
    for class_name in ["pet", "can", "foreign"]:
        csv_file = dataset_dir / f"{class_name}.csv"
        if csv_file.exists():
            # Count lines (excluding header)
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                line_count = sum(1 for _ in f) - 1
                stats["classes"][class_name] = max(0, line_count)

    return stats


def generate_dataset_readme(dataset_dir: Path, repo_id: str) -> str:
    """Generate README.md content for the dataset."""
    stats = count_dataset_stats(dataset_dir)

    readme = f"""---
license: mit
task_categories:
- image-classification
- object-detection
tags:
- bottles
- recycling
- waste-classification
- pet
- can
- containers
language:
- ru
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: train
    path: "pet.csv"
  - split: train
    path: "can.csv"
  - split: train
    path: "foreign.csv"
---

# Container Classification Dataset

Датасет для классификации контейнеров (бутылки PET, алюминиевые банки, посторонние объекты).

## Dataset Description

This dataset contains images and annotations for container classification tasks.
The dataset includes three main classes:

- **PET**: Plastic bottles (PET containers)
- **CAN**: Aluminum cans
- **FOREIGN**: Foreign objects (non-target items)

### Dataset Statistics

- **Total Images**: {stats['total_images']}
- **Total Annotations**: {stats['total_metadata']}

**Class Distribution**:
{chr(10).join(f"- {name.upper()}: {count} samples" for name, count in stats['classes'].items())}

### Dataset Structure

```
dataset/
├── images/          # Image files (YYYYMMDD_HHMMSS_ffffff.jpg)
├── meta/            # JSON metadata files
├── pet.csv          # PET class annotations
├── can.csv          # CAN class annotations
└── foreign.csv      # FOREIGN class annotations
```

### Data Fields

Each CSV file contains the following fields:

**Common attributes**:
- `timestamp`: Image capture timestamp
- `image_filename`: Corresponding image file
- `class`: Object class (PET/CAN/FOREIGN)
- `container_name`: Specific container identifier
- `volume`: Container volume
- `position`: Object position in frame
- `wet`: Whether container is wet
- `glare`: Presence of glare
- `shadow`: Presence of shadow

**Class-specific attributes**:

*PET*:
- `deformation`, `fill`, `transparency`, `label`, `neck_direction`, `cap_present`, `condensate`

*CAN*:
- `deformation`, `fill`, `finish`, `label`, `condensate`

*FOREIGN*:
- `subtype`, `is_container`, `material`, `multiple_items`, `reason`

### Data Collection

Data collected using Gradio-based web interface with:
- Real-time camera feed
- Interactive attribute annotation
- Automatic metadata generation
- Quality control features

### Usage

```python
from datasets import load_dataset

# Load full dataset
dataset = load_dataset("{repo_id}")

# Load specific class
pet_dataset = load_dataset("{repo_id}", data_files="pet.csv")
can_dataset = load_dataset("{repo_id}", data_files="can.csv")
foreign_dataset = load_dataset("{repo_id}", data_files="foreign.csv")
```

### Citation

If you use this dataset, please cite:

```bibtex
@misc{{container_classification_2025,
  title={{Container Classification Dataset}},
  author={{ChilledAndRelaxed}},
  year={{2025}},
  publisher={{Hugging Face}},
  howpublished={{\\url{{https://huggingface.co/datasets/{repo_id}}}}}
}}
```

### License

MIT License

### Updates

Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This dataset is continuously updated with new samples.
"""

    return readme


def upload_dataset_full(
    dataset_dir: Path,
    repo_id: str,
    token: Optional[str] = None,
    private: bool = False
) -> None:
    """Upload entire dataset folder to Hugging Face Hub."""
    logger.info(f"Uploading full dataset from {dataset_dir} to {repo_id}")

    api = HfApi(token=token)

    # Create repo if doesn't exist
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=private,
            exist_ok=True
        )
        logger.info(f"Repository {repo_id} created/verified")
    except Exception as e:
        logger.error(f"Failed to create repository: {e}")
        raise

    # Generate and save README
    readme_content = generate_dataset_readme(dataset_dir, repo_id)
    readme_path = dataset_dir / "README.md"
    readme_path.write_text(readme_content, encoding='utf-8')
    logger.info("Generated README.md")

    # Upload using upload_large_folder for better performance
    try:
        api.upload_large_folder(
            folder_path=str(dataset_dir),
            repo_id=repo_id,
            repo_type="dataset",
        )
        logger.success(f"Dataset uploaded successfully to {repo_id}")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise


def get_remote_files(api: HfApi, repo_id: str) -> set:
    """Get list of files already in the remote repository."""
    try:
        files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
        return set(files)
    except HfHubHTTPError:
        logger.warning("Repository doesn't exist or is empty")
        return set()


def upload_dataset_incremental(
    dataset_dir: Path,
    repo_id: str,
    token: Optional[str] = None,
    private: bool = False
) -> None:
    """Upload only new files to Hugging Face Hub."""
    logger.info(f"Performing incremental upload from {dataset_dir} to {repo_id}")

    api = HfApi(token=token)

    # Create repo if doesn't exist
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=private,
            exist_ok=True
        )
    except Exception as e:
        logger.error(f"Failed to create repository: {e}")
        raise

    # Get existing files in remote repo
    remote_files = get_remote_files(api, repo_id)
    logger.info(f"Found {len(remote_files)} files in remote repository")

    # Collect operations for files that need to be uploaded
    operations: List[CommitOperationAdd] = []

    # Check all local files
    for local_file in dataset_dir.rglob("*"):
        if local_file.is_file():
            # Get relative path
            rel_path = local_file.relative_to(dataset_dir)
            path_in_repo = str(rel_path).replace("\\", "/")  # Windows compatibility

            # Skip cache and hidden files/folders
            path_parts = path_in_repo.split("/")
            if any(part.startswith(".") for part in path_parts):
                continue

            # Skip if file already exists remotely
            if path_in_repo in remote_files:
                continue

            # Add operation to upload this file
            operations.append(
                CommitOperationAdd(
                    path_in_repo=path_in_repo,
                    path_or_fileobj=str(local_file)
                )
            )

    if not operations:
        logger.info("No new files to upload")
        return

    logger.info(f"Found {len(operations)} new files to upload")

    # Always update README and CSV files
    readme_content = generate_dataset_readme(dataset_dir, repo_id)
    readme_path = dataset_dir / "README.md"
    readme_path.write_text(readme_content, encoding='utf-8')

    # Force update README and CSV files
    always_update = ["README.md", "pet.csv", "can.csv", "foreign.csv"]
    for filename in always_update:
        file_path = dataset_dir / filename
        if file_path.exists():
            # Remove from operations if already there
            operations = [op for op in operations if op.path_in_repo != filename]
            # Add as new operation
            operations.append(
                CommitOperationAdd(
                    path_in_repo=filename,
                    path_or_fileobj=str(file_path)
                )
            )

    # Commit all operations
    try:
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message=f"Incremental update - {len(operations)} files - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        logger.success(f"Uploaded {len(operations)} files to {repo_id}")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Upload bottle classifier dataset to Hugging Face Hub"
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="Repository ID (e.g., 'username/dataset-name')"
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("dataset"),
        help="Path to dataset directory (default: ./dataset)"
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Hugging Face token (default: from HF_TOKEN env var)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Upload only new files (incremental update)"
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create private repository"
    )

    args = parser.parse_args()

    # Get token from args or environment
    token = args.token or os.getenv("HF_TOKEN")
    if not token:
        logger.error("No Hugging Face token provided. Set HF_TOKEN env var or use --token")
        return

    # Check dataset directory exists
    if not args.dataset_dir.exists():
        logger.error(f"Dataset directory not found: {args.dataset_dir}")
        return

    # Show dataset statistics
    stats = count_dataset_stats(args.dataset_dir)
    logger.info(f"Dataset statistics: {json.dumps(stats, indent=2)}")

    # Upload
    if args.incremental:
        upload_dataset_incremental(
            args.dataset_dir,
            args.repo_id,
            token=token,
            private=args.private
        )
    else:
        upload_dataset_full(
            args.dataset_dir,
            args.repo_id,
            token=token,
            private=args.private
        )


if __name__ == "__main__":
    main()
