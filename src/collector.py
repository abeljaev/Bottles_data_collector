import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

Spec = Dict[str, Any]


@dataclass
class AppState:
    current_class: str = "PET"
    attrs: Dict[str, Any] = field(default_factory=dict)
    preview_h: int = 720
    save_requested: bool = False
    quit_requested: bool = False


def load_spec(path: str) -> Spec:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
        defaults[cls] = d
    return specs, defaults
