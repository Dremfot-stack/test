#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
围棋 (Go / Weiqi) — 完整规则 + Tkinter 图形界面 + 自学习 AI

规则实现:
  * 9 / 13 / 19 路棋盘, 黑先白后交替落子
  * 气与提子: 无气之棋串被全部提掉
  * 禁止自杀 (含多子自杀)
  * 禁止全局同形 (位置超级劫, 覆盖单劫、循环劫等一切重复局面)
  * 停一手: 双方连续停一手即进入数目阶段
  * 认输
  * 数目: 中国规则数子法 — 点击标记死子后计分,
    黑 = 活子 + 黑地, 白 = 活子 + 白地 + 贴目 7.5
  * 悔棋 (可无限回溯)

AI (weiqi_ai.py):
  * 蒙特卡洛树搜索 (UCT) + 3x3 局部棋形胜率先验
  * 每局结束自动学习并持久化 (~/.local/share/weiqi/knowledge.json),
    同时保存 SGF 棋谱 → 越下越强
  * 支持 AI 自战循环训练

运行: python3 weiqi.py
快捷键: P = 停一手, U = 悔棋
"""

import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

import weiqi_ai

KOMI = weiqi_ai.KOMI
COLS = "ABCDEFGHJKLMNOPQRST"  # 19 路列名 (惯例跳过 I)

AI_LEVELS = {"弱": 0.8, "中": 2.5, "强": 6.0}


class GoGame:
    """规则引擎 (纯逻辑, 不依赖界面, 可单独测试)"""

    def __init__(self, size=19):
        self.size = size
        self.reset()

    def reset(self):
        n = self.size
        self.board = [[0] * n for _ in range(n)]  # 0 空 / 1 黑 / 2 白
        self.turn = 1
        self.passes = 0
        self.prisoners = {1: 0, 2: 0}       # 双方提子数
        self.last_move = None
        self.game_over = False
        self.scoring = False
        self.dead = set()                   # 数目阶段标记的死子坐标
        self.result = None
        self.winner = None
        self.history = []                   # 悔棋栈
        self.positions = {self._snapshot()}  # 全局同形检测 (超级劫)

    # ---------- 基础 ----------
    def _snapshot(self):
        return tuple(tuple(row) for row in self.board)

    def neighbors(self, x, y):
        n = self.size
        if x > 0:
            yield (x - 1, y)
        if x < n - 1:
            yield (x + 1, y)
        if y > 0:
            yield (x, y - 1)
        if y < n - 1:
            yield (x, y + 1)

    def group(self, x, y):
        """返回 (x,y) 所在棋串的 (坐标集合, 气数)"""
        color = self.board[y][x]
        if color == 0:
            return set(), 0
        seen, stack, libs = set(), [(x, y)], set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in seen:
                continue
            seen.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                c = self.board[ny][nx]
                if c == 0:
                    libs.add((nx, ny))
                elif c == color:
                    stack.append((nx, ny))
        return seen, len(libs)

    # ---------- 走子 ----------
    def play(self, x, y):
        """在 (x,y) 落子; 返回是否合法并已执行"""
        if self.game_over or self.scoring:
            return False
        if not (0 <= x < self.size and 0 <= y < self.size):
            return False
        if self.board[y][x] != 0:
            return False
        self._push()
        opp = 3 - self.turn
        self.board[y][x] = self.turn
        captured = 0
        for nx, ny in self.neighbors(x, y):
            if self.board[ny][nx] == opp:
                g, libs = self.group(nx, ny)
                if libs == 0:
                    for cx, cy in g:
                        self.board[cy][cx] = 0
                    captured += len(g)
        self.prisoners[self.turn] += captured
        # 禁自杀 (落子后己方棋串无气且未提掉对方子)
        g, libs = self.group(x, y)
        if libs == 0:
            self._pop()
            return False
        # 禁全局同形 (位置超级劫)
        snap = self._snapshot()
        if snap in self.positions:
            self._pop()
            return False
        self.positions.add(snap)
        self.last_move = (x, y)
        self.turn = opp
        self.passes = 0
        return True

    def pass_turn(self):
        """停一手; 双方连续停一手后进入数目阶段"""
        if self.game_over or self.scoring:
            return
        self._push()
        self.passes += 1
        self.last_move = None
        self.turn = 3 - self.turn
        if self.passes >= 2:
            self.scoring = True

    def resign(self, player):
        """player 认输, 对方获胜"""
        if self.game_over:
            return
        self.game_over = True
        self.scoring = False
        self.winner = 3 - player

    # ---------- 悔棋 ----------
    def _push(self):
        self.history.append((
            self._snapshot(), self.turn, self.passes,
            dict(self.prisoners), self.last_move, set(self.positions),
        ))

    def _pop(self):
        snap, turn, passes, prisoners, last, positions = self.history.pop()
        self.board = [list(row) for row in snap]
        self.turn = turn
        self.passes = passes
        self.prisoners = prisoners
        self.last_move = last
        self.positions = positions

    def undo(self):
        """悔一步 (含停一手); 数目阶段返回对局"""
        if not self.history:
            return False
        self._pop()
        self.game_over = False
        self.scoring = False
        self.dead = set()
        self.result = None
        self.winner = None
        return True

    # ---------- 数目 (中国规则) ----------
    def toggle_dead(self, x, y):
        """数目阶段: 点击棋子, 切换其所在整块棋的死/活标记"""
        if not self.scoring:
            return
        if self.board[y][x] == 0:
            return
        g, _ = self.group(x, y)
        if g <= self.dead:
            self.dead -= g
        else:
            self.dead |= g

    def compute_score(self):
        """数子法计分: 死子移除后, 黑 = 活子 + 黑地; 白 = 活子 + 白地 + 贴目"""
        board = [row[:] for row in self.board]
        for x, y in self.dead:
            board[y][x] = 0
        n = self.size
        visited = set()
        terr = {1: 0, 2: 0}
        for y in range(n):
            for x in range(n):
                if board[y][x] == 0 and (x, y) not in visited:
                    region, stack, border = set(), [(x, y)], set()
                    while stack:
                        cx, cy = stack.pop()
                        if (cx, cy) in region:
                            continue
                        region.add((cx, cy))
                        for nx, ny in self.neighbors(cx, cy):
                            c = board[ny][nx]
                            if c == 0:
                                stack.append((nx, ny))
                            else:
                                border.add(c)
                    visited |= region
                    if len(border) == 1:
                        terr[next(iter(border))] += len(region)
        black_stones = sum(row.count(1) for row in board)
        white_stones = sum(row.count(2) for row in board)
        black_total = black_stones + terr[1]
        white_total = white_stones + terr[2] + KOMI
        self.result = {
            "black_stones": black_stones,
            "white_stones": white_stones,
            "black_territory": terr[1],
            "white_territory": terr[2],
            "black_total": black_total,
            "white_total": white_total,
            "komi": KOMI,
        }
        self.game_over = True
        self.scoring = False
        if black_total > white_total:
            self.winner = 1
        elif white_total > black_total:
            self.winner = 2
        else:
            self.winner = 0
        return self.result


class GoGUI:
    """Tkinter 图形界面 (含 AI 集成)"""

    def __init__(self, root):
        self.root = root
        self.game = GoGame(19)
        self.cell = 36          # 相邻交叉点像素间距
        self.margin = 44        # 棋盘边距
        self.hover = None       # 悬停预览坐标
        self.ai = weiqi_ai.Knowledge()
        self.ai_thread = None
        self.ai_result = None
        self.ai_game_ref = None
        self.ai_thinking = False
        self.record = []        # 对局记录: (x,y,color) | (None,None,color)
        self.learned = False    # 本局是否已完成学习
        self._build()
        self._update_ai_info()
        self.refresh()

    # ---------- 界面搭建 ----------
    def _build(self):
        self.root.title("围棋 Go — 中国规则 · 贴目 7.5 · 自学习 AI")
        self.root.resizable(False, False)
        self.root.configure(bg="#2b2b2b")

        self.canvas = tk.Canvas(self.root, bg="#E3BA6E", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=(12, 0), pady=12)

        panel = tk.Frame(self.root, bg="#2b2b2b", padx=14, pady=14)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(panel, text="当前落子", bg="#2b2b2b", fg="#cccccc",
                 font=("Sans", 11)).pack()
        self.player_canvas = tk.Canvas(panel, width=56, height=56,
                                       bg="#2b2b2b", highlightthickness=0)
        self.player_canvas.pack(pady=(4, 10))

        self.info_var = tk.StringVar()
        tk.Label(panel, textvariable=self.info_var, bg="#2b2b2b",
                 fg="#e8e8e8", font=("Sans", 11),
                 justify=tk.LEFT).pack(anchor="w", pady=2)

        self.status_var = tk.StringVar()
        tk.Label(panel, textvariable=self.status_var, bg="#2b2b2b",
                 fg="#f0c674", font=("Sans", 10), wraplength=180,
                 justify=tk.LEFT).pack(anchor="w", pady=(6, 10))

        self.btn_pass = tk.Button(panel, text="停一手 (P)",
                                  command=self.on_pass, width=15)
        self.btn_pass.pack(pady=3)
        self.btn_resign = tk.Button(panel, text="认输",
                                    command=self.on_resign, width=15)
        self.btn_resign.pack(pady=3)
        self.btn_undo = tk.Button(panel, text="悔棋 (U)",
                                  command=self.on_undo, width=15)
        self.btn_undo.pack(pady=3)
        self.btn_score = tk.Button(panel, text="确认计分",
                                   command=self.on_confirm_score, width=15,
                                   state=tk.DISABLED)
        self.btn_score.pack(pady=3)
        self.btn_resume = tk.Button(panel, text="返回对局",
                                    command=self.on_resume, width=15,
                                    state=tk.DISABLED)
        self.btn_resume.pack(pady=3)
        self.btn_new = tk.Button(panel, text="新对局",
                                 command=self.on_new_game, width=15)
        self.btn_new.pack(pady=3)

        tk.Label(panel, text="棋盘大小", bg="#2b2b2b", fg="#cccccc",
                 font=("Sans", 10)).pack(pady=(16, 0))
        self.size_var = tk.StringVar(value="19")
        om = tk.OptionMenu(panel, self.size_var, "19", "13", "9",
                           command=lambda _v: self.on_new_game())
        om.config(width=13)
        om.pack(pady=4)

        tk.Label(panel, text="对局模式", bg="#2b2b2b", fg="#cccccc",
                 font=("Sans", 10)).pack(pady=(8, 0))
        self.mode_var = tk.StringVar(value="双人对弈")
        om2 = tk.OptionMenu(panel, self.mode_var,
                            "双人对弈", "人执黑 · AI执白",
                            "人执白 · AI执黑", "AI 自战",
                            command=lambda _v: self.on_new_game())
        om2.config(width=13)
        om2.pack(pady=4)

        tk.Label(panel, text="AI 强度", bg="#2b2b2b", fg="#cccccc",
                 font=("Sans", 10)).pack(pady=(8, 0))
        self.level_var = tk.StringVar(value="中")
        om3 = tk.OptionMenu(panel, self.level_var, "弱", "中", "强")
        om3.config(width=13)
        om3.pack(pady=4)

        self.ai_info_var = tk.StringVar()
        tk.Label(panel, textvariable=self.ai_info_var, bg="#2b2b2b",
                 fg="#8fd3a7", font=("Sans", 9), wraplength=180,
                 justify=tk.LEFT).pack(anchor="w", pady=(16, 0))

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda _e: self._set_hover(None))
        self.root.bind("p", lambda _e: self.on_pass())
        self.root.bind("P", lambda _e: self.on_pass())
        self.root.bind("u", lambda _e: self.on_undo())
        self.root.bind("U", lambda _e: self.on_undo())
        self._resize_canvas()

    def _resize_canvas(self):
        n = self.game.size
        px = self.margin * 2 + self.cell * (n - 1)
        self.canvas.config(width=px, height=px)

    # ---------- 绘制 ----------
    def _star_points(self):
        n = self.game.size
        pts = {19: [3, 9, 15], 13: [3, 9], 9: [2, 6]}[n]
        stars = [(a, b) for a in pts for b in pts]
        if n in (9, 13):
            stars.append((n // 2, n // 2))
        return stars

    def draw(self):
        c = self.canvas
        c.delete("all")
        n = self.game.size
        cell, m = self.cell, self.margin
        px = m * 2 + cell * (n - 1)
        edge = cell // 2
        c.create_rectangle(0, 0, px, px, fill="#E3BA6E", outline="")
        c.create_rectangle(m - edge, m - edge,
                           m + (n - 1) * cell + edge,
                           m + (n - 1) * cell + edge,
                           outline="#7a5230", width=3)
        for i in range(n):
            p = m + i * cell
            c.create_line(m, p, m + (n - 1) * cell, p, fill="#5b4326")
            c.create_line(p, m, p, m + (n - 1) * cell, fill="#5b4326")
        for sx, sy in self._star_points():
            x, y = m + sx * cell, m + sy * cell
            c.create_oval(x - 4, y - 4, x + 4, y + 4,
                          fill="#3d2f1c", outline="")
        for i in range(n):
            p = m + i * cell
            c.create_text(p, m - edge - 12, text=COLS[i],
                          fill="#5b4326", font=("Arial", 9))
            c.create_text(p, m + (n - 1) * cell + edge + 12, text=COLS[i],
                          fill="#5b4326", font=("Arial", 9))
            c.create_text(m - edge - 14, p, text=str(n - i),
                          fill="#5b4326", font=("Arial", 9))
            c.create_text(m + (n - 1) * cell + edge + 14, p, text=str(n - i),
                          fill="#5b4326", font=("Arial", 9))
        for y in range(n):
            for x in range(n):
                v = self.game.board[y][x]
                if v:
                    self._stone(x, y, v)
        for x, y in self.game.dead:
            sx, sy = m + x * cell, m + y * cell
            r = cell * 0.46
            c.create_line(sx - r, sy - r, sx + r, sy + r,
                          fill="#d22", width=2)
            c.create_line(sx + r, sy - r, sx - r, sy + r,
                          fill="#d22", width=2)
        if self.game.last_move and not self.game.scoring:
            x, y = self.game.last_move
            sx, sy = m + x * cell, m + y * cell
            v = self.game.board[y][x]
            dot = "#eee" if v == 1 else "#222"
            c.create_oval(sx - 4, sy - 4, sx + 4, sy + 4,
                          fill=dot, outline="")
        if (self.hover and not self.game.game_over
                and not self.ai_thinking):
            x, y = self.hover
            if self.game.board[y][x] == 0:
                self._stone(x, y, self.game.turn, ghost=True)

    def _stone(self, x, y, color, ghost=False):
        c, m = self.cell, self.margin
        sx, sy = m + x * c, m + y * c
        r = c * 0.46
        if ghost:
            fill = "#333" if color == 1 else "#fff"
            self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                    fill=fill, outline="#666",
                                    stipple="gray50")
            return
        if color == 1:
            self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                    fill="#1d1d1d", outline="#000")
            self.canvas.create_oval(sx - r * 0.6, sy - r * 0.65,
                                    sx - r * 0.05, sy - r * 0.1,
                                    fill="#555", outline="")
        else:
            self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                    fill="#fafafa", outline="#8a8a8a")
            self.canvas.create_oval(sx - r * 0.55, sy - r * 0.6,
                                    sx - r * 0.05, sy - r * 0.1,
                                    fill="#ffffff", outline="")

    # ---------- 事件 ----------
    def _grid_at(self, px, py):
        n, c, m = self.game.size, self.cell, self.margin
        gx = round((px - m) / c)
        gy = round((py - m) / c)
        if 0 <= gx < n and 0 <= gy < n:
            ox, oy = m + gx * c, m + gy * c
            if (px - ox) ** 2 + (py - oy) ** 2 <= (c * 0.48) ** 2:
                return gx, gy
        return None

    def on_motion(self, ev):
        self._set_hover(self._grid_at(ev.x, ev.y))

    def _set_hover(self, pos):
        if pos != self.hover:
            self.hover = pos
            self.draw()

    def on_click(self, ev):
        pos = self._grid_at(ev.x, ev.y)
        if not pos:
            return
        x, y = pos
        g = self.game
        if g.scoring:
            g.toggle_dead(x, y)
            self.refresh()
            return
        if g.game_over:
            return
        if self.ai_thinking or self._ai_to_move():
            self.refresh(flash="AI 回合 / 思考中, 请稍候")
            return
        mover = g.turn
        if g.play(x, y):
            self.record.append((x, y, mover))
            self.refresh()
            self.maybe_ai_move()
        else:
            self.refresh(flash="非法落子: 自杀或全局同形(劫)均被禁止")

    def on_pass(self):
        g = self.game
        if g.game_over or self.ai_thinking or self._ai_to_move():
            return
        mover = g.turn
        g.pass_turn()
        self.record.append((None, None, mover))
        if g.scoring:
            self.refresh(flash="双方停手, 进入数目阶段:\n"
                               "点击棋子标记死子, 再点[确认计分]")
        else:
            self.refresh()
            self.maybe_ai_move()

    def on_resign(self):
        g = self.game
        if g.game_over or self.ai_thinking:
            return
        name = "黑棋" if g.turn == 1 else "白棋"
        if messagebox.askyesno("认输", f"{name}确定认输吗?"):
            g.resign(g.turn)
            self._finalize_game()
            self.refresh()
            self._announce()

    def on_undo(self):
        if self.ai_thinking or self.game.scoring:
            return
        if self.game.undo():
            if self.record:
                self.record.pop()
            self.refresh()
        else:
            self.refresh(flash="已无棋可悔")

    def on_resume(self):
        """数目阶段返回对局 (撤销最后一次停一手)"""
        if self.game.scoring and self.game.undo():
            if self.record:
                self.record.pop()
            self.refresh()

    def on_confirm_score(self):
        if not self.game.scoring:
            return
        self.game.compute_score()
        self._finalize_game()
        self.refresh()
        self._announce()

    def on_new_game(self, silent=False):
        g = self.game
        played = any(v for row in g.board for v in row)
        if played and not g.game_over and not silent:
            if not messagebox.askyesno("新对局", "当前对局尚未结束, 确定重新开始?"):
                return
        self.ai_thread = None
        self.ai_thinking = False
        self.ai_result = None
        self.ai_game_ref = None
        self.game = GoGame(int(self.size_var.get()))
        self.record = []
        self.learned = False
        self.hover = None
        self._resize_canvas()
        self.refresh()
        self.maybe_ai_move()

    # ---------- AI ----------
    def _ai_to_move(self):
        mode = self.mode_var.get()
        if mode == "双人对弈":
            return False
        if mode == "AI 自战":
            return True
        g = self.game
        if mode == "人执黑 · AI执白":
            return g.turn == 2
        if mode == "人执白 · AI执黑":
            return g.turn == 1
        return False

    def maybe_ai_move(self):
        g = self.game
        if g.game_over or g.scoring:
            return
        if self.ai_thread is not None:
            return
        if not self._ai_to_move():
            return
        self.ai_thinking = True
        self.ai_game_ref = g
        self.ai_result = None
        mode = self.mode_var.get()
        level = self.level_var.get()
        self.ai_thread = threading.Thread(
            target=self._ai_think, args=(mode, level), daemon=True)
        self.ai_thread.start()
        self.refresh()
        self.root.after(120, self._poll_ai)

    def _ai_think(self, mode, level):
        g = self.game
        board = [row[:] for row in g.board]
        size, turn = g.size, g.turn
        budget = AI_LEVELS.get(level, 2.5)
        if size <= 9:
            budget *= 1.5
        elif size == 13:
            budget *= 1.2
        if mode == "AI 自战":
            budget = min(budget, 1.0)  # 自战训练保持节奏
        temperature = 0.5 if mode == "AI 自战" else 0.0
        mcts = weiqi_ai.MCTS(self.ai, cpuct=1.2)
        debug = os.environ.get("WEIQI_AI_DEBUG") == "1"
        self.ai_result = mcts.search(board, size, turn,
                                     budget=budget, temperature=temperature,
                                     debug=debug)

    def _poll_ai(self):
        if self.ai_thread and self.ai_thread.is_alive():
            self.root.after(120, self._poll_ai)
            return
        move = self.ai_result
        self.ai_thread = None
        self.ai_thinking = False
        g = self.game
        if self.ai_game_ref is not g or g.game_over or g.scoring:
            self.refresh()
            return
        if move is None:
            self.record.append((None, None, g.turn))
            g.pass_turn()
        elif g.play(move[0], move[1]):
            self.record.append((move[0], move[1], 3 - g.turn))
        else:
            self.record.append((None, None, g.turn))
            g.pass_turn()
        self.refresh()
        if g.scoring:
            if self.mode_var.get() == "AI 自战":
                self._auto_score_selfplay()
            else:
                self.refresh(flash="双方停手, 进入数目阶段:\n"
                                   "点击棋子标记死子, 再点[确认计分]")
            return
        self.maybe_ai_move()

    def _auto_score_selfplay(self):
        """自战模式自动计分: 单气棋串按死子处理 (训练用简化启发)"""
        g = self.game
        if not g.scoring:
            return
        for y in range(g.size):
            for x in range(g.size):
                if g.board[y][x]:
                    grp, libs = g.group(x, y)
                    if libs <= 1:
                        g.dead |= grp
        g.compute_score()
        self._finalize_game()
        self.refresh()
        self.root.after(1600, self._selfplay_next)

    def _selfplay_next(self):
        if self.mode_var.get() == "AI 自战":
            self.on_new_game(silent=True)

    # ---------- 学习与棋谱 ----------
    def _finalize_game(self):
        if self.learned:
            return
        g = self.game
        if not g.game_over or g.winner is None:
            return
        self.learned = True
        feats = weiqi_ai.extract_moves(g.size, self.record)
        self.ai.update(feats, g.winner)
        self.ai.save()
        self._save_sgf(g.winner)
        self._update_ai_info()

    def _save_sgf(self, winner):
        g = self.game
        try:
            os.makedirs(weiqi_ai.GAMES_DIR, exist_ok=True)
            name = time.strftime("%Y%m%d-%H%M%S") + f"-{g.size}x{g.size}.sgf"
            lines = [f"(;FF[4]GM[1]SZ[{g.size}]KM[{KOMI}]PB[黑棋]PW[白棋]"]
            for x, y, c in self.record:
                col = COLS[x] if x is not None else ""
                row = g.size - y if y is not None else ""
                lines.append(f"{'B' if c == 1 else 'W'}[{col}{row}]")
            lines.append(f"RE[{'B+R' if winner == 1 else 'W+R'}]")
            lines.append(")")
            with open(os.path.join(weiqi_ai.GAMES_DIR, name),
                      "w", encoding="utf-8") as f:
                f.write("".join(lines))
        except OSError:
            pass

    def _update_ai_info(self):
        try:
            n_games = len(os.listdir(weiqi_ai.GAMES_DIR))
        except OSError:
            n_games = 0
        self.ai_info_var.set(
            f"AI 已学习棋形: {len(self.ai)} 种\n"
            f"已存棋谱: {n_games} 局\n"
            f"(知识库: {weiqi_ai.KB_FILE})"
        )

    # ---------- 刷新 ----------
    def refresh(self, flash=None):
        g = self.game
        pc = self.player_canvas
        pc.delete("all")
        if g.turn == 1:
            pc.create_oval(10, 10, 46, 46, fill="#1d1d1d",
                           outline="#000", width=2)
        else:
            pc.create_oval(10, 10, 46, 46, fill="#fafafa",
                           outline="#8a8a8a", width=2)
        self.info_var.set(
            f"黑棋提子: {g.prisoners[1]}\n"
            f"白棋提子: {g.prisoners[2]}\n"
            f"贴目: {KOMI}"
        )
        if g.game_over:
            st = "对局已结束"
        elif self.ai_thinking:
            st = "AI 思考中…"
        elif g.scoring:
            st = "数目阶段:\n点击棋子标记/取消死子,\n然后点[确认计分]"
        else:
            name = "黑棋" if g.turn == 1 else "白棋"
            st = f"{name}落子"
            if g.passes == 1:
                st += "\n(对方已停一手)"
        self.status_var.set(flash or st)
        busy = self.ai_thinking
        self.btn_score.config(state=tk.NORMAL if g.scoring else tk.DISABLED)
        self.btn_resume.config(state=tk.NORMAL if g.scoring else tk.DISABLED)
        self.btn_undo.config(
            state=tk.NORMAL if (g.history and not g.game_over
                                and not g.scoring and not busy)
            else tk.DISABLED)
        self.btn_resign.config(
            state=tk.NORMAL if (not g.game_over and not busy) else tk.DISABLED)
        self.btn_pass.config(
            state=tk.NORMAL if (not g.game_over and not busy) else tk.DISABLED)
        self.draw()

    def _announce(self):
        g = self.game
        if g.result:
            r = g.result
            msg = (
                f"黑棋: 活子 {r['black_stones']} + 地域 {r['black_territory']}"
                f" = {r['black_total']}\n"
                f"白棋: 活子 {r['white_stones']} + 地域 {r['white_territory']}"
                f" + 贴目 {r['komi']} = {r['white_total']}\n\n"
            )
        else:
            msg = ""
        if g.winner == 1:
            msg += "黑棋获胜!"
        elif g.winner == 2:
            msg += "白棋获胜!"
        else:
            msg += "和棋"
        messagebox.showinfo("对局结果", msg)


def main():
    root = tk.Tk()
    GoGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
