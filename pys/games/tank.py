"""Prison - 双人无限迷宫射击（Pygame）

P1: W 前进 / S 后退 / A 左转 / D 右转（连续角度），J 射击
P2: ↑ 前进 / ↓ 后退 / ← 左转 / → 右转（连续角度），小键盘 1 / 右 Shift 射击
Space: 暂停/继续
R:   游戏结束后重开
Esc: 退出

特性：
- 迷宫无限大，随着玩家接近即时生成（超出屏幕一点作为缓冲）
- 镜头固定为玩家坐标的平均值，并根据玩家距离自动缩放
- 玩家不能穿墙、不能互相重叠，斜着撞墙不会滑动
- 子弹在墙上无限反弹，任何玩家碰到炮弹（包括自己的跳弹）立即爆炸
- 死亡有爆炸特效，之后显示胜者，可重开
"""

import math
import random

import pygame
from pygame.locals import *

# ---------------- 基础常量 ----------------

stdsize = 10
R = stdsize / 2
width = 80 * stdsize
height = 60 * stdsize

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 70, 70)
GREEN = (80, 220, 120)
BLUE = (80, 140, 255)
YELLOW = (255, 220, 80)

BG = (12, 12, 18)
WALL_EDGE = (92, 92, 128)

CELL = 25              # 迷宫格子尺寸（世界坐标像素）
WALL_T = 5             # 墙厚

MAX_BULLETS = 200
ROT_SPEED = 3.0        # 转向角速度（弧度/秒），按住左右键连续旋转

SPAWN2_CX = 10         # 玩家 2 的初始格（x 方向第几格）

# 镜头参数
BASE_DIST = 250.0      # 玩家距离等于这个值时缩放为 1
MIN_ZOOM = 0.55
MAX_ZOOM = 2.2
GEN_BUF = 2            # 屏幕外多生成的迷宫圈数（缓冲）
BULLET_RANGE = 1500.0  # 子弹离镜头超过这个距离就回收，避免无限向外生成

pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Prison")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
bigfont = pygame.font.SysFont(None, 72)

# ---------------- 无限迷宫 ----------------

# cells[(cx,cy)] = {"left": bool, "up": bool}：该格左边界/上边界是否有墙
cells = {}
cam_x = 0.0
cam_y = 0.0
zoom = 1.0


def ensure_cell(cx, cy):
    """按需生成一个迷宫格：与一个随机的已存在相邻格打通，保证连通。"""
    if (cx, cy) in cells:
        return
    cells[(cx, cy)] = {"left": True, "up": True}

    nbrs = []
    for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
        if (nx, ny) in cells:
            nbrs.append((nx, ny))
    if not nbrs:
        return

    nx, ny = random.choice(nbrs)
    if nx == cx - 1:
        cells[(cx, cy)]["left"] = False
    elif nx == cx + 1:
        cells[(cx + 1, cy)]["left"] = False
    elif ny == cy - 1:
        cells[(cx, cy)]["up"] = False
    else:
        cells[(cx, cy + 1)]["up"] = False


def ensure_path(x0, y0, x1, y1):
    """先打通 (x0,y0) 到 (x1,y1) 的一条随机路径，保证两个出生点连通。"""
    cx, cy = x0, y0
    ensure_cell(cx, cy)
    guard = 0
    while (cx, cy) != (x1, y1) and guard < 100000:
        guard += 1
        options = []
        if cx < x1:
            options.append((cx + 1, cy))
        if cx > x1:
            options.append((cx - 1, cy))
        if cy < y1:
            options.append((cx, cy + 1))
        if cy > y1:
            options.append((cx, cy - 1))
        if random.random() < 0.3:                      # 偶尔绕路，让迷宫自然一些
            dx, dy = random.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            options.append((cx + dx, cy + dy))
        if not options:
            break
        cx, cy = random.choice(options)
        ensure_cell(cx, cy)


def reset_maze():
    global cells
    cells = {}
    ensure_cell(0, 0)
    ensure_path(0, 0, SPAWN2_CX, 0)


def circle_rect(x, y, r, rx, ry, rw, rh):
    nx = max(rx, min(x, rx + rw))
    ny = max(ry, min(y, ry + rh))
    return (x - nx) ** 2 + (y - ny) ** 2 < r * r


