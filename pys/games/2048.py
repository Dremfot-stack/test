import pygame
import math
import time
import sys
import random
from pygame.locals import *

sl = ('u','l','d','r')
cd = 0.01

level = 4
size = 100
width = level * size
height = level * size

txtsize = 50
bgc = (255,255,255)
txtcolor = (
        (205, 193, 180),
        (205, 193, 180),
        (237, 224, 200),
        (242, 177, 121),
        (245, 149, 99),
        (246, 124, 95),
        (246, 124, 95),
        (246, 124, 95),
        (237, 204, 97),
        (237, 200, 80),
        (237, 200, 80),
        (237, 194, 46),
        (66, 180, 200),
        (70, 130, 180),
        (145, 100, 200),
        (145, 100, 200),
        (150, 50, 120)
        )

HEADLESS = "--headless" in sys.argv
screen = None
FONT = None
if not HEADLESS:
    pygame.init()
    screen = pygame.display.set_mode((width,height))
    FONT = pygame.font.SysFont("microsoftsansserif",txtsize,True,False)

# =====================================================================
# 棋盘逻辑（纯函数，不依赖 pygame，也不会在模拟时偷偷补格子）
# =====================================================================

def new_board():
    return [[0 for _ in range(level)] for _ in range(level)]

def produce(wall):
    """在随机空格放一个 2 或 4（保持原来的 50/50 分布）"""
    empties = [(i,j) for i in range(level) for j in range(level) if wall[i][j] == 0]
    if not empties:
        return
    i,j = random.choice(empties)
    wall[i][j] = 2 if random.random() < 0.5 else 4

def _merge(line):
    """把一行/一列向行首压缩并合并，返回 (结果, 本次得分)"""
    vals = [x for x in line if x]
    out = []
    gained = 0
    i = 0
    while i < len(vals):
        if i + 1 < len(vals) and vals[i] == vals[i+1]:
            v = vals[i] * 2
            out.append(v)
            gained += v
            i += 2
        else:
            out.append(vals[i])
            i += 1
    out += [0] * (len(line) - len(out))
    return out, gained

def slide(board, sign):
    """返回 (移动后的新棋盘, 本次合并得分, 是否真的发生了移动)，不补格子"""
    n = len(board)
    nb = [row[:] for row in board]
    gained = 0
    moved = False
    if sign in ('l','r'):
        for i in range(n):
            orig = nb[i][:]
            line = orig if sign == 'l' else orig[::-1]
            merged, g = _merge(line)
            if sign == 'r':
                merged = merged[::-1]
            if merged != orig:
                moved = True
            nb[i] = merged
            gained += g
    else:
        for j in range(n):
            orig = [nb[i][j] for i in range(n)]
            line = orig if sign == 'u' else orig[::-1]
            merged, g = _merge(line)
            if sign == 'd':
                merged = merged[::-1]
            for i in range(n):
                if nb[i][j] != merged[i]:
                    moved = True
                nb[i][j] = merged[i]
            gained += g
    return nb, gained, moved

def apply_move(board, sign):
    """真正走一步：滑动 + 补一个新格子，返回本次得分"""
    nb, gained, moved = slide(board, sign)
    if not moved:
        return 0
    for i in range(level):
        board[i][:] = nb[i]
    produce(board)
    return gained

# =====================================================================
# 局面评估
# =====================================================================

W_EMPTY  = 270.0   # 每个空格
W_SMOOTH = 10.0    # 相邻块差值（负向）
W_MONO   = 47.0    # 单调性（负向）
W_MAX    = 1000.0   # 最大块
W_MERGE  = 200.0    # 可合并的相邻对
W_CORNER = 100.0   # 最大块在角落

def evaluate(board):
    empty = 0
    smooth = 0
    max_rank = 0
    merges = 0

    for i in range(level):
        for j in range(level):
            v = board[i][j]
            if v == 0:
                empty += 1
                continue
            r = v.bit_length() - 1
            if r > max_rank:
                max_rank = r
            if j + 1 < level and board[i][j+1]:
                smooth -= abs(r - (board[i][j+1].bit_length() - 1))
            if i + 1 < level and board[i+1][j]:
                smooth -= abs(r - (board[i+1][j].bit_length() - 1))
            if j + 1 < level and v == board[i][j+1]:
                merges += 1
            if i + 1 < level and v == board[i+1][j]:
                merges += 1

    # 单调性：每行/每列分别看两个方向，取惩罚较小的那个方向
    mono = 0
    for i in range(level):
        lr = rl = 0
        for j in range(level - 1):
            a = board[i][j].bit_length() - 1 if board[i][j] else 0
            b = board[i][j+1].bit_length() - 1 if board[i][j+1] else 0
            if a > b:
                lr += b - a
            if b > a:
                rl += a - b
        mono += max(lr, rl)

    for j in range(level):
        ud = du = 0
        for i in range(level - 1):
            a = board[i][j].bit_length() - 1 if board[i][j] else 0
            b = board[i+1][j].bit_length() - 1 if board[i+1][j] else 0
            if a > b:
                ud += b - a
            if b > a:
                du += a - b
        mono += max(ud, du)

    corner = 0
    if max_rank:
        for c in (board[0][0], board[0][level-1],
                  board[level-1][0], board[level-1][level-1]):
            if c and c.bit_length() - 1 == max_rank:
                corner = max_rank * W_CORNER
                break

    return (empty * W_EMPTY
            + smooth * W_SMOOTH
            + mono * W_MONO
            + max_rank * W_MAX
            + merges * W_MERGE
            + corner)

