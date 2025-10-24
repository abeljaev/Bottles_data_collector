import json
import pathlib
from datetime import datetime
import cv2 as cv
from typing import Tuple, Dict, Any


def ensure_session_dir(root="dataset") -> pathlib.Path:
    today = datetime.now().strftime("%Y%m%d")
    base = pathlib.Path(root) / today
    base.mkdir(parents=True, exist_ok=True)
    sid = 1
    while (base / f"session_{sid:02d}").exists():
        sid += 1
    sess = base / f"session_{sid:02d}"
    (sess / "images").mkdir(parents=True, exist_ok=True)
    (sess / "meta").mkdir(parents=True, exist_ok=True)
    return sess


def save_sample(
    sess_dir: pathlib.Path, frame_bgr, meta: Dict[str, Any]
) -> Tuple[pathlib.Path, pathlib.Path]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    img_path = sess_dir / "images" / f"{ts}.jpg"
    json_path = sess_dir / "meta" / f"{ts}.json"
    cv.imwrite(str(img_path), frame_bgr, [cv.IMWRITE_JPEG_QUALITY, 95])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return img_path, json_path
