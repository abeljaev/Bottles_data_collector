import argparse
from datetime import datetime
import cv2 as cv
import numpy as np

from .state import specs_and_defaults, AppState
from .io_utils import ensure_session_dir, save_sample
from .ui import build_panel, PANEL_W, put_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument(
        "--font",
        default="",
        help="путь к .ttf/.otf для кириллицы, например /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    ap.add_argument("--pet", default="states/states_pet.json")
    ap.add_argument("--can", default="states/states_can.json")
    ap.add_argument("--foreign", default="states/states_non_target.json")
    ap.add_argument("--out", default="dataset")
    args = ap.parse_args()

    specs, defaults = specs_and_defaults(args.pet, args.can, args.foreign)

    cap = cv.VideoCapture(args.cam)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, args.w)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, args.h)
    cap.set(cv.CAP_PROP_FPS, args.fps)
    if not cap.isOpened():
        print("ERROR: camera not opened")
        return

    sess = ensure_session_dir(args.out)
    state = AppState(
        current_class="PET", attrs=defaults["PET"].copy(), preview_h=args.h
    )

    WIN = "collector"
    cv.namedWindow(WIN, cv.WINDOW_NORMAL)
    widgets = []

    def on_mouse(event, mx, my, flags, userdata):
        nonlocal widgets, state
        if event != cv.EVENT_LBUTTONDOWN:
            return
        if mx < args.w:
            return
        px, py = mx - args.w, my
        for w in widgets:
            x, y, wid, h = w.rect
            if x <= px <= x + wid and y <= py <= y + h:
                if w.wtype == "class_radio":
                    state.current_class = w.payload["cls"]
                    state.attrs = defaults[state.current_class].copy()
                elif w.wtype == "attr_enum":
                    state.attrs[w.payload["name"]] = w.payload["value"]
                elif w.wtype == "attr_bool":
                    name = w.payload["name"]
                    state.attrs[name] = not bool(state.attrs.get(name))
                elif w.wtype == "save":
                    state.save_requested = True
                elif w.wtype == "quit":
                    state.quit_requested = True
                break

    cv.setMouseCallback(WIN, on_mouse)
    print("Controls: [1]=PET, [2]=CAN, [3]=FOREIGN, [s]=save, [q/ESC]=quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            cv.waitKey(1)
            continue

        panel, widgets = build_panel(specs, state)
        canvas = cv.hconcat([frame, panel])
        hint = f"CLASS={state.current_class} attrs={state.attrs}"
        cv.rectangle(canvas, (0, 0), (args.w + PANEL_W, 22), (0, 0, 0), -1)
        put_text(canvas, hint[: min(len(hint), 120)], (10, 16))

        cv.imshow(WIN, canvas)
        key = cv.waitKey(1) & 0xFF

        if key in (ord("q"), 27) or state.quit_requested:
            break
        if key == ord("1"):
            state.current_class = "PET"
            state.attrs = defaults["PET"].copy()
        if key == ord("2"):
            state.current_class = "CAN"
            state.attrs = defaults["CAN"].copy()
        if key == ord("3"):
            state.current_class = "FOREIGN"
            state.attrs = defaults["FOREIGN"].copy()

        if key == ord("s") or state.save_requested:
            meta = {
                "timestamp": datetime.now().isoformat(),
                "class": state.current_class,
                "attributes": state.attrs,
                "user_assert_one_object": True,
                "capture": {
                    "width": int(cap.get(cv.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                    "fps": cap.get(cv.CAP_PROP_FPS),
                },
                "session_dir": str(sess),
            }
            img_p, json_p = save_sample(sess, frame, meta)
            print(f"Saved: {img_p.name}  meta: {json_p.name}")
            state.save_requested = False

    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