def circle_hits_wall(x, y, r):
    """圆 (x,y,r) 是否撞到迷宫墙（无限迷宫，没有屏幕边界）。"""
    min_cx = int((x - r) // CELL)
    max_cx = int((x + r) // CELL)
    min_cy = int((y - r) // CELL)
    max_cy = int((y + r) // CELL)

    # 墙矩形会向相邻格凸出 WALL_T/2，所以扫描范围要比圆的外接格再多一格
    for cy in range(min_cy, max_cy + 2):
        for cx in range(min_cx, max_cx + 2):
            ensure_cell(cx, cy)

    for cy in range(min_cy, max_cy + 2):
        for cx in range(min_cx, max_cx + 2):
            if cells[(cx, cy)]["left"] and circle_rect(
                    x, y, r, cx * CELL - WALL_T / 2, cy * CELL, WALL_T, CELL):
                return True
    for cy in range(min_cy, max_cy + 2):
        for cx in range(min_cx, max_cx + 2):
            if cells[(cx, cy)]["up"] and circle_rect(
                    x, y, r, cx * CELL, cy * CELL - WALL_T / 2, CELL, WALL_T):
                return True
    return False


def target_zoom_for(dist):
    return max(MIN_ZOOM, min(MAX_ZOOM, BASE_DIST / max(dist, 1.0)))

# ---------------- 玩家 ----------------

class Player:
    def __init__(self, x, y, name, color, controls):
        self.x = x
        self.y = y
        self.name = name
        self.color = color
        self.controls = controls
        self.radius = R
        self.speed = 240.0          # 像素/秒
        self.dir = (1.0, 0.0)
        self.cooldown = 0.0
        self.alive = True

    def blocked(self, nx, ny, others):
        """目标位置是否撞墙或撞到另一个玩家。"""
        if circle_hits_wall(nx, ny, self.radius):
            return True
        for o in others:
            if o is self or not o.alive:
                continue
            if (o.x - nx) ** 2 + (o.y - ny) ** 2 < (self.radius + o.radius) ** 2:
                return True
        return False

    def update(self, keys, others, dt):
        if not self.alive:
            return

        # 左右键：连续旋转角度（按住持续转，同时按两个键则抵消）
        turn = 0
        if keys[self.controls["left"]]:
            turn -= 1
        if keys[self.controls["right"]]:
            turn += 1
        if turn:
            da = turn * ROT_SPEED * dt
            c, s = math.cos(da), math.sin(da)
            dx, dy = self.dir
            self.dir = (dx * c - dy * s, dx * s + dy * c)
            n = math.hypot(self.dir[0], self.dir[1]) or 1.0
            self.dir = (self.dir[0] / n, self.dir[1] / n)

        # W/S：沿面朝方向前进 / 后退（同时按两个键时前进优先）
        move = 0
        if keys[self.controls["up"]]:
            move = 1
        elif keys[self.controls["down"]]:
            move = -1
        if move:
            total = self.speed * dt
            # 细墙只有 5px，分成小步移动，避免高速穿墙
            steps = max(1, int(math.ceil(total / 3.0)))
            mx = self.dir[0] * move * total / steps
            my = self.dir[1] * move * total / steps
            for _ in range(steps):
                # 整体移动：撞墙（包括斜着撞）就完全停下，不沿墙滑动
                nx = self.x + mx
                ny = self.y + my
                if not self.blocked(nx, ny, others):
                    self.x = nx
                    self.y = ny

        self.cooldown = max(0.0, self.cooldown - dt)
        if self.cooldown <= 0 and any(keys[k] for k in self.controls["shoot"]):
            self.shoot()
            self.cooldown = 0.22

    def shoot(self):
        bx = self.x + self.dir[0] * (self.radius + 5)
        by = self.y + self.dir[1] * (self.radius + 5)
        # 炮口在墙里就不发射，避免贴墙射击直接自杀
        if circle_hits_wall(bx, by, 3):
            return
        if len(bullets) >= MAX_BULLETS:
            bullets.pop(0)
        bullets.append(Bullet(bx, by, self.dir, self))

# ---------------- 子弹 ----------------

class Bullet:
    def __init__(self, x, y, direction, owner):
        self.x = x
        self.y = y
        self.vx = direction[0] * 420.0
        self.vy = direction[1] * 420.0
        self.owner = owner
        self.radius = 3
        self.alive = True

    def update(self, players, dt):
        if not self.alive:
            return

        # 速度方向可能在子步中改变，所以每步重新计算位移
        speed = math.hypot(self.vx, self.vy)
        steps = max(1, int(math.ceil(speed * dt / 3.0)))

        for _ in range(steps):
            sx = self.vx * dt / steps
            sy = self.vy * dt / steps

            # X 轴：撞墙就翻转 vx
            if circle_hits_wall(self.x + sx, self.y, self.radius):
                self.vx = -self.vx
            else:
                self.x += sx

            # Y 轴：撞墙就翻转 vy
            if circle_hits_wall(self.x, self.y + sy, self.radius):
                self.vy = -self.vy
            else:
                self.y += sy

            # 任何玩家碰到子弹（包括发射者自己）立即爆炸
            for p in players:
                if not p.alive:
                    continue
                if (p.x - self.x) ** 2 + (p.y - self.y) ** 2 < (p.radius + self.radius) ** 2:
                    p.alive = False
                    self.alive = False
                    explosions.append(Explosion(p.x, p.y, p.color))
                    return

# ---------------- 爆炸特效 ----------------

class Explosion:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.t = 0.45

    def update(self, dt):
        self.t -= dt

    @property
    def alive(self):
        return self.t > 0

    def draw(self):
        k = 1 - max(0.0, self.t) / 0.45          # 0→1 逐渐扩散
        fade = 1 - k
        col = (int(self.color[0] * fade),
               int(self.color[1] * fade),
               int(self.color[2] * fade))
        sx, sy = to_screen(self.x, self.y)
        pygame.draw.circle(screen, col, (sx, sy),
                           max(1, int((6 + 26 * k) * zoom)), 2)
        pygame.draw.circle(screen, YELLOW, (sx, sy),
                           max(1, int((3 + 12 * k) * zoom)), 2)

# ---------------- 游戏状态 ----------------

players = []
bullets = []
explosions = []


def reset():
    global players, bullets, explosions, cam_x, cam_y, zoom
    reset_maze()
    bullets = []
    explosions = []

    p1x, p1y = CELL / 2, CELL / 2
    p2x = SPAWN2_CX * CELL + CELL / 2
    p2y = CELL / 2
    players = [
        Player(p1x, p1y, "Player1", RED,
               {"up": K_w, "down": K_s, "left": K_a, "right": K_d,
                "shoot": (K_j,)}),
        Player(p2x, p2y, "Player2", GREEN,
               {"up": K_UP, "down": K_DOWN, "left": K_LEFT, "right": K_RIGHT,
                "shoot": (K_KP1, K_RSHIFT)}),
    ]

    cam_x = (p1x + p2x) / 2
    cam_y = (p1y + p2y) / 2
    zoom = target_zoom_for(math.hypot(p2x - p1x, p2y - p1y))

# ---------------- 渲染 ----------------

def to_screen(x, y):
    """世界坐标 → 屏幕坐标（经过镜头平移与缩放）。"""
    return (int((x - cam_x) * zoom + width / 2),
            int((y - cam_y) * zoom + height / 2))


def draw_maze():
    screen.fill(BG)

    half_w = width / 2 / zoom
    half_h = height / 2 / zoom
    wx0 = cam_x - half_w
    wx1 = cam_x + half_w
    wy0 = cam_y - half_h
    wy1 = cam_y + half_h
    min_cx = int(math.floor(wx0 / CELL))
    max_cx = int(math.floor(wx1 / CELL))
    min_cy = int(math.floor(wy0 / CELL))
    max_cy = int(math.floor(wy1 / CELL))

    # 屏幕外多生成一圈作为缓冲，避免看到迷宫边界
    for cy in range(min_cy - GEN_BUF, max_cy + GEN_BUF + 1):
        for cx in range(min_cx - GEN_BUF, max_cx + GEN_BUF + 1):
            ensure_cell(cx, cy)

    ww = max(1, int(WALL_T * zoom))
    sh = max(1, int(CELL * zoom))
    sw = max(1, int(CELL * zoom))

    for cy in range(min_cy, max_cy + 2):
        for cx in range(min_cx, max_cx + 1):
            if cells[(cx, cy)]["left"]:
                sx = (cx * CELL - WALL_T / 2 - cam_x) * zoom + width / 2
                sy = (cy * CELL - cam_y) * zoom + height / 2
                pygame.draw.rect(screen, WALL_EDGE, (int(sx), int(sy), ww, sh))
    for cy in range(min_cy, max_cy + 1):
        for cx in range(min_cx, max_cx + 2):
            if cells[(cx, cy)]["up"]:
                sx = (cx * CELL - cam_x) * zoom + width / 2
                sy = (cy * CELL - WALL_T / 2 - cam_y) * zoom + height / 2
                pygame.draw.rect(screen, WALL_EDGE, (int(sx), int(sy), sw, ww))


def draw_player(p):
    if not p.alive:
        return
    sx, sy = to_screen(p.x, p.y)
    r = max(2, int(p.radius * zoom))
    pygame.draw.circle(screen, p.color, (sx, sy), r)
    pygame.draw.circle(screen, WHITE, (sx, sy), r, 1)
    # 朝向指示线
    ex, ey = to_screen(p.x + p.dir[0] * (p.radius + 6),
                       p.y + p.dir[1] * (p.radius + 6))
    pygame.draw.line(screen, p.color, (sx, sy), (ex, ey), max(1, int(2 * zoom)))


def draw_overlay(title, subtitle=""):
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    t = bigfont.render(title, True, WHITE)
    screen.blit(t, t.get_rect(center=(width // 2, height // 2 - 20)))
    if subtitle:
        s = font.render(subtitle, True, WHITE)
        screen.blit(s, s.get_rect(center=(width // 2, height // 2 + 40)))


def draw(paused, show_over, winner):
    draw_maze()
    for b in bullets:
        if b.alive:
            sx, sy = to_screen(b.x, b.y)
            pygame.draw.circle(screen, YELLOW, (sx, sy),
                               max(1, int(b.radius * zoom)))
    for p in players:
        draw_player(p)
    for e in explosions:
        e.draw()

    if paused and not show_over:
        draw_overlay("PAUSED", "Press SPACE to resume")
    if show_over:
        title = ("%s wins" % winner) if winner else "Draw"
        draw_overlay(title, "Press R to restart, ESC to quit")

# ---------------- 主循环 ----------------

def main():
    global cam_x, cam_y, zoom
    reset()
    paused = False
    game_over = False
    end_timer = 0.0
    winner = ""

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE and not game_over:
                    paused = not paused
                elif event.key == K_r and game_over:
                    reset()
                    paused = False
                    game_over = False
                    end_timer = 0.0
                    winner = ""

        if not paused:
            # 镜头：中心 = 存活玩家坐标平均值；缩放随玩家距离变化
            alive = [p for p in players if p.alive]
            if alive:
                tx = sum(p.x for p in alive) / len(alive)
                ty = sum(p.y for p in alive) / len(alive)
                if len(alive) == 2:
                    tz = target_zoom_for(
                        math.hypot(alive[0].x - alive[1].x,
                                   alive[0].y - alive[1].y))
                else:
                    tz = 1.0
                cam_x += (tx - cam_x) * min(1.0, 8.0 * dt)
                cam_y += (ty - cam_y) * min(1.0, 8.0 * dt)
                zoom += (tz - zoom) * min(1.0, 6.0 * dt)

            if game_over:
                # 爆炸动画期间残余子弹继续飞，双方都可能再被击中
                if end_timer > 0:
                    end_timer -= dt
                    for b in bullets:
                        b.update(players, dt)
                        if b.alive and (b.x - cam_x) ** 2 + (b.y - cam_y) ** 2 > BULLET_RANGE ** 2:
                            b.alive = False
                    bullets[:] = [b for b in bullets if b.alive]
                    if end_timer <= 0:
                        alive2 = [p for p in players if p.alive]
                        winner = alive2[0].name if len(alive2) == 1 else ""
            else:
                keys = pygame.key.get_pressed()
                for p in players:
                    p.update(keys, players, dt)
                for b in bullets:
                    b.update(players, dt)
                    if b.alive and (b.x - cam_x) ** 2 + (b.y - cam_y) ** 2 > BULLET_RANGE ** 2:
                        b.alive = False
                bullets[:] = [b for b in bullets if b.alive]

                alive = [p for p in players if p.alive]
                if len(alive) <= 1:
                    game_over = True
                    end_timer = 0.6
                    winner = alive[0].name if len(alive) == 1 else ""

            for e in explosions:
                e.update(dt)
            explosions[:] = [e for e in explosions if e.alive]

        draw(paused, game_over and end_timer <= 0, winner)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
