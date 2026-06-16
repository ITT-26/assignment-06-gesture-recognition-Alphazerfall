# recorder for the test set for task 2

import os
import re
import time
import pyglet
import pyglet.shapes

WINDOW_W, WINDOW_H = 600, 650

BG_GL = (248 / 255, 248 / 255, 250 / 255, 1.0)

LIGHT_GRAY    = (229, 229, 234)
CANVAS_FILL   = (235, 242, 255)
CANVAS_BORDER = (100, 140, 210)
TEXT_DARK     = (28,  28,  30)
TEXT_GRAY     = (110, 110, 118)

RED   = (255,  59,  48)
BLUE  = (0,   122, 255)
GREEN = (52,  199,  89)

FONT = "Arial"

CANVAS_X1 = 40
CANVAS_Y1 = 80
CANVAS_X2 = 560
CANVAS_Y2 = 545
CANVAS_W  = CANVAS_X2 - CANVAS_X1
CANVAS_H  = CANVAS_Y2 - CANVAS_Y1


GESTURE_CLASSES = [
    "arrow", "caret", "check", "circle", "delete_mark",
    "left_curly_brace", "left_sq_bracket", "pigtail", "question_mark",
    "rectangle", "right_curly_brace", "right_sq_bracket",
    "star", "triangle", "v", "x",
]


SAMPLES_PER_CLASS = 10  # ten gestures per class
SUBJECT = "1"  # subject id
OUT_DIR = os.path.join("datasets", "custom", f"s{SUBJECT}")
MIN_POINTS = 10 # minimum number of points for a valid gesture, to avoid accidental clicks


def rgba(rgb, a=255):
    return (*rgb, a)


