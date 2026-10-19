import os
import tkinter
import time
import sys
import random
from collections import deque
import pygame
from pygame.locals import *

##############################################################

rate = 0.618
size = 20
margin_rate = 1

##############################################################

root = tkinter.Tk()
width = root.winfo_screenwidth()
height = root.winfo_screenheight()

##############################################################

width *= rate
height *= rate
width = int(width / size) * size
height = int(height / size) * size

background_margin_breadth = 1

snake_body_size = size
snake_init_length = 10
snake_head_symbol_breadth = 3
init_direction = 'd'

food_margin_breadth = 1
food_number = 10

##############################################################

white = (255,255,255)
red = (255,0,0)
orange = (255,128,0)
yellow = (255,255,0)
green = (0,255,0)
cyan = (0,160,233)
blue = (0,0,255)
violet = (212,196,219)
black = (0,0,0)
replace = (0,140,140)
level_board = [white,red,orange,yellow,green,cyan,blue,violet,replace]

##############################################################

snake_block_color = (128,128,128)
snake_body_margin_color = (60,60,60)
snake_body_margin_breadth = 2
snake_head_symbol_color = black
background_color = black
background_margin_color = black

##############################################################

class block:
    def __init__(self,up,height,left,width,margin_color,content_color,margin_breadth):
        self.up = up
        self.left = left
        self.margin_color = margin_color
        self.content_color = content_color
        self.margin_breadth = margin_breadth
        self.width = width
        self.height = height
        
    def draw(self):
        pos = (self.left,self.up,self.width,self.height)
        pygame.draw.rect(screen,self.content_color,pos,0)
        pygame.draw.rect(screen,self.margin_color,pos,self.margin_breadth)

class food:
    def __init__(self,number):
        self.number = number
        self.effect = [random.randint(1,9) for i in range(self.number)]
        self.summary = [block(random.randint(0,CYCLE_ROWS - 1) * size,size,random.randint(0,int(margin.width / size) - 1) * size,size,level_board[self.effect[i] - 1],level_board[self.effect[i] - 1],food_margin_breadth) for i in range(self.number)]
        
    def draw(self):
        for i in self.summary:
            i.draw()

