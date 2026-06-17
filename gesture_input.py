# gesture input program for first task

import os
import glob
import time
import xml.etree.ElementTree as ET
import pyglet
import pyglet.shapes
from recognizer import Recognizer

WINDOW_W, WINDOW_H = 600, 650

BG_GL = (248 / 255, 248 / 255, 250 / 255, 1.0)

CANVAS_FILL   = (235, 242, 255)
CANVAS_BORDER = (100, 140, 210)
TEXT_DARK     = (28,  28,  30)
TEXT_GRAY     = (142, 142, 147)
STROKE        = (0, 122, 255)   # colour of the drawn stroke

FONT = "Arial"

CANVAS_X1 = 18
CANVAS_Y1 = 78
CANVAS_X2 = 582
CANVAS_Y2 = 590
CANVAS_W  = CANVAS_X2 - CANVAS_X1
CANVAS_H  = CANVAS_Y2 - CANVAS_Y1

SHAPES = "rectangle    circle    check    delete    pigtail"

GESTURE_FILES = {
    "rectangle": "rectangle",
    "circle": "circle",
    "check": "check",
    "delete": "delete_mark",
    "pigtail": "pigtail",
}

TEMPLATE_DIR = os.path.join("datasets", "wobbrock")
TEMPLATES_PER_CLASS = 5


def _rgba(rgb, a=255):
    return (*rgb, a)


def _load_points(path):
    root = ET.parse(path).getroot()
    # flip y values to match the canvas (y up)
    return [(float(e.get("X")), -float(e.get("Y"))) for e in root.findall("Point")]


def _template_paths(label):
    paths = []
    for subj in sorted(glob.glob(os.path.join(TEMPLATE_DIR, "s*"))):
        hits = sorted(glob.glob(os.path.join(subj, "medium", f"{label}*.xml")))
        if hits:
            paths.append(hits[0])
        if len(paths) == TEMPLATES_PER_CLASS:
            break
    return paths


def _preprocess(r, pts):
    pts = r.resample(list(pts), 64)
    pts = r.rotate_by(pts, -r.indicative_angle(pts))
    pts = r.scale_to(pts, 250)
    pts = r.translate_to(pts, (0, 0))
    return pts


def build_recognizer():
    # five wobbrock templates per class from different writers
    helper = Recognizer([])
    templates = []
    for name, label in GESTURE_FILES.items():
        for path in _template_paths(label):
            templates.append({"name": name, "points": _preprocess(helper, _load_points(path))})
    return Recognizer(templates)


