#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
weiqi_ai — 蒙特卡洛树搜索 AI + 在线模式学习

思路 (轻量版 "模式先验 + 对局学习"):
  1. 每手棋提取落子点的 3x3 局部模式 (己方视角归一化 + 8 向对称规范化)。
  2. 知识库统计每个模式走出的棋的胜负 (胜方走出的模式 +1 胜, 负方 +1 负),
     形成 "模式胜率先验" (拉普拉斯平滑, 未知模式先验 0.5)。
  3. MCTS 的树内选择与模拟走子都由该先验引导 (heavy playout),
     因此知识越丰富, 模拟质量越高, 棋力越强。
  4. 每局结束 (数子或认输) 自动把本局所有落子回放并更新知识库,
     持久化到 ~/.local/share/weiqi/knowledge.json, 同时保存 SGF 棋谱。

与 AlphaZero 的区别: 这里学习的是局部模式统计而非神经网络,
在本机 CPU 上即可实时运行, 并随对局数量持续进步 (主要提升战术层面)。
"""

import json
import math
import os
import random
import time

KOMI = 7.5

DATA_DIR = os.path.expanduser("~/.local/share/weiqi")
KB_FILE = os.path.join(DATA_DIR, "knowledge.json")
GAMES_DIR = os.path.join(DATA_DIR, "games")


# ==================== 局部模式 ====================

def _canon(pattern):
    """8 种对称变换取字典序最小者, 增强泛化"""
    def rot(p):   # 3x3 顺时针旋转
        return (p[6], p[3], p[0], p[7], p[4], p[1], p[8], p[5], p[2])

    def flip(p):  # 水平翻转
        return (p[2], p[1], p[0], p[5], p[4], p[3], p[8], p[7], p[6])

    forms = [pattern]
    p = pattern
    for _ in range(3):
        p = rot(p)
        forms.append(p)
    p = flip(pattern)
    forms.append(p)
    for _ in range(3):
        p = rot(p)
        forms.append(p)
    return min(forms)


def move_key(board, size, x, y, color):
    """落子前局面中 (x,y) 的 3x3 邻域模式, 己方视角归一化。
    取值: 0 空 / 1 己方 / 2 对方 / 3 棋盘边界"""
    feats = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if 0 <= nx < size and 0 <= ny < size:
                v = board[ny][nx]
                if color == 2 and v in (1, 2):
                    v = 3 - v
                feats.append(v)
            else:
                feats.append(3)
    return _canon(tuple(feats))


# ==================== 知识库 ====================

class Knowledge:
    """局部模式胜率知识库 (在线学习, 自动持久化)"""

    def __init__(self, path=KB_FILE):
        self.path = path
        self.stats = {}
        try:
            with open(path) as f:
                raw = json.load(f)
            for k, v in raw.items():
                self.stats[tuple(int(i) for i in k.split(","))] = [float(v[0]), float(v[1])]
        except (OSError, ValueError):
            pass

    def prior(self, key):
        """模式胜率先验 (拉普拉斯平滑, 未知模式 0.5)"""
        w, l = self.stats.get(key, (0.0, 0.0))
        return (w + 1.0) / (w + l + 2.0)

    def update(self, moves, winner):
        """moves: [(board_before, x, y, color)], winner: 1 黑胜 / 2 白胜"""
        for board, x, y, color in moves:
            key = move_key(board, len(board), x, y, color)
            s = self.stats.setdefault(key, [0.0, 0.0])
            if color == winner:
                s[0] += 1.0
            else:
                s[1] += 1.0

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            raw = {",".join(str(i) for i in k): v for k, v in self.stats.items()}
            with open(self.path, "w") as f:
                json.dump(raw, f)
        except OSError:
            pass

    def __len__(self):
        return len(self.stats)


def extract_moves(size, record):
    """把对局记录 [(x,y,color) | (None,color)] 重放为
    [(落子前棋盘, x, y, color)], 供知识库学习用"""
    bd = FastBoard(size)
    out = []
    for x, y, c in record:
        if x is None:
            bd.turn = 3 - bd.turn
            bd.ko = None
            continue
        if bd.turn != c:
            continue
        snap = [row[:] for row in bd.b]
        if bd.play_fast(x, y):
            out.append((snap, x, y, c))
    return out


# ==================== 快速棋盘 (模拟专用) ====================

class FastBoard:
    """轻量棋盘: 快速走子, 供 MCTS 模拟使用。
    规则: 提子、禁自杀、简单劫 (回提劫点单子禁止)。不做全局同形检测。"""

    def __init__(self, size, board=None, turn=1):
        self.size = size
        self.b = [row[:] for row in board] if board else [[0] * size for _ in range(size)]
        self.turn = turn
        self.ko = None  # 劫点: 刚被提掉的单子位置

    def neighbors(self, x, y):
        n = self.size
        if x > 0:
            yield x - 1, y
        if x < n - 1:
            yield x + 1, y
        if y > 0:
            yield x, y - 1
        if y < n - 1:
            yield x, y + 1

    def group(self, x, y):
        """返回 (棋串坐标集合, 气数)"""
        color = self.b[y][x]
        seen, stack, libs = set(), [(x, y)], set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in seen:
                continue
            seen.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                v = self.b[ny][nx]
                if v == 0:
                    libs.add((nx, ny))
                elif v == color:
                    stack.append((nx, ny))
        return seen, len(libs)

    def play_fast(self, x, y):
        """执行走子; 非法返回 False"""
        color = self.turn
        opp = 3 - color
        n = self.size
        if not (0 <= x < n and 0 <= y < n) or self.b[y][x] != 0:
            return False
        # 先落子, 再检查对方死子 (气数必须计入这手新子)
        self.b[y][x] = color
        dead = []
        for nx, ny in self.neighbors(x, y):
            if self.b[ny][nx] == opp:
                g, libs = self.group(nx, ny)
                if libs == 0:
                    dead.append(g)
        captured = sum(len(g) for g in dead)
        # 简单劫: 禁止在劫点立即回提单子
        if captured == 1 and self.ko == (x, y):
            self.b[y][x] = 0  # 撤销这手
            return False
        # 移除死子
        for g in dead:
            for cx, cy in g:
                self.b[cy][cx] = 0
        self.ko = None
        if captured == 1:
            self.ko = next(iter(dead[0]))
        # 禁自杀
        g, libs = self.group(x, y)
        if libs == 0:
            self.b[y][x] = 0
            for gg in dead:
                for cx, cy in gg:
                    self.b[cy][cx] = opp
            self.ko = None
            return False
        self.turn = opp
        return True

    def candidates(self):
        """候选点: 已有棋子 3x3 邻域内的空点; 空盘返回天元"""
        n = self.size
        pts = set()
        for y in range(n):
            for x in range(n):
                if self.b[y][x] != 0:
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < n and 0 <= ny < n and self.b[ny][nx] == 0:
                                pts.add((nx, ny))
        if not pts:
            c = n // 2
            pts = {(c, c)}
        return list(pts)


def area_score(board, size, komi=KOMI):
    """数子法快速计分: 空域归唯一相邻方; 返回 1 黑胜 / 2 白胜 / 0 和"""
    b = board
    visited = set()
    terr = {1: 0, 2: 0}
    for y in range(size):
        for x in range(size):
            if b[y][x] == 0 and (x, y) not in visited:
                region, stack, border = set(), [(x, y)], set()
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in region:
                        continue
                    region.add((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < size and 0 <= ny < size:
                            v = b[ny][nx]
                            if v == 0:
                                stack.append((nx, ny))
                            else:
                                border.add(v)
                visited |= region
                if len(border) == 1:
                    terr[next(iter(border))] += len(region)
    black = sum(row.count(1) for row in b) + terr[1]
    white = sum(row.count(2) for row in b) + terr[2] + komi
    if black > white:
        return 1
    if white > black:
        return 2
    return 0


# ==================== MCTS ====================

class _Node:
    __slots__ = ("parent", "move", "mover", "tomove", "N", "W", "prior", "children", "untried")

    def __init__(self, parent, move, mover, tomove):
        self.parent = parent
        self.move = move          # 进入本节点的那手棋 (x,y)
        self.mover = mover        # 谁下了这手棋 (root 为 None)
        self.tomove = tomove      # 本节点轮到谁
        self.N = 0.0
        self.W = 0.0
        self.prior = 0.5
        self.children = []
        self.untried = None       # None=尚未生成候选; 空列表=已全部尝试


class MCTS:
    """带模式先验的 UCT 蒙特卡洛树搜索"""

    def __init__(self, kb, cpuct=1.2):
        self.kb = kb
        self.cpuct = cpuct

    def search(self, board, size, turn, budget=2.5, max_iters=20000,
               temperature=0.0, debug=False):
        """搜索并返回 (x,y); 若认为应停一手返回 None。
        temperature>0 时按访问量 softmax 采样 (自我对弈多样性用)。
        "停一手" 作为显式候选加入树中, 由统计决定是否停。
        debug=True 时输出决策时命中的棋形与先验概率, 用于验证知识库生效。"""
        root = _Node(None, None, None, turn)
        bd0 = FastBoard(size, board, turn)
        root.untried = bd0.candidates() + [None]
        t0 = time.time()
        iters = 0
        while time.time() - t0 < budget and iters < max_iters:
            iters += 1
            bd = FastBoard(size, bd0.b, turn)
            node = root
            # ---- 选择 ----
            while node.untried == [] and node.children:
                unvisited = [ch for ch in node.children if ch.N == 0]
                if unvisited:
                    node = self._pick_prior(unvisited)
                else:
                    node = self._pick_uct(node)
                if node.move is None:
                    bd.turn = 3 - bd.turn
                    bd.ko = None
                else:
                    bd.play_fast(node.move[0], node.move[1])
            # ---- 扩展 ----
            if node.untried is None:
                node.untried = bd.candidates() + [None]  # 首次访问: 生成候选(含停一手)
            if node.untried:
                mv = self._sample_untried(node, bd)
                if mv is None:
                    # 扩展 "停一手" 子节点
                    node.untried.remove(None)
                    bd.turn = 3 - bd.turn
                    bd.ko = None
                    child = _Node(node, None, node.tomove, 3 - node.tomove)
                    child.prior = 0.4
                    node.children.append(child)
                    node = child
                else:
                    # 关键: 棋形必须在落子"之前"的棋盘上提取,
                    # 此时落点中心格为 0(空), 与训练时的键空间一致。
                    key = move_key(bd.b, size, mv[0], mv[1], node.tomove)
                    if not bd.play_fast(mv[0], mv[1]):
                        node.untried.remove(mv)
                        continue
                    node.untried.remove(mv)  # 成功扩展后移除, 避免重复采样
                    child = _Node(node, mv, node.tomove, 3 - node.tomove)
                    child.prior = self.kb.prior(key)
                    node.children.append(child)
                    node = child
            # ---- 模拟 (heavy playout) ----
            result = self._rollout(bd, size)
            # ---- 回传 ----
            while node is not None:
                node.N += 1.0
                if node.mover is not None:
                    if result == node.mover:
                        node.W += 1.0
                    elif result == 0:
                        node.W += 0.5
                    else:
                        node.W -= 1.0
                node = node.parent
        # ---- 决策 ----
        if not root.children:
            if debug:
                print(f"[AI] 决策: 停一手 (无候选) | 知识库 {len(self.kb)} 种棋形",
                      flush=True)
            return None
        if temperature > 0:
            cands = [(ch.N ** (1.0 / temperature), ch)
                     for ch in root.children if ch.N > 0]
            if not cands:
                return None
            total = sum(w for w, _ in cands)
            r = random.random() * total
            acc = 0.0
            for w, ch in cands:
                acc += w
                if r <= acc:
                    best = ch
                    break
            else:
                best = cands[-1][1]
            if debug:
                self._log_decision(board, size, turn, best)
            return best.move
        best = max(root.children, key=lambda ch: (ch.N, ch.W / ch.N if ch.N else -1))
        if debug:
            self._log_decision(board, size, turn, best)
        return best.move

    def _log_decision(self, board, size, turn, best):
        """打印决策时命中的棋形与先验, 用于验证知识库是否真正生效"""
        if best.move is None:
            print(f"[AI] 决策: 停一手 | 访问 {best.N:.0f} | "
                  f"知识库 {len(self.kb)} 种棋形", flush=True)
            return
        key = move_key(board, size, best.move[0], best.move[1], turn)
        q = best.W / best.N if best.N else 0.0
        print(f"[AI] 当前匹配棋形: {key}, 先验概率: {best.prior:.3f}, "
              f"访问: {best.N:.0f}, 模拟胜率: {q:+.3f}, "
              f"知识库: {len(self.kb)} 种棋形", flush=True)

    def _pick_prior(self, children):
        total = sum(ch.prior for ch in children) or len(children)
        r = random.random() * total
        acc = 0.0
        for ch in children:
            acc += ch.prior
            if r <= acc:
                return ch
        return children[-1]

    def _pick_uct(self, node):
        best_ch, best_v = None, None
        for ch in node.children:
            n = ch.N
            q = ch.W / n if n else 0.0
            u = self.cpuct * ch.prior * math.sqrt(node.N) / (1.0 + n)
            v = q + u
            if best_ch is None or v > best_v:
                best_ch, best_v = ch, v
        return best_ch

    def _sample_untried(self, node, bd):
        if not node.untried:
            return None
        weighted = []
        for mv in node.untried:
            if mv is None:
                weighted.append((0.4, None))  # 停一手的固定先验
            else:
                pr = self.kb.prior(move_key(bd.b, bd.size, mv[0], mv[1], node.tomove))
                weighted.append((pr, mv))
        total = sum(p for p, _ in weighted)
        if total <= 0:
            return weighted[0][1]
        r = random.random() * total
        acc = 0.0
        for p, mv in weighted:
            acc += p
            if r <= acc:
                return mv
        return weighted[-1][1]

    def _rollout(self, bd, size):
        cap = 120 if size <= 9 else 200
        moves = 0
        passes = 0
        while moves < cap and passes < 2:
            cands = bd.candidates()
            weighted = []
            total = 0.0
            for mx, my in cands:
                pr = self.kb.prior(move_key(bd.b, size, mx, my, bd.turn))
                weighted.append((pr, (mx, my)))
                total += pr
            placed = False
            if weighted and total > 0:
                for _ in range(len(weighted)):
                    r = random.random() * total
                    acc = 0.0
                    for pr, mv in weighted:
                        acc += pr
                        if r <= acc and bd.play_fast(mv[0], mv[1]):
                            placed = True
                            break
                    if placed:
                        break
            if placed:
                moves += 1
                passes = 0
            else:
                bd.turn = 3 - bd.turn
                bd.ko = None
                passes += 1
        return area_score(bd.b, size)
