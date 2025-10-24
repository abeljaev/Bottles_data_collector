from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

from .config import load_class_spec

Spec = Dict[str, Any]


@dataclass
class AppState:
    current_class: str = "PET"
    attrs: Dict[str, Any] = field(default_factory=dict)
    preview_h: int = 720
    save_requested: bool = False
    quit_requested: bool = False
    active_text_field: str = ""  # name of currently editing text field
    text_input_buffer: str = ""  # buffer for text input


def load_spec(path: str) -> Spec:
    """Load class specification from YAML or JSON file."""
    return load_class_spec(path)


def specs_and_defaults(
    pet: str, can: str, foreign: str
) -> Tuple[Dict[str, Spec], Dict[str, Dict[str, Any]]]:
    specs = {
        "PET": load_spec(pet),
        "CAN": load_spec(can),
        "FOREIGN": load_spec(foreign),
    }
    defaults: Dict[str, Dict[str, Any]] = {}
    for cls, spec in specs.items():
        d: Dict[str, Any] = {}
        for a in spec["attributes"]:
            if a["type"] == "enum":
                d[a["name"]] = a.get("default", a["options"][0])
            elif a["type"] == "bool":
                d[a["name"]] = bool(a.get("default", False))
            elif a["type"] == "text":
                d[a["name"]] = a.get("default", "")
        defaults[cls] = d
    return specs, defaults