class snake:
    def __init__(self,direction,init_x,init_y,length):
        self.direction = direction
        self.x = init_x
        self.y = init_y
        self.length = length
        self.body = []
        for i in range(self.length):
            self.body.append(block(init_y,snake_body_size,init_x,snake_body_size,snake_block_color,snake_block_color,0))
        
    def move(self):
        del(self.body[self.length - 1])
        self.body = [block(self.body[0].up,snake_body_size,self.body[0].left,snake_body_size,snake_block_color,snake_block_color,0)] + self.body
        if self.direction == 'u':
            self.body[0].up -= size
        elif self.direction == 'd':
            self.body[0].up += size
        elif self.direction == 'l':
            self.body[0].left -= size
        elif self.direction == 'r':
            self.body[0].left += size

    def draw(self):
        # 每格对应的身体序号列表（尾巴处可能有重叠块）
        cell_blocks = {}
        for i in range(self.length):
            pos = (self.body[i].left, self.body[i].up)
            cell_blocks.setdefault(pos, []).append(i)

        # 先画内容（纯色方块）
        for i in range(self.length):
            (self.body[i]).draw()

        mc = snake_body_margin_color
        bw = snake_body_margin_breadth

        def draw_top(x, y, color, width):
            pygame.draw.line(screen, color, (x, y), (x + size - 1, y), width)

        def draw_bottom(x, y, color, width):
            pygame.draw.line(screen, color, (x, y + size - 1),
                             (x + size - 1, y + size - 1), width)

        def draw_left(x, y, color, width):
            pygame.draw.line(screen, color, (x, y), (x, y + size - 1), width)

        def draw_right(x, y, color, width):
            pygame.draw.line(screen, color, (x + size - 1, y),
                             (x + size - 1, y + size - 1), width)

        def consecutive(a, b):
            """两格之间是否存在身体顺序上前后相连的节（序号差 1）。"""
            for i in cell_blocks[a]:
                for j in cell_blocks[b]:
                    if abs(i - j) == 1:
                        return True
            return False

        for x, y in cell_blocks:
            # 外轮廓：该方向没有身体
            if (x, y - size) not in cell_blocks:
                draw_top(x, y, mc, bw)
            if (x, y + size) not in cell_blocks:
                draw_bottom(x, y, mc, bw)
            if (x - size, y) not in cell_blocks:
                draw_left(x, y, mc, bw)
            if (x + size, y) not in cell_blocks:
                draw_right(x, y, mc, bw)
            # 内部隔断：相邻但「不是前后相连节」的平行身体段之间画分隔线
            if (x, y + size) in cell_blocks and not consecutive((x, y), (x, y + size)):
                draw_bottom(x, y, mc, bw)
            if (x + size, y) in cell_blocks and not consecutive((x, y), (x + size, y)):
                draw_right(x, y, mc, bw)

        # 蛇头标记：3px 黑描边，只画「外露」和「非前后相连」的边
        hx, hy = self.body[0].left, self.body[0].up
        hbw = snake_head_symbol_breadth
        if (hx, hy - size) not in cell_blocks or not consecutive((hx, hy), (hx, hy - size)):
            draw_top(hx, hy, snake_head_symbol_color, hbw)
        if (hx, hy + size) not in cell_blocks or not consecutive((hx, hy), (hx, hy + size)):
            draw_bottom(hx, hy, snake_head_symbol_color, hbw)
        if (hx - size, hy) not in cell_blocks or not consecutive((hx, hy), (hx - size, hy)):
            draw_left(hx, hy, snake_head_symbol_color, hbw)
        if (hx + size, hy) not in cell_blocks or not consecutive((hx, hy), (hx + size, hy)):
            draw_right(hx, hy, snake_head_symbol_color, hbw)
        
    def increase(self,effect):
        for i in range(effect):
            x = self.body[self.length - 1].left
            y = self.body[self.length - 1].up
            self.body.append(block(y,snake_body_size,x,snake_body_size,snake_block_color,snake_block_color,0))
        self.length += effect

margin = block(0,height,0,width * margin_rate,background_margin_color,background_color,background_margin_breadth)

pygame.init()

screen = pygame.display.set_mode((width,height))

pygame.display.set_caption("Snake")

snake1 = snake(init_direction,size,size,snake_init_length)

snakes = []
snakes.append(snake1)

##############################################################
# 自动控制：移植自 cs/sl.cpp
#   "ham"    哈密顿环 + 捷径（默认，不会困死，会铺满棋盘）
#   "greedy" BFS 找食物 + 追尾 + 空间评估
# 用环境变量切换：SNAKE_STRATEGY=ham|greedy
##############################################################

STRATEGY = os.environ.get("SNAKE_STRATEGY", "ham").lower()

COLS = int(margin.width / size)
ROWS = int(margin.height / size)
CYCLE_ROWS = ROWS - (ROWS % 2)          # 哈密顿环要求行数为偶数

DIRS = ('u', 'd', 'l', 'r')
DX = (0, 0, -1, 1)
DY = (-1, 1, 0, 0)

order = [[0] * COLS for _ in range(CYCLE_ROWS)]
cycle_cell = [None] * (COLS * CYCLE_ROWS)
cycle_n = 0


def build_cycle():
    """与 sl.cpp 相同的哈密顿环：第 0 行从左到右，
    第 1..CYCLE_ROWS-1 行在 1..COLS-1 之间蛇形，最后沿第 0 列返回。"""
    global cycle_n
    n = 0

    def add(x, y):
        nonlocal n
        order[y][x] = n
        cycle_cell[n] = (x, y)
        n += 1

    for x in range(COLS):
        add(x, 0)
    for y in range(1, CYCLE_ROWS):
        if y % 2 == 1:
            for x in range(COLS - 1, 0, -1):
                add(x, y)
        else:
            for x in range(1, COLS):
                add(x, y)
    for y in range(CYCLE_ROWS - 1, 0, -1):
        add(0, y)
    cycle_n = n


def dir_index(d):
    return DIRS.index(d)


