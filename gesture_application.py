# Rock Paper Scissors game for task 3. Draw your move (circle = rock,
# rectangle = paper, v = scissors); moves are recognized with the $1 recognizer.

import os
import math
import random
import pyglet
import pyglet.shapes
from recognizer import Recognizer
from gesture_input import (
    FONT, BG_GL, CANVAS_FILL, CANVAS_BORDER, TEXT_DARK, TEXT_GRAY,
    APPLE_RED, APPLE_GREEN, APPLE_BLUE,
    _template_paths, _load_points, _preprocess,
)

WINDOW_W, WINDOW_H = 600, 720

CANVAS_X1, CANVAS_Y1 = 20, 40
CANVAS_X2, CANVAS_Y2 = 580, 560
CANVAS_W = CANVAS_X2 - CANVAS_X1
CANVAS_H = CANVAS_Y2 - CANVAS_Y1

GESTURES = ["circle", "rectangle", "v"]
GESTURE_TO_MOVE = {"circle": "rock", "rectangle": "paper", "v": "scissors"}
MOVES = ["rock", "paper", "scissors"]
BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

WIN_TARGET = 3
CONF_THRESH = 0.78  # min $1 score to accept a move
MIN_POINTS = 12

ICON_INK = (45, 45, 50)
ICON_DIM = (203, 203, 210)

THINK_DUR = 0.65   # CPU cycling through moves
HOLD_DUR = 0.45    # CPU holding its move before clash animation
CLASH_DUR = 0.55   # player and CPU choices slide together in the centers
FLOAT_DUR = 0.9    # +1 / -1 text rising under the score

ICON_Y = 405
ICON_SIZE = 130
YOU_REST, CPU_REST = 190, 410     # shapes start apart
YOU_CLASH, CPU_CLASH = 235, 365   # and slide together

DRAW, REVEAL = "draw", "reveal"


def rgba(rgb, a=255):
    return (*rgb, a)


def build_recognizer():
    # five wobbrock templates per class, each also reversed so the draw direction
    # does not matter, reusing the task 1 pipeline. only the three game gestures.
    helper = Recognizer([])
    templates = []
    for name in GESTURES:
        for path in _template_paths(name):
            pts = _preprocess(helper, _load_points(path))
            templates.append({"name": name, "points": pts})
            templates.append({"name": name, "points": pts[::-1]})
    return Recognizer(templates)


# --- game ---