class GestureInputApp:
    def __init__(self, window, recognizer):
        self.window = window
        self.recognizer = recognizer
        self.batch = pyglet.graphics.Batch()

        g1 = pyglet.graphics.Group(order=1)  # canvas border
        g2 = pyglet.graphics.Group(order=2)  # canvas fill
        g3 = pyglet.graphics.Group(order=3)  # text

        self.drawing = False
        self.stroke_points = []
        self.result = None
        self._stroke_lines = []
        self._stroke_batch = pyglet.graphics.Batch()

        # result text, one colour, goes bold once a gesture is recognized
        self._status_lbl = pyglet.text.Label(
            "Draw a gesture",
            font_name=FONT, font_size=16,
            x=WINDOW_W // 2, y=620,
            anchor_x="center", anchor_y="center",
            color=_rgba(TEXT_DARK),
            batch=self.batch, group=g3)

        # canvas border
        self._canvas_border_shape = pyglet.shapes.RoundedRectangle(
            CANVAS_X1 - 3, CANVAS_Y1 - 3, CANVAS_W + 6, CANVAS_H + 6, radius=18,
            color=CANVAS_BORDER, batch=self.batch, group=g1)

        self._canvas_fill_shape = pyglet.shapes.RoundedRectangle(
            CANVAS_X1, CANVAS_Y1, CANVAS_W, CANVAS_H, radius=16,
            color=CANVAS_FILL, batch=self.batch, group=g2)

        self._canvas_hint = pyglet.text.Label(
            "Draw here",
            font_name=FONT, font_size=18,
            x=WINDOW_W // 2, y=(CANVAS_Y1 + CANVAS_Y2) // 2,
            anchor_x="center", anchor_y="center",
            color=_rgba(TEXT_GRAY),
            batch=self.batch, group=g3)

        # supported shapes, below the drawing field
        self._shapes_lbl = pyglet.text.Label(
            SHAPES,
            font_name=FONT, font_size=13,
            x=WINDOW_W // 2, y=52,
            anchor_x="center", anchor_y="center",
            color=_rgba(TEXT_GRAY),
            batch=self.batch, group=g3)

        self._controls_lbl = pyglet.text.Label(
            "Release mouse to recognize  ·  R to clear  ·  Q to quit",
            font_name=FONT, font_size=11,
            x=WINDOW_W // 2, y=26,
            anchor_x="center", anchor_y="center",
            color=_rgba(TEXT_GRAY),
            batch=self.batch, group=g3)

    def _in_canvas(self, x, y):
        return CANVAS_X1 <= x <= CANVAS_X2 and CANVAS_Y1 <= y <= CANVAS_Y2

    def _rebuild_stroke(self):
        self._stroke_batch = pyglet.graphics.Batch()
        self._stroke_lines = []
        if len(self.stroke_points) < 2:
            return
        color = _rgba(STROKE, 210)
        for i in range(1, len(self.stroke_points)):
            p1, p2 = self.stroke_points[i - 1], self.stroke_points[i]
            line = pyglet.shapes.Line(
                p1[0], p1[1], p2[0], p2[1],
                3, color=color,
                batch=self._stroke_batch)
            self._stroke_lines.append(line)

    def _set_status(self, text, bold=False):
        self._status_lbl.text = text
        self._status_lbl.bold = bold

    def clear(self):
        self.drawing = False
        self.stroke_points = []
        self.result = None
        self._stroke_batch = pyglet.graphics.Batch()
        self._stroke_lines = []
        self._canvas_hint.color = _rgba(TEXT_GRAY)
        self._set_status("Draw a gesture")

    def on_mouse_press(self, x, y, button, _modifiers):
        if button != pyglet.window.mouse.LEFT or not self._in_canvas(x, y):
            return
        self.drawing = True
        self.stroke_points = [(x, y)]
        self.result = None
        self._canvas_hint.color = (0, 0, 0, 0)
        self._set_status("Recording unistroke…")
        self._rebuild_stroke()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if not self.drawing:
            return
        cx = max(CANVAS_X1, min(CANVAS_X2, x))
        cy = max(CANVAS_Y1, min(CANVAS_Y2, y))
        self.stroke_points.append((cx, cy))
        self._rebuild_stroke()

    def on_mouse_release(self, x, y, button, modifiers):
        if not self.drawing:
            return
        self.drawing = False
        if len(self.stroke_points) < 10:
            self._set_status("Too short, draw again")
            return
        t0 = time.perf_counter()
        name, score = self.recognizer.recognize(self.stroke_points)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.result = name
        self._set_status(f"detected {name}  ({score:.2f})  in {elapsed_ms:.0f} ms", bold=True)

    def draw(self):
        self.batch.draw()
        self._stroke_batch.draw()


def main():
    config = pyglet.gl.Config(sample_buffers=1, samples=4, double_buffer=True)
    try:
        win = pyglet.window.Window(WINDOW_W, WINDOW_H,
                                   caption="Gesture Recognizer", resizable=False,
                                   config=config)
    except pyglet.window.NoSuchConfigException:
        win = pyglet.window.Window(WINDOW_W, WINDOW_H,
                                   caption="Gesture Recognizer", resizable=False)
    pyglet.gl.glClearColor(*BG_GL)

    recognizer = build_recognizer()
    app = GestureInputApp(win, recognizer)

    @win.event
    def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.Q:
            pyglet.app.exit()
            os._exit(0)
        elif symbol == pyglet.window.key.R:
            app.clear()

    @win.event
    def on_mouse_press(x, y, button, modifiers):
        app.on_mouse_press(x, y, button, modifiers)

    @win.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        app.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    @win.event
    def on_mouse_release(x, y, button, modifiers):
        app.on_mouse_release(x, y, button, modifiers)

    @win.event
    def on_draw():
        win.clear()
        app.draw()

    try:
        pyglet.app.run()
    except KeyboardInterrupt:
        os._exit(0)


if __name__ == "__main__":
    main()