# =====================================================================
# Expectimax 搜索
# =====================================================================

SEARCH_DEPTH = 4
NEG_INF = -1e18

def expectimax_chance(board, depth):
    """随机补格层：对每个空格、2/4 两种新块取期望"""
    if depth <= 0:
        return evaluate(board)

    empties = [(i,j) for i in range(level) for j in range(level)
               if board[i][j] == 0]
    if not empties:
        return evaluate(board)

    total = 0.0
    for i,j in empties:
        for tile, p in ((2,0.5), (4,0.5)):
            board[i][j] = tile
            total += p * expectimax_max(board, depth - 1)
            board[i][j] = 0
    return total / len(empties)

def expectimax_max(board, depth):
    """玩家层：选期望值最高的方向"""
    if depth <= 0:
        return evaluate(board)

    best = NEG_INF
    any_move = False
    for sign in sl:
        nb, gained, moved = slide(board, sign)
        if not moved:
            continue
        any_move = True
        val = gained + expectimax_chance(nb, depth - 1)
        if val > best:
            best = val

    if not any_move:
        return -1e9
    return best

def best_move(board, depth=SEARCH_DEPTH):
    best = NEG_INF
    best_sign = None
    for sign in sl:
        nb, gained, moved = slide(board, sign)
        if not moved:
            continue
        val = gained + expectimax_chance(nb, depth - 1)
        if val > best:
            best = val
            best_sign = sign
    return best_sign

# =====================================================================
# 无界面批量测试
# =====================================================================

def play_headless(games, seed):
    total = 0
    best_score = 0
    for g in range(games):
        random.seed(seed + g)
        board = new_board()
        produce(board)
        produce(board)
        score = 0
        steps = 0
        while steps < 50000:
            sign = best_move(board)
            if sign is None:
                break
            score += apply_move(board, sign)
            steps += 1
        mt = max(max(row) for row in board)
        total += score
        if score > best_score:
            best_score = score
        print(f"game {g}: score={score} max={mt} steps={steps}")
    print(f"avg={total/games:.1f} best={best_score}")

# =====================================================================
# 渲染与主循环
# =====================================================================

def log(x):
    n = 0
    while x > 1:
        x //= 2
        n += 1
    return n

def out():
    if not HEADLESS:
        pygame.quit()
    sys.exit(0)

def txt(content,center):
    idx = min(log(int(content)), len(txtcolor) - 1)
    obj = FONT.render(content,True,txtcolor[idx])
    txtrect = obj.get_rect()
    txtrect.center = center
    screen.blit(obj,txtrect)

def draw(wall):
    screen.fill(bgc)
    for i in range(level):
        for j in range(level):
            if wall[i][j] == 0:
                continue
            center = ((j * size + size / 2),(i * size + size / 2))
            txt(str(wall[i][j]),center)
    pygame.display.update()

def receive():
    for event in pygame.event.get():
        if event.type == QUIT:
            out()
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                out()

def main():
    if HEADLESS:
        idx = sys.argv.index("--headless")
        games = int(sys.argv[idx+1]) if idx + 1 < len(sys.argv) else 5
        seed = int(sys.argv[idx+2]) if idx + 2 < len(sys.argv) else 1
        play_headless(games, seed)
        return

    wall = new_board()
    produce(wall)
    produce(wall)
    score = 0
    draw(wall)

    while True:
        receive()
        sign = best_move(wall)
        if sign is None:
            print("Game over. score =", score)
            pygame.time.wait(1500)
            out()
        score += apply_move(wall, sign)
        draw(wall)
        pygame.display.set_caption("2048 AI   score=%d" % score)
        time.sleep(cd)

if __name__ == "__main__":
    main()