class RockPaperScissors:
    def __init__(self):
        self.recognizer = build_recognizer()

        self.batch = pyglet.graphics.Batch()
        bg = pyglet.graphics.Group(order=0)
        fg = pyglet.graphics.Group(order=1)

        title = pyglet.text.Label(
            "Rock  Paper  Scissors", font_name=FONT, font_size=24,
            x=300, y=694, anchor_x="center", anchor_y="center",
            color=rgba(TEXT_DARK), batch=self.batch, group=fg)
        title.bold = True

        # scoreboard: a name each side and one pip per round needed to win
        self.you_hdr = pyglet.text.Label("YOU", font_name=FONT, font_size=17, x=168, y=652,
                                         anchor_x="center", anchor_y="center", color=rgba(TEXT_DARK),
                                         batch=self.batch, group=fg)
        self.cpu_hdr = pyglet.text.Label("CPU", font_name=FONT, font_size=17, x=432, y=652,
                                         anchor_x="center", anchor_y="center", color=rgba(TEXT_DARK),
                                         batch=self.batch, group=fg)
        self.you_hdr.bold = self.cpu_hdr.bold = True
        self.you_pips, self.cpu_pips = [], []
        for i in range(WIN_TARGET):
            self.you_pips.append(pyglet.shapes.Circle(214 + i * 26, 652, 8,
                                 color=ICON_DIM, batch=self.batch, group=fg))
            self.cpu_pips.append(pyglet.shapes.Circle(334 + i * 26, 652, 8,
                                 color=ICON_DIM, batch=self.batch, group=fg))

        pyglet.shapes.RoundedRectangle(
            CANVAS_X1 - 3, CANVAS_Y1 - 3, CANVAS_W + 6, CANVAS_H + 6, radius=18,
            color=CANVAS_BORDER, batch=self.batch, group=bg)
        pyglet.shapes.RoundedRectangle(
            CANVAS_X1, CANVAS_Y1, CANVAS_W, CANVAS_H, radius=16,
            color=CANVAS_FILL, batch=self.batch, group=bg)

        # shown while drawing
        self.draw_batch = pyglet.graphics.Batch()
        self.hint_lbl = pyglet.text.Label(
            "draw your move", font_name=FONT, font_size=20,
            x=300, y=(CANVAS_Y1 + CANVAS_Y2) // 2,
            anchor_x="center", anchor_y="center", color=rgba(TEXT_GRAY),
            batch=self.draw_batch)
        self.legend_lbl = pyglet.text.Label(
            "circle = rock      rectangle = paper      V = scissors",
            font_name=FONT, font_size=15, x=300, y=24,
            anchor_x="center", anchor_y="center", color=rgba(TEXT_GRAY),
            batch=self.draw_batch)

        # reveal overlay
        self.reveal_batch = pyglet.graphics.Batch()
        rt = pyglet.graphics.Group(order=1)
        panel = pyglet.shapes.Rectangle(
            CANVAS_X1, CANVAS_Y1, CANVAS_W, CANVAS_H, color=(247, 247, 250),
            batch=self.reveal_batch, group=pyglet.graphics.Group(order=0))
        panel.opacity = 242
        self.vs_lbl = pyglet.text.Label("vs", font_name=FONT, font_size=18, x=300, y=ICON_Y,
                                        anchor_x="center", anchor_y="center", color=rgba(TEXT_GRAY),
                                        batch=self.reveal_batch, group=rt)
        self.you_move_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=18, x=YOU_REST, y=312,
            anchor_x="center", anchor_y="center", color=rgba(TEXT_DARK),
            batch=self.reveal_batch, group=rt)
        self.cpu_move_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=18, x=CPU_REST, y=312,
            anchor_x="center", anchor_y="center", color=rgba(TEXT_DARK),
            batch=self.reveal_batch, group=rt)
        self.result_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=44, x=300, y=205,
            anchor_x="center", anchor_y="center", batch=self.reveal_batch, group=rt)
        self.result_lbl.bold = True
        self.prompt_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=16, x=300, y=112,
            anchor_x="center", anchor_y="center", color=rgba(TEXT_GRAY),
            batch=self.reveal_batch, group=rt)

        # floating +1 / -1, rises in the gap just below the score
        self.float_lbl = pyglet.text.Label(
            "", font_name=FONT, font_size=24, x=300, y=620,
            anchor_x="center", anchor_y="center", color=(0, 0, 0, 0))
        self.float_lbl.bold = True
        self.float_t = 0.0

        self.icon_batch = pyglet.graphics.Batch()
        self.icon_shapes = []
        self.stroke_batch = pyglet.graphics.Batch()
        self.stroke_lines = []

        self.restart()

    # --- state ---

    def restart(self):
        self.state = DRAW
        self.you_score = 0
        self.cpu_score = 0
        self.drawing = False
        self.points = []
        self.float_t = 0.0
        self._clear_stroke()
        self._update_score()

    def _update_score(self):
        for i, p in enumerate(self.you_pips):
            p.color = APPLE_GREEN if i < self.you_score else ICON_DIM
        for i, p in enumerate(self.cpu_pips):
            p.color = APPLE_RED if i < self.cpu_score else ICON_DIM

    def _start_reveal(self, you_move):
        self.you_move = you_move
        self.cpu_move = random.choice(MOVES)
        if you_move == self.cpu_move:
            self.winner = None
        elif BEATS[you_move] == self.cpu_move:
            self.winner = "you"
        else:
            self.winner = "cpu"
        self.state = REVEAL
        self.phase = "think"
        self.phase_t = 0.0
        self.settled = False
        self.match_over = False
        self.result_lbl.text = ""

    def _settle(self):
        if self.settled:
            return
        self.settled = True
        self.phase = "done"

        if self.winner == "you":
            self.you_score += 1
            self.result_lbl.text, color = "You win!", APPLE_GREEN
            self._float("+1", APPLE_GREEN)
        elif self.winner == "cpu":
            self.cpu_score += 1
            self.result_lbl.text, color = "You lose", APPLE_RED
            self._float("-1", APPLE_RED)
        else:
            self.result_lbl.text, color = "Draw", TEXT_GRAY
        self.result_lbl.color = rgba(color)
        self._update_score()

        if self.you_score == WIN_TARGET or self.cpu_score == WIN_TARGET:
            self.match_over = True
            won = self.you_score == WIN_TARGET
            self.result_lbl.text = "You won!" if won else "CPU won"
            self.result_lbl.color = rgba(APPLE_GREEN if won else APPLE_RED)
            self.prompt_lbl.text = "press space to play again"
        else:
            self.prompt_lbl.text = "press space for the next round"

    def _float(self, text, color):
        self.float_lbl.text = text
        self.float_base = color
        self.float_t = FLOAT_DUR

    def _next_round(self):
        self.state = DRAW
        self.hint_lbl.text = "draw your move"
        self.hint_lbl.color = rgba(TEXT_GRAY)
        self.prompt_lbl.text = ""
        self._clear_stroke()

    # --- animation ---

    def update(self, dt):
        if self.float_t > 0:
            self.float_t = max(0.0, self.float_t - dt)
            f = self.float_t / FLOAT_DUR
            self.float_lbl.y = 616 + (1 - f) * 24
            self.float_lbl.color = rgba(self.float_base, int(255 * f))

        if self.state != REVEAL:
            return
        self.phase_t += dt
        if self.phase == "think" and self.phase_t >= THINK_DUR:
            self.phase, self.phase_t = "hold", 0.0
        elif self.phase == "hold" and self.phase_t >= HOLD_DUR:
            self.phase, self.phase_t = "clash", 0.0
        elif self.phase == "clash" and self.phase_t >= CLASH_DUR:
            self._settle()
        self._build_icons()

    def _build_icons(self):
        if self.phase == "think":
            you_cx, cpu_cx = YOU_REST, CPU_REST
            you_shape = self.you_move
            cpu_shape = MOVES[int(self.phase_t / 0.08) % 3]   # cycle while thinking
        elif self.phase == "hold":
            you_cx, cpu_cx = YOU_REST, CPU_REST
            you_shape, cpu_shape = self.you_move, self.cpu_move
        elif self.phase == "clash":
            f = min(1.0, self.phase_t / CLASH_DUR)
            f = f * f * (3 - 2 * f)   # ease in-out
            you_cx = YOU_REST + (YOU_CLASH - YOU_REST) * f
            cpu_cx = CPU_REST + (CPU_CLASH - CPU_REST) * f
            you_shape, cpu_shape = self.you_move, self.cpu_move
        else:  # done
            you_cx, cpu_cx = YOU_CLASH, CPU_CLASH
            you_shape, cpu_shape = self.you_move, self.cpu_move

        you_ink = ICON_DIM if (self.phase == "done" and self.winner == "cpu") else ICON_INK
        cpu_ink = ICON_DIM if (self.phase == "done" and self.winner == "you") else ICON_INK

        # at the end the winning shape grows to mark the win
        you_size = cpu_size = ICON_SIZE
        if self.phase == "done" and self.winner:
            g = min(1.0, self.phase_t / 0.2)
            grown = ICON_SIZE * (1 + 0.22 * g * g * (3 - 2 * g))
            if self.winner == "you":
                you_size = grown
            else:
                cpu_size = grown

        batch = pyglet.graphics.Batch()
        shapes = self._draw_move(you_shape, you_cx, you_ink, batch, you_size)
        shapes += self._draw_move(cpu_shape, cpu_cx, cpu_ink, batch, cpu_size)
        self.icon_batch = batch
        self.icon_shapes = shapes

        self.you_move_lbl.x = you_cx
        self.cpu_move_lbl.x = cpu_cx
        self.you_move_lbl.text = self.you_move
        self.cpu_move_lbl.text = "?" if self.phase == "think" else self.cpu_move
        self.vs_lbl.color = rgba(TEXT_GRAY) if self.phase in ("think", "hold") else (0, 0, 0, 0)

    def _draw_move(self, move, cx, color, batch, s=ICON_SIZE):
        if move == "paper":
            w, h = s * 0.62, s * 0.72
            return [pyglet.shapes.Box(cx - w / 2, ICON_Y - h / 2, w, h,
                                      thickness=6, color=color, batch=batch)]
        if move == "rock":
            r = s * 0.4
            pts = [(cx + r * math.cos(a), ICON_Y + r * math.sin(a))
                   for a in [2 * math.pi * i / 48 for i in range(49)]]
            return [pyglet.shapes.Line(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1],
                                       6, color=color, batch=batch) for i in range(1, len(pts))]
        # scissors: a V with a dot at the joint so the corner is clean
        apex = (cx, ICON_Y - s * 0.32)
        left = (cx - s * 0.3, ICON_Y + s * 0.34)
        right = (cx + s * 0.3, ICON_Y + s * 0.34)
        return [pyglet.shapes.Line(left[0], left[1], apex[0], apex[1], 6, color=color, batch=batch),
                pyglet.shapes.Line(apex[0], apex[1], right[0], right[1], 6, color=color, batch=batch),
                pyglet.shapes.Circle(apex[0], apex[1], 3.2, color=color, batch=batch)]

    # --- input ---

    def _classify(self, points):
        # the $1 recognizer does its own resample/rotate/scale, just hand it the stroke
        return self.recognizer.recognize(points)

    def _evaluate(self):
        if len(self.points) < MIN_POINTS:
            self._clear_stroke()
            return
        gesture, conf = self._classify(self.points)
        if conf < CONF_THRESH:
            self.hint_lbl.text = "not sure, draw again"
            self.hint_lbl.color = rgba(APPLE_RED)
            self._clear_stroke()
            return
        self._start_reveal(GESTURE_TO_MOVE[gesture])

    def _clear_stroke(self):
        self.points = []
        self.stroke_lines = []
        self.stroke_batch = pyglet.graphics.Batch()

    def _in_canvas(self, x, y):
        return CANVAS_X1 <= x <= CANVAS_X2 and CANVAS_Y1 <= y <= CANVAS_Y2

    def _rebuild_stroke(self):
        self.stroke_batch = pyglet.graphics.Batch()
        self.stroke_lines = []
        for i in range(1, len(self.points)):
            p1, p2 = self.points[i - 1], self.points[i]
            self.stroke_lines.append(pyglet.shapes.Line(
                p1[0], p1[1], p2[0], p2[1], 3, color=rgba(APPLE_BLUE, 220),
                batch=self.stroke_batch))

    def on_mouse_press(self, x, y, button, modifiers):
        if self.state != DRAW or button != pyglet.window.mouse.LEFT or not self._in_canvas(x, y):
            return
        self.drawing = True
        self.points = [(x, y)]
        self.hint_lbl.color = (0, 0, 0, 0)
        self._rebuild_stroke()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if not self.drawing:
            return
        cx = max(CANVAS_X1, min(CANVAS_X2, x))
        cy = max(CANVAS_Y1, min(CANVAS_Y2, y))
        self.points.append((cx, cy))
        self._rebuild_stroke()

    def on_mouse_release(self, x, y, button, modifiers):
        if self.drawing:
            self.drawing = False
            self._evaluate()

    def advance(self):
        if self.state != REVEAL:
            return
        if self.phase != "done":
            self._settle() # skip animtion
        elif self.match_over:
            self.restart()
        else:
            self._next_round()

    def on_key_press(self, symbol, modifiers):
        key = pyglet.window.key
        if symbol == key.Q:
            pyglet.app.exit()
            os._exit(0)
        elif symbol in (key.SPACE, key.ENTER, key.RETURN):
            self.advance()

    def draw(self):
        self.batch.draw()
        if self.state == DRAW:
            self.draw_batch.draw()
            self.stroke_batch.draw()
        else:
            self.reveal_batch.draw()
            self.icon_batch.draw()
        if self.float_t > 0:
            self.float_lbl.draw()


def main():
    config = pyglet.gl.Config(sample_buffers=1, samples=4, double_buffer=True)
    try:
        win = pyglet.window.Window(WINDOW_W, WINDOW_H, caption="Rock Paper Scissors",
                                   resizable=False, config=config)
    except pyglet.window.NoSuchConfigException:
        win = pyglet.window.Window(WINDOW_W, WINDOW_H, caption="Rock Paper Scissors", resizable=False)
    pyglet.gl.glClearColor(*BG_GL)

    game = RockPaperScissors()

    @win.event
    def on_key_press(symbol, modifiers):
        game.on_key_press(symbol, modifiers)

    @win.event
    def on_mouse_press(x, y, button, modifiers):
        game.on_mouse_press(x, y, button, modifiers)

    @win.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        game.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    @win.event
    def on_mouse_release(x, y, button, modifiers):
        game.on_mouse_release(x, y, button, modifiers)

    @win.event
    def on_draw():
        win.clear()
        game.draw()

    pyglet.clock.schedule_interval(game.update, 1 / 60)
    try:
        pyglet.app.run()
    except KeyboardInterrupt:
        os._exit(0)


if __name__ == "__main__":
    main()