def dir_to(a, b):
    if b[1] == a[1] - 1:
        return 'u'
    if b[1] == a[1] + 1:
        return 'd'
    if b[0] == a[0] - 1:
        return 'l'
    return 'r'


def body_cells(S):
    return [(b.left // size, b.up // size) for b in S.body]


def head_cell(S):
    return (S.body[0].left // size, S.body[0].up // size)


def tail_info(S):
    """返回 (尾巴格子, 该格上的方块数)。数量 == 1 表示下一步尾巴会移开。"""
    cells = body_cells(S)
    tail = cells[-1]
    return tail, cells.count(tail)


def occ_set(S):
    """当前占据的格子集合；尾巴下一步会移开时把尾巴格去掉。"""
    cells = body_cells(S)
    occ = set(cells)
    tail = cells[-1]
    if cells.count(tail) == 1:
        occ.discard(tail)
    return occ


def food_cells():
    return [(f.left // size, f.up // size) for f in F.summary
            if 0 <= f.left // size < COLS and 0 <= f.up // size < CYCLE_ROWS]


def bfs(start, blocked):
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)]
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= COLS or ny < 0 or ny >= CYCLE_ROWS:
                continue
            if (nx, ny) in blocked or (nx, ny) in dist:
                continue
            dist[(nx, ny)] = d + 1
            q.append((nx, ny))
    return dist


def choose_hamiltonian(S):
    """沿哈密顿环走，并在安全时抄近路（跳过整段空环）。"""
    occ = occ_set(S)
    hx, hy = head_cell(S)
    if not (0 <= hx < COLS and 0 <= hy < CYCLE_ROWS):
        return S.direction
    h = order[hy][hx]

    target_d = cycle_n
    for fx, fy in food_cells():
        d = (order[fy][fx] - h) % cycle_n
        if d < target_d:
            target_d = d
    if target_d == cycle_n:
        target_d = cycle_n - 1

    best_jump = 0
    best_dir = S.direction
    for k in range(4):
        if (k ^ 1) == dir_index(S.direction):
            continue
        nx, ny = hx + DX[k], hy + DY[k]
        if nx < 0 or nx >= COLS or ny < 0 or ny >= CYCLE_ROWS:
            continue
        if (nx, ny) in occ:
            continue
        j = order[ny][nx]
        jump = (j - h) % cycle_n
        if jump == 0 or jump > target_d:
            continue
        clear = True
        for s in range(1, jump):
            cx, cy = cycle_cell[(h + s) % cycle_n]
            if (cx, cy) in occ:
                clear = False
                break
        if not clear:
            continue
        if jump > best_jump:
            best_jump = jump
            best_dir = DIRS[k]

    if best_jump == 0:
        cx, cy = cycle_cell[(h + 1) % cycle_n]
        best_dir = dir_to((hx, hy), (cx, cy))
        if (cx, cy) in occ:
            for k in range(4):
                nx, ny = hx + DX[k], hy + DY[k]
                if 0 <= nx < COLS and 0 <= ny < CYCLE_ROWS and (nx, ny) not in occ:
                    best_dir = DIRS[k]
                    break
    return best_dir


def choose_greedy(S):
    """BFS 评估：安全且能吃到→最短路；否则追尾；再否则取最大空间。"""
    hx, hy = head_cell(S)
    foods = food_cells()
    cells = body_cells(S)
    occ = occ_set(S)

    def analyze(head2):
        nb = [head2] + cells[:-1]        # 走一步后的身体（尾块被删掉一个）
        tail_cell = nb[-1]
        passable = tail_cell if nb.count(tail_cell) == 1 else None
        blocked = set(nb)
        if passable is not None:
            blocked.discard(passable)
        dist = bfs(head2, blocked)
        area = len(dist) - 1
        food_d = -1
        for fc in foods:
            if fc in dist and (food_d < 0 or dist[fc] < food_d):
                food_d = dist[fc]
        tail_d = dist.get(tail_cell, -1)
        return area, food_d, tail_d

    best_dir = S.direction
    best_rank = -1
    best_food = 0
    best_tail = 0
    best_area = -1
    best_straight = False
    has = False

    for k in range(4):
        if (k ^ 1) == dir_index(S.direction):
            continue
        nx, ny = hx + DX[k], hy + DY[k]
        if nx < 0 or nx >= COLS or ny < 0 or ny >= CYCLE_ROWS:
            continue
        if (nx, ny) in occ:
            continue

        area, food_d, tail_d = analyze((nx, ny))
        safe = tail_d >= 0
        rank = 2 if (safe and food_d >= 0) else (1 if safe else 0)
        straight = DIRS[k] == S.direction

        better = False
        if not has:
            better = True
        elif rank != best_rank:
            better = rank > best_rank
        elif rank == 2:
            better = (food_d < best_food
                      or (food_d == best_food and area > best_area)
                      or (food_d == best_food and area == best_area
                          and straight and not best_straight))
        elif rank == 1:
            t1 = tail_d if tail_d >= 0 else 1 << 30
            t2 = best_tail if best_tail >= 0 else 1 << 30
            better = (t1 < t2
                      or (t1 == t2 and area > best_area)
                      or (t1 == t2 and area == best_area
                          and straight and not best_straight))
        else:
            better = (area > best_area
                      or (area == best_area and straight and not best_straight))

        if better:
            has = True
            best_dir = DIRS[k]
            best_rank = rank
            best_food = food_d
            best_tail = tail_d
            best_area = area
            best_straight = straight

    return best_dir if has else S.direction


def choose_direction(S):
    return choose_hamiltonian(S) if STRATEGY == "ham" else choose_greedy(S)


build_cycle()

# 哈密顿环需要身体沿环铺开：把初始身体重排到环的前 initLength 格
if STRATEGY == "ham" and snake1.length <= cycle_n:
    for i in range(snake1.length):
        cx, cy = cycle_cell[snake1.length - 1 - i]
        snake1.body[i].left = cx * size
        snake1.body[i].up = cy * size
    snake1.direction = 'r'

F = food(food_number)

def ifeat(S):
    effect = 0
    for i in range(F.number):
        if F.summary[i].left == S.body[0].left and F.summary[i].up == S.body[0].up:
            effect = F.effect[i]
            F.effect[i] = random.randint(1,9)
            x = random.randint(0,int(margin.width / size) - 1) * size
            y = random.randint(0,CYCLE_ROWS - 1) * size
            while (x,y) in waller():
                x = random.randint(0,int(margin.width / size) - 1) * size
                y = random.randint(0,int(margin.height / size) - 1) * size
            F.summary[i] = block(y,size,x,size,level_board[F.effect[i] - 1],level_board[F.effect[i] - 1],food_margin_breadth)
            break
    return effect

def txt(fontsize,text,anti_alias=False,color=white,pos=(0,0)):
    myfont = pygame.font.Font(None,fontsize)
    textImage = myfont.render(text,anti_alias,color)
    screen.blit(textImage,pos)
    
stats = {
    "steps": 0,      # 运行步数
    "foods": 0,      # 吃到食物的次数
    "growth": 0,     # 累计增长的格数
    "max_len": 0,    # 最大长度
    "t0": 0.0,       # 开局时间
}


def end(reason, details=()):
    """打印详细的结束报告并退出。"""
    hx = snake1.body[0].left // size
    hy = snake1.body[0].up // size
    strategy_name = ("哈密顿环 + 捷径" if STRATEGY == "ham" else "BFS 贪心评估")

    lines = []
    lines.append("=" * 56)
    lines.append("本局结束报告")
    lines.append("=" * 56)
    lines.append("结束原因：%s" % reason)
    for d in details:
        lines.append("  - " + d)
    lines.append("策略：%s" % strategy_name)
    lines.append("棋盘：%d x %d 格（AI 活动区 %d x %d 格）"
                 % (COLS, ROWS, COLS, CYCLE_ROWS))
    lines.append("运行步数：%d" % stats["steps"])
    lines.append("最终长度：%d（初始 %d，净增长 %d）"
                 % (snake1.length, snake_init_length,
                    snake1.length - snake_init_length))
    lines.append("最大长度：%d" % stats["max_len"])
    lines.append("吃到食物：%d 次，累计增长 %d 格"
                 % (stats["foods"], stats["growth"]))
    lines.append("蛇头最终位置：格子 (%d, %d)" % (hx, hy))
    if stats["t0"] > 0 and stats["steps"] > 0:
        elapsed = time.time() - stats["t0"]
        lines.append("运行时长：%.1f 秒（平均每步 %.0f 毫秒）"
                     % (elapsed, elapsed * 1000.0 / stats["steps"]))
    lines.append("=" * 56)
    print("\n".join(lines))
    pygame.quit()
    sys.exit()

def receive():
    for event in pygame.event.get():
        if event.type == QUIT:
            end("玩家关闭窗口")
        elif event.type == KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                end("玩家按 Esc 退出")
            elif event.key == pygame.K_UP and snake1.direction != 'd':
                snake1.direction = 'u'
            elif event.key == pygame.K_DOWN and snake1.direction != 'u':
                snake1.direction = 'd'
            elif event.key == pygame.K_LEFT and snake1.direction != 'r':
                snake1.direction = 'l'
            elif event.key == pygame.K_RIGHT and snake1.direction != 'l':
                snake1.direction = 'r'
            elif event.key == pygame.K_SPACE:
                stop = True
                txt(30,"Stop...",True,red,(width - 60,height - 30))
                pygame.display.update()
                while stop:
                    for event in pygame.event.get():
                        if event.type == QUIT:
                            end("玩家关闭窗口")
                        elif event.type == KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                end("玩家按 Esc 退出")
                            elif event.key == pygame.K_SPACE:
                                stop = False

def draw():
    screen.fill(blue)
    
    pygame.display.set_caption("Snake length:%d" % snake1.length)
    margin.draw()
    F.draw()
    snake1.draw()
    
    pygame.display.update()

def waller():
    wall_list = []
    for i in snakes:
        for j in i.body:
            pos = (j.left,j.up)
            wall_list.append(pos)
    if len(wall_list) >= int(width * height / size / size):
        end("身体长度达到棋盘总格数（历史遗留判断）",
            ["身体长度 %d，棋盘总格数 %d"
             % (len(wall_list), int(width * height / size / size))])
    return wall_list

def ac(S):                       #auto control（移植自 cs/sl.cpp）
    d = choose_direction(S)
    S.direction = d

def check():
    x = snake1.body[0].left
    y = snake1.body[0].up
    if x < 0 or x >= width or y < 0 or y >= height:
        if x < 0:
            side = "左"
        elif x >= width:
            side = "右"
        elif y < 0:
            side = "上"
        else:
            side = "下"
        end("蛇头越出棋盘边界",
            ["越界方向：%s" % side,
             "蛇头位置：格子 (%d, %d)，像素 (%d, %d)"
             % (x // size, y // size, x, y)])
    for i in range(1, len(snake1.body)):
        if snake1.body[i].left == x and snake1.body[i].up == y:
            end("蛇头撞到自己的身体",
                ["相撞的是身体第 %d 节（距蛇头 %d 节）" % (i, i),
                 "碰撞位置：格子 (%d, %d)" % (x // size, y // size)])

def main():
    stats["t0"] = time.time()
    stats["steps"] = 0
    stats["foods"] = 0
    stats["growth"] = 0
    stats["max_len"] = snake1.length

    while True:
        #time.sleep(0.05)
        stats["steps"] += 1
        ac(snake1)
        receive()
        snake1.move()
        effect = ifeat(snake1)
        if effect:
            stats["foods"] += 1
            stats["growth"] += effect
        snake1.increase(effect)
        if snake1.length > stats["max_len"]:
            stats["max_len"] = snake1.length
        draw()
        check()
        if snake1.length >= COLS * CYCLE_ROWS:
            occ = len({(b.left, b.up) for b in snake1.body})
            end("铺满棋盘获胜（Perfect）",
                ["身体长度 %d，实际占据 %d / %d 格"
                 % (snake1.length, occ, COLS * CYCLE_ROWS)])


if __name__ == "__main__":
    main()
