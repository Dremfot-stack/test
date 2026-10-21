#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
翻翻乐 (Lights Out 图论版) — 10 个关卡

规则:
  * 每个节点有两种状态 (亮/暗)
  * 点击一个节点: 该节点 + 所有与它相连的节点 一起翻转状态
  * 目标: 让所有节点状态相同 (全亮或全暗均可)

关卡: 三连星 → 正方形环 → 六环 → 七环 → 五角星 → 八宫格
      → 九宫格 → 十宫格 → 十二宫格 → 十六宫格
每关的初始局面由全状态空间 BFS 选定 —— 取"离全同状态最远"的合法局面
(即该图形下最难的一关), 并经双向 BFS 独立验证, 保证有解且难度最大。

运行: python3 flip_game.py
"""

import json
import math
import os
import threading
import tkinter as tk
from collections import deque
from tkinter import messagebox

DATA_DIR = os.path.expanduser("~/.local/share/flip_game")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")

CANVAS = 480
CENTER = CANVAS // 2
NODE_R = 21


# ==================== 关卡定义 ====================

def ring_positions(n, cx=CENTER, cy=CENTER, r=150, rot=-90):
    """圆环上均布 n 个点"""
    return [
        (cx + r * math.cos(math.radians(rot + 360 * i / n)),
         cy + r * math.sin(math.radians(rot + 360 * i / n)))
        for i in range(n)
    ]


def grid_graph(w, h):
    """矩形网格图: 返回 (节点坐标, 边列表)"""
    nodes, edges, idx = [], [], {}
    spacing = 340 // max(w, h)
    off_x = CENTER - (w - 1) * spacing / 2
    off_y = CENTER - (h - 1) * spacing / 2
    for r in range(h):
        for c in range(w):
            idx[(r, c)] = len(nodes)
            nodes.append((off_x + c * spacing, off_y + r * spacing))
    for r in range(h):
        for c in range(w):
            a = idx[(r, c)]
            if c + 1 < w:
                edges.append((a, idx[(r, c + 1)]))
            if r + 1 < h:
                edges.append((a, idx[(r + 1, c)]))
    return nodes, edges


def build_graphs():
    """10 个关卡图: (名称, 节点坐标, 边)"""
    G = []
    # 1 三连星 (3 节点路径图)
    G.append(("三连星", [(150, CENTER), (CENTER, CENTER), (330, CENTER)],
              [(0, 1), (1, 2)]))
    # 2 正方形环
    G.append(("正方形环", ring_positions(4),
              [(0, 1), (1, 2), (2, 3), (3, 0)]))
    # 3 六环
    G.append(("六环", ring_positions(6),
              [(i, (i + 1) % 6) for i in range(6)]))
    # 4 七环
    G.append(("七环", ring_positions(7),
              [(i, (i + 1) % 7) for i in range(7)]))
    # 5 五角星 (中心 + 4 叶)
    nodes = [(CENTER, CENTER)] + ring_positions(4, r=140)
    G.append(("五角星", nodes, [(0, 1), (0, 2), (0, 3), (0, 4)]))
    # 6 八宫格 (2x4)
    nodes, edges = grid_graph(2, 4)
    G.append(("八宫格", nodes, edges))
    # 7 九宫格 (3x3, 经典 Lights Out)
    nodes, edges = grid_graph(3, 3)
    G.append(("九宫格", nodes, edges))
    # 8 十宫格 (2x5)
    nodes, edges = grid_graph(2, 5)
    G.append(("十宫格", nodes, edges))
    # 9 十二宫格 (3x4)
    nodes, edges = grid_graph(3, 4)
    G.append(("十二宫格", nodes, edges))
    # 10 十六宫格 (4x4)
    nodes, edges = grid_graph(4, 4)
    G.append(("十六宫格", nodes, edges))
    return G


# 各关初始局面: 由全状态空间 BFS 选出的"离全同状态最远"的合法局面,
# 并经双向 BFS 独立验证 (三连星2步, 正方形环2步, 六环3步, 七环3步,
# 五角星4步, 八宫格6步, 九宫格6步, 十宫格6步, 十二宫格7步, 十六宫格6步)
INITIALS = [0b101, 0b1100, 0b101010, 0b1001010, 0b11110,
            0b00001111, 0b010000111, 0b1100001111,
            0b010000111101, 0b0000001110110101]


class Level:
    """一个关卡: 图结构 + 已验证可解的初始局面"""

    def __init__(self, idx, name, nodes, edges, initial):
        self.idx = idx
        self.name = name
        self.n = len(nodes)
        self.nodes = nodes
        self.edges = edges
        adj = [[] for _ in range(self.n)]
        for a, b in edges:
            adj[a].append(b)
            adj[b].append(a)
        self.masks = []  # masks[i]: 点击 i 影响的位掩码
        for i in range(self.n):
            m = 1 << i
            for j in adj[i]:
                m |= 1 << j
            self.masks.append(m)
        self.initial = initial


def build_levels():
    return [
        Level(i + 1, name, nodes, edges, INITIALS[i])
        for i, (name, nodes, edges) in enumerate(build_graphs())
    ]


def min_moves(state, masks, n):
    """BFS 求最少步数 (同时验证可解性); 无解返回 None"""
    full = (1 << n) - 1
    if state == 0 or state == full:
        return 0
    seen = {state: 0}
    q = deque([state])
    while q:
        s = q.popleft()
        d = seen[s] + 1
        for m in masks:
            t = s ^ m
            if t == 0 or t == full:
                return d
            if t not in seen:
                seen[t] = d
                q.append(t)
    return None


# ==================== 图形界面 ====================

class FlipGame:
    def __init__(self, root):
        self.root = root
        self.levels = build_levels()
        self.progress = self._load_progress()
        self.level = 0
        self.state = 0
        self.moves = 0
        self.history = []
        self.hover = None
        self.min_cache = {}
        self._min_thread = None
        self._min_result = None
        self.quiet = False  # 测试时置 True, 跳过弹窗
        self._build()
        self.load_level(0)

    # ---------- 进度持久化 ----------
    def _load_progress(self):
        try:
            with open(PROGRESS_FILE) as f:
                d = json.load(f)
            return {int(k): v for k, v in d.items()}
        except (OSError, ValueError):
            return {}

    def _save_progress(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(PROGRESS_FILE, "w") as f:
                json.dump({str(k): v for k, v in self.progress.items()}, f)
        except OSError:
            pass

    # ---------- 界面 ----------
    def _build(self):
        self.root.title("翻翻乐 · Lights Out")
        self.root.resizable(False, False)
        self.root.configure(bg="#2b2b2b")

        self.canvas = tk.Canvas(self.root, width=CANVAS, height=CANVAS,
                                bg="#22252b", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=(12, 0), pady=12)

        panel = tk.Frame(self.root, bg="#2b2b2b", padx=14, pady=14)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(panel, text="关卡", bg="#2b2b2b", fg="#cccccc",
                 font=("Sans", 11)).pack(anchor="w")
        self.listbox = tk.Listbox(panel, width=16, height=10,
                                  bg="#33373f", fg="#e8e8e8",
                                  selectbackground="#5a7d9a",
                                  font=("Sans", 11))
        self.listbox.pack(pady=(4, 10))
        self.listbox.bind("<<ListboxSelect>>", self.on_select_level)

        self.moves_var = tk.StringVar()
        tk.Label(panel, textvariable=self.moves_var, bg="#2b2b2b",
                 fg="#e8e8e8", font=("Sans", 12)).pack(anchor="w")
        self.min_var = tk.StringVar()
        tk.Label(panel, textvariable=self.min_var, bg="#2b2b2b",
                 fg="#8fd3a7", font=("Sans", 10)).pack(anchor="w", pady=2)

        self.status_var = tk.StringVar()
        tk.Label(panel, textvariable=self.status_var, bg="#2b2b2b",
                 fg="#f0c674", font=("Sans", 10), wraplength=170,
                 justify=tk.LEFT).pack(anchor="w", pady=(8, 10))

        tk.Button(panel, text="重来", command=self.on_restart,
                  width=14).pack(pady=3)
        tk.Button(panel, text="悔棋", command=self.on_undo,
                  width=14).pack(pady=3)
        frm = tk.Frame(panel, bg="#2b2b2b")
        frm.pack(pady=3)
        tk.Button(frm, text="◀ 上一关", command=lambda: self.load_level(
            self.level - 1), width=7).pack(side=tk.LEFT, padx=2)
        tk.Button(frm, text="下一关 ▶", command=lambda: self.load_level(
            self.level + 1), width=7).pack(side=tk.LEFT, padx=2)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda _e: self._set_hover(None))
        self._refresh_list()

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, lv in enumerate(self.levels):
            star = " ★" if self.progress.get(lv.idx, {}).get("solved") else ""
            self.listbox.insert(tk.END, f"{lv.idx}. {lv.name}{star}")
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(self.level)

    # ---------- 关卡加载 ----------
    def load_level(self, idx):
        if not (0 <= idx < len(self.levels)):
            return
        self.level = idx
        lv = self.levels[idx]
        self.state = lv.initial
        self.moves = 0
        self.history = []
        self.hover = None
        self.moves_var.set(f"步数: {self.moves}")
        if idx in self.min_cache:
            self.min_var.set(f"最少步数: {self.min_cache[idx]}")
        else:
            self.min_var.set("最少步数: 计算中…")
        self.status_var.set(f"点击节点翻转它及相连节点,\n使所有节点同色")
        self._refresh_list()
        self._draw()
        self._async_min()

    def _async_min(self):
        idx = self.level
        if idx in self.min_cache:
            return
        if self._min_thread and self._min_thread.is_alive():
            return
        lv = self.levels[idx]
        self._min_result = None
        self._min_thread = threading.Thread(
            target=lambda: self._min_worker(idx, lv), daemon=True)
        self._min_thread.start()
        self.root.after(120, self._poll_min)

    def _min_worker(self, idx, lv):
        self._min_result = (idx, min_moves(lv.initial, lv.masks, lv.n))

    def _poll_min(self):
        if self._min_thread and self._min_thread.is_alive():
            self.root.after(120, self._poll_min)
            return
        if self._min_result:
            idx, m = self._min_result
            self._min_result = None
            if m is not None:
                self.min_cache[idx] = m
            if idx == self.level:
                self.min_var.set(
                    f"最少步数: {m}" if m is not None else "最少步数: 无解")

    # ---------- 逻辑 ----------
    def _flip(self, i):
        lv = self.levels[self.level]
        self.state ^= lv.masks[i]
        self.moves += 1
        self.history.append(i)

    def _uniform(self):
        lv = self.levels[self.level]
        full = (1 << lv.n) - 1
        return self.state == 0 or self.state == full

    def _check_win(self):
        if not self._uniform():
            return
        lv = self.levels[self.level]
        entry = self.progress.setdefault(lv.idx, {"solved": False, "best": None})
        entry["solved"] = True
        if entry["best"] is None or self.moves < entry["best"]:
            entry["best"] = self.moves
        self._save_progress()
        self._refresh_list()
        self.status_var.set(f"过关! 用了 {self.moves} 步")
        if not self.quiet:
            msg = f"恭喜过关!\n本次用了 {self.moves} 步"
            if self.min_cache.get(self.level) is not None:
                msg += f" (最少 {self.min_cache[self.level]} 步)"
            messagebox.showinfo("过关!", msg)

    # ---------- 事件 ----------
    def on_click(self, ev):
        i = self._node_at(ev.x, ev.y)
        if i is None or self._uniform():
            return
        self._flip(i)
        self.moves_var.set(f"步数: {self.moves}")
        self._draw()
        self._check_win()

    def on_motion(self, ev):
        self._set_hover(self._node_at(ev.x, ev.y))

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self._draw()

    def _node_at(self, px, py):
        lv = self.levels[self.level]
        best, best_d = None, NODE_R + 8
        for i, (x, y) in enumerate(lv.nodes):
            d = math.hypot(px - x, py - y)
            if d < best_d:
                best, best_d = i, d
        return best

    def on_restart(self):
        lv = self.levels[self.level]
        self.state = lv.initial
        self.moves = 0
        self.history = []
        self.moves_var.set(f"步数: {self.moves}")
        self.status_var.set(f"点击节点翻转它及相连节点,\n使所有节点同色")
        self._draw()

    def on_undo(self):
        if not self.history:
            return
        lv = self.levels[self.level]
        i = self.history.pop()
        self.state ^= lv.masks[i]
        self.moves -= 1
        self.moves_var.set(f"步数: {self.moves}")
        self._draw()

    def on_select_level(self, _ev):
        sel = self.listbox.curselection()
        if sel:
            self.load_level(sel[0])

    # ---------- 绘制 ----------
    def _draw(self):
        c = self.canvas
        c.delete("all")
        lv = self.levels[self.level]
        for a, b in lv.edges:
            x1, y1 = lv.nodes[a]
            x2, y2 = lv.nodes[b]
            c.create_line(x1, y1, x2, y2, fill="#7d8594", width=3)
        for i, (x, y) in enumerate(lv.nodes):
            on = (self.state >> i) & 1
            fill = "#ffcf4d" if on else "#454c5c"
            outline = "#d9a520" if on else "#6b7484"
            c.create_oval(x - NODE_R, y - NODE_R, x + NODE_R, y + NODE_R,
                          fill=fill, outline=outline, width=2)
            if i == self.hover:
                c.create_oval(x - NODE_R - 5, y - NODE_R - 5,
                              x + NODE_R + 5, y + NODE_R + 5,
                              outline="#ffffff", width=2)


def main():
    root = tk.Tk()
    FlipGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