class GestureRecorder:
    def __init__(self):
        self.batch = pyglet.graphics.Batch()
        g1 = pyglet.graphics.Group(order=1)
        g2 = pyglet.graphics.Group(order=2)
        g3 = pyglet.graphics.Group(order=3)

        os.makedirs(OUT_DIR, exist_ok=True)

        self.saved = {c: self.count_existing(c) for c in GESTURE_CLASSES}

        self.class_idx = self.first_unfinished_class()
        self.drawing = False
        self.reviewing = False
        self.stroke = []  # (x, y, time in ms)
        self.stroke_lines = []
        self.stroke_batch = pyglet.graphics.Batch()

        title = pyglet.text.Label(
            "Gesture Recorder", font_name=FONT, font_size=20,
            x=WINDOW_W // 2, y=625, anchor_x="center", anchor_y="center",
            color=rgba(TEXT_DARK), batch=self.batch, group=g3)
        title.bold = True

        self.class_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=22,
            x=WINDOW_W // 2, y=592, anchor_x="center", anchor_y="center",
            color=rgba(BLUE), batch=self.batch, group=g3)
        self.class_lbl.bold = True

        self.progress_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=13,
            x=WINDOW_W // 2, y=565, anchor_x="center", anchor_y="center",
            color=rgba(TEXT_GRAY), batch=self.batch, group=g3)

        self.canvas_border = pyglet.shapes.RoundedRectangle(
            CANVAS_X1 - 3, CANVAS_Y1 - 3, CANVAS_W + 6, CANVAS_H + 6, radius=18,
            color=CANVAS_BORDER, batch=self.batch, group=g1)
        self.canvas_fill = pyglet.shapes.RoundedRectangle(
            CANVAS_X1, CANVAS_Y1, CANVAS_W, CANVAS_H, radius=16,
            color=CANVAS_FILL, batch=self.batch, group=g2)

        self.canvas_hint = pyglet.text.Label(
            "draw here", font_name=FONT, font_size=18,
            x=WINDOW_W // 2, y=(CANVAS_Y1 + CANVAS_Y2) // 2,
            anchor_x="center", anchor_y="center",
            color=rgba(LIGHT_GRAY), batch=self.batch, group=g3)

        self.prompt_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=13,
            x=WINDOW_W // 2, y=44, anchor_x="center", anchor_y="center",
            color=rgba(TEXT_GRAY), batch=self.batch, group=g3)

        pyglet.text.Label(
            "ENTER save   R redraw   [ ] change class   Q quit",
            font_name=FONT, font_size=10,
            x=WINDOW_W // 2, y=18, anchor_x="center", anchor_y="center",
            color=rgba(TEXT_GRAY), batch=self.batch, group=g3)

        self.update_labels()

    # saving / loading files

    def count_existing(self, cls):
        if not os.path.isdir(OUT_DIR):
            return 0
        pat = re.compile(rf"^{re.escape(cls)}(\d+)\.xml$")
        return sum(1 for f in os.listdir(OUT_DIR) if pat.match(f))

    def first_unfinished_class(self):
        for i, cls in enumerate(GESTURE_CLASSES):
            if self.saved[cls] < SAMPLES_PER_CLASS:
                return i
        return 0

    @property
    def current_class(self):
        return GESTURE_CLASSES[self.class_idx]

    def next_filename(self, cls):
        # find the smallest free number
        used = set()
        pat = re.compile(rf"^{re.escape(cls)}(\d+)\.xml$")
        for f in os.listdir(OUT_DIR):
            m = pat.match(f)
            if m:
                used.add(int(m.group(1)))
        n = 1
        while n in used:
            n += 1
        return f"{cls}{n:02d}.xml", n

    def save_stroke(self):
        cls = self.current_class
        fname, number = self.next_filename(cls)
        path = os.path.join(OUT_DIR, fname)

        duration = int(self.stroke[-1][2] - self.stroke[0][2])

        lines = [
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>',
            f'<Gesture Name="{cls}{number:02d}" Subject="{SUBJECT}" '
            f'Speed="medium" Number="{number}" NumPts="{len(self.stroke)}" '
            f'Millseconds="{duration}" AppName="GestureRecorder" '
            f'AppVer="1.0.0.0" Date="{time.strftime("%A, %B %d, %Y")}" '
            f'TimeOfDay="{time.strftime("%I:%M:%S %p")}">',
        ]
        for (x, y, t) in self.stroke:
            # pyglet has y going up, the xml files use y going down, so flip it
            sx = int(round(x))
            sy = int(round(WINDOW_H - y))
            lines.append(f'  <Point X="{sx}" Y="{sy}" T="{int(t)}" />')
        lines.append('</Gesture>')

        # the wobbrock files are utf-8 with a BOM and CRLF line endings, so do the same
        with open(path, "w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write("\n".join(lines))

        self.saved[cls] = self.count_existing(cls)
        return fname

    # drawing the stroke

    def rebuild_stroke(self, color):
        self.stroke_batch = pyglet.graphics.Batch()
        self.stroke_lines = []
        if len(self.stroke) < 2:
            return
        c = (*color, 220)
        for i in range(1, len(self.stroke)):
            x1, y1, _ = self.stroke[i - 1]
            x2, y2, _ = self.stroke[i]
            self.stroke_lines.append(
                pyglet.shapes.Line(x1, y1, x2, y2, 3, color=c,
                                   batch=self.stroke_batch))

    def clear_stroke(self):
        self.stroke = []
        self.stroke_lines = []
        self.stroke_batch = pyglet.graphics.Batch()

    # text labels

    def update_labels(self):
        cls = self.current_class
        done = self.saved[cls]
        self.class_lbl.text = cls

        total_done = sum(min(v, SAMPLES_PER_CLASS) for v in self.saved.values())
        total_need = SAMPLES_PER_CLASS * len(GESTURE_CLASSES)
        self.progress_lbl.text = (
            f"sample {min(done + 1, SAMPLES_PER_CLASS)} / {SAMPLES_PER_CLASS}"
            f"     (class {self.class_idx + 1}/{len(GESTURE_CLASSES)}, "
            f"{total_done}/{total_need} total)"
        )

        if done >= SAMPLES_PER_CLASS:
            self.set_prompt(f"{cls} done, press ] for the next one", GREEN)
        elif self.reviewing:
            self.set_prompt("ENTER to save, R to redraw", BLUE)
        else:
            self.set_prompt("draw the gesture above", TEXT_GRAY)

    def set_prompt(self, text, color):
        self.prompt_lbl.text = text
        self.prompt_lbl.color = rgba(color)

    # mouse / keyboard

    def in_canvas(self, x, y):
        return CANVAS_X1 <= x <= CANVAS_X2 and CANVAS_Y1 <= y <= CANVAS_Y2

    def on_mouse_press(self, x, y, button, modifiers):
        if button != pyglet.window.mouse.LEFT or not self.in_canvas(x, y):
            return
        self.drawing = True
        self.reviewing = False
        self.canvas_hint.color = (0, 0, 0, 0)
        self.stroke = [(x, y, time.perf_counter() * 1000.0)]
        self.rebuild_stroke(BLUE)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if not self.drawing:
            return
        # keep the points inside the canvas
        cx = max(CANVAS_X1, min(CANVAS_X2, x))
        cy = max(CANVAS_Y1, min(CANVAS_Y2, y))
        self.stroke.append((cx, cy, time.perf_counter() * 1000.0))
        self.rebuild_stroke(BLUE)

    def on_mouse_release(self, x, y, button, modifiers):
        if not self.drawing:
            return
        self.drawing = False
        if len(self.stroke) < MIN_POINTS:
            self.clear_stroke()
            self.canvas_hint.color = rgba(LIGHT_GRAY)
            self.set_prompt("too short, try again", RED)
            return
        self.reviewing = True
        self.set_prompt("ENTER to save, R to redraw", BLUE)

    def discard(self):
        self.reviewing = False
        self.clear_stroke()
        self.canvas_hint.color = rgba(LIGHT_GRAY)
        self.update_labels()

    def accept(self):
        if not self.reviewing or not self.stroke:
            return
        if self.saved[self.current_class] >= SAMPLES_PER_CLASS:
            self.set_prompt("this class is already done, press ]", GREEN)
            return
        fname = self.save_stroke()
        self.reviewing = False
        self.clear_stroke()
        self.canvas_hint.color = rgba(LIGHT_GRAY)
        # jump to the next class once this one has enough samples
        if self.saved[self.current_class] >= SAMPLES_PER_CLASS:
            self.change_class(+1)
        self.update_labels()
        self.set_prompt(f"saved {fname}", GREEN)

    def change_class(self, step):
        self.reviewing = False
        self.clear_stroke()
        self.canvas_hint.color = rgba(LIGHT_GRAY)
        self.class_idx = (self.class_idx + step) % len(GESTURE_CLASSES)
        self.update_labels()

    def on_key_press(self, symbol, modifiers):
        key = pyglet.window.key
        if symbol == key.Q:
            pyglet.app.exit()
            os._exit(0)
        elif symbol in (key.ENTER, key.RETURN, key.SPACE):
            self.accept()
        elif symbol in (key.R, key.BACKSPACE):
            self.discard()
        elif symbol == key.BRACKETRIGHT:
            self.change_class(+1)
        elif symbol == key.BRACKETLEFT:
            self.change_class(-1)

    def draw(self):
        self.batch.draw()
        self.stroke_batch.draw()


def main():
    config = pyglet.gl.Config(sample_buffers=1, samples=4, double_buffer=True)
    try:
        win = pyglet.window.Window(WINDOW_W, WINDOW_H,
                                   caption="Gesture Recorder", resizable=False,
                                   config=config)
    except pyglet.window.NoSuchConfigException:
        win = pyglet.window.Window(WINDOW_W, WINDOW_H,
                                   caption="Gesture Recorder", resizable=False)
    pyglet.gl.glClearColor(*BG_GL)

    app = GestureRecorder()

    @win.event
    def on_key_press(symbol, modifiers):
        app.on_key_press(symbol, modifiers)

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

    print(f"Saving recordings to: {os.path.abspath(OUT_DIR)}")
    pyglet.app.run()


if __name__ == "__main__":
    main()
