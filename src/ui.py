from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import cv2 as cv
import numpy as np
from PIL import ImageFont, ImageDraw, Image

FONT = cv.FONT_HERSHEY_SIMPLEX
FS = 0.5
TH = 1
PANEL_W = 360
ROW_H = 26
PAD = 10


@dataclass
class Widget:
    rect: Tuple[int, int, int, int]
    wtype: str
    payload: Dict[str, Any]


def put_text(
    img, text, org, color=(220, 220, 220), scale=0.5, thick=1, font_path: str = ""
):
    if font_path:
        pil = Image.fromarray(img)
        draw = ImageDraw.Draw(pil)
        # масштаб: 0.5 ~ 16pt
        size = max(12, int(16 * scale * 1.6))
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            font = ImageFont.load_default()
        draw.text(org, text, fill=tuple(int(c) for c in color), font=font)
        img[:] = np.array(pil)
    else:
        cv.putText(
            img, text, org, cv.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv.LINE_AA
        )


def draw_button(img, rect, text, active=False):
    x, y, w, h = rect
    bg = (70, 70, 70) if not active else (90, 140, 90)
    cv.rectangle(img, (x, y), (x + w, y + h), bg, -1)
    cv.rectangle(img, (x, y), (x + w, y + h), (110, 110, 110), 1)
    put_text(img, text, (x + 8, y + h - 8))


def draw_radio(img, rect, label, selected):
    x, y, w, h = rect
    cv.rectangle(img, (x, y), (x + w, y + h), (60, 60, 60), -1)
    cv.circle(img, (x + 12, y + h // 2), 8, (180, 180, 180), 1)
    if selected:
        cv.circle(img, (x + 12, y + h // 2), 5, (90, 200, 90), -1)
    put_text(img, label, (x + 28, y + h - 8))


def draw_checkbox(img, rect, label, checked):
    x, y, w, h = rect
    cv.rectangle(img, (x, y), (x + w, y + h), (60, 60, 60), -1)
    cv.rectangle(img, (x + 4, y + 4), (x + 20, y + h - 4), (180, 180, 180), 1)
    if checked:
        cv.line(img, (x + 5, y + h // 2), (x + 12, y + h - 6), (90, 200, 90), 2)
        cv.line(img, (x + 12, y + h - 6), (x + 22, y + 6), (90, 200, 90), 2)
    put_text(img, label, (x + 28, y + h - 8))


def build_panel(specs: Dict[str, Any], state) -> Tuple[np.ndarray, List[Widget]]:
    H = state.preview_h
    panel = np.zeros((H, PANEL_W, 3), dtype=np.uint8)
    panel[:] = (45, 45, 45)
    widgets: List[Widget] = []

    put_text(panel, "CLASS", (PAD, 24), (200, 200, 200), 0.6, 2)
    y = 30
    for cls in ["PET", "CAN", "FOREIGN"]:
        rect = (PAD, y, PANEL_W - 2 * PAD, ROW_H)
        draw_radio(panel, rect, cls, state.current_class == cls)
        widgets.append(Widget(rect, "class_radio", {"cls": cls}))
        y += ROW_H + 4

    y += 6
    cv.line(panel, (PAD, y), (PANEL_W - PAD, y), (90, 90, 90), 1)
    y += 10
    put_text(panel, "ATTRIBUTES", (PAD, y), (200, 200, 200), 0.6, 2)
    y += 8

    spec = specs[state.current_class]
    for a in spec["attributes"]:
        y += 6
        put_text(panel, a["name"], (PAD, y + ROW_H - 8), (180, 180, 180), 0.5, 1)
        if a["type"] == "enum":
            y += 2
            for opt in a["options"]:
                rect = (PAD, y, PANEL_W - 2 * PAD, ROW_H)
                draw_radio(panel, rect, opt, state.attrs.get(a["name"]) == opt)
                widgets.append(
                    Widget(rect, "attr_enum", {"name": a["name"], "value": opt})
                )
                y += ROW_H + 2
        elif a["type"] == "bool":
            y += 2
            rect = (PAD, y, PANEL_W - 2 * PAD, ROW_H)
            draw_checkbox(panel, rect, "yes", bool(state.attrs.get(a["name"])))
            widgets.append(Widget(rect, "attr_bool", {"name": a["name"]}))
            y += ROW_H + 2

        if y > H - 100:
            break

    y = H - 80
    left_w = (PANEL_W - 3 * PAD) // 2
    draw_button(panel, (PAD, y, left_w, 36), "SAVE (s)", False)
    widgets.append(Widget((PAD, y, left_w, 36), "save", {}))
    draw_button(panel, (PAD + left_w + PAD, y, left_w, 36), "QUIT (q/esc)", False)
    widgets.append(Widget((PAD + left_w + PAD, y, left_w, 36), "quit", {}))

    return panel, widgets
