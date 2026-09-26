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

pygame.init()

screen = pygame.display.set_mode((width,height))

class Pad:
    def __init__(self, pad):
        self.pad = pad
        self.blanks = []
        self.blocks = []
        for i in range(level):
            for j in range(level):
                if self.pad[i][j] == 0:
                    self.blanks.append((i,j))
                else:
                    self.blocks.append((i,j))
        self.switches = [0,0,0,0]
        self.pads = []
        for i in range(4):
            temp = []
            for j in range(level):
                temp.append(pad[j].copy())
            self.switches[i] = move(temp,sl[i])
            self.pads.append(temp)
    def score(self):
        board = self.pad
        n = level
        score = 0
    # =====================
    # 1. 空格奖励
    # =====================
        empty = 0
        max_tile = 0
        for i in range(n):
            for j in range(n):
                if board[i][j] == 0:
                    empty += 1
                else:
                    max_tile = max(max_tile, board[i][j])
        score += empty * 100
    # =====================
    # 2. 最大块奖励
    # 使用 log2 防止数值过大
    # =====================
        if max_tile > 0:
            score += math.log2(max_tile) * 50
    # =====================
    # 3. 角落权重
    # 希望大数字待在角落
    # =====================
        weight = [
                [16, 8, 4, 2],
                [8,  4, 2, 1],
                [4,  2, 1, 0],
                [2,  1, 0, 0]
                ]
        for i in range(n):
            for j in range(n):
                if board[i][j] != 0:
                    score += math.log2(board[i][j]) * weight[i][j]
    # =====================
    # 4. 平滑性
    # 相邻数字差距越小越好
    # =====================
        smoothness = 0
        for i in range(n):
            for j in range(n):
                if board[i][j] != 0:
                    value = math.log2(board[i][j])
                # 右边
                    if j + 1 < n and board[i][j+1] != 0:
                        diff = abs(
                                value - math.log2(board[i][j+1])
                                )
                        smoothness -= diff
                # 下边
                    if i + 1 < n and board[i+1][j] != 0:
                        diff = abs(
                                value - math.log2(board[i+1][j])
                                )
                        smoothness -= diff
        score += smoothness * 10
    # =====================
    # 5. 单调性
    # =====================
        monotonicity = 0
    # 横向
        for i in range(n-1):
            for j in range(n-1):
                if board[i][j] > board[i][j+1]:
                    monotonicity += math.log2(
                            max(board[i][j],1)
                            )
                else:
                    monotonicity -= math.log2(
                            max(board[i][j+1],1)
                            )
    # 纵向
        for j in range(n-1):
            for i in range(n-1):
                if board[i][j] > board[i+1][j]:
                    monotonicity += math.log2(
                            max(board[i][j],1)
                            )
                else:
                    monotonicity -= math.log2(
                            max(board[i][j+1],1)
                            )
        score += monotonicity * 5
        return score
    def evaluate(self, k):
        scores = [0,0,0,0]
        for k in (2,4):
            for i,p in enumerate(self.pads):
                obj = Pad(p)
                for x,y in obj.blanks:
                    np = []
                    for j in p:
                        np.append(j.copy())
                    np[x][y] = k
                    nobj = Pad(np)
                    scores[i] += nobj.score()
        tag = 0
        for i in range(4):
            if self.switches[i] != 0:
                tag = i
        for i,s in enumerate(scores):
            if self.switches[i] == 0:
                continue
            if scores[tag] < s:
                tag = i
        if self.switches[tag] == 0:
            print("out")
            out()
        return tag

def log(x):
    n = 0
    while x != 1:
        x /= 2
        n += 1
    return n

def out():
    pygame.quit()
    sys.exit()
    exit()

def txt(content,center):
    myfont = pygame.font.SysFont("microsoftsansserif",txtsize,True,False)
    obj = myfont.render(content,True,txtcolor[log(int(content))])
    txtrect = obj.get_rect()
    txtrect.center = center
    screen.blit(obj,txtrect)

def over(wall):
    center = (width / 2,height / 2)
    for i in range(wall):
        for j in i:
            if j >= 2 ** int(level * level / 3):
                txt("Win",center)
                out()
    txt("Defeat",center)
    out()

def init(wall):
    for j in range(level):
        wall.append([0 for i in range(level)])

def produce(wall):
    AccessiblePlace = []
    for i in range(level):
        for j in range(level):
            if wall[i][j] == 0:
                AccessiblePlace.append((i,j))
    if len(AccessiblePlace) != 0:
        i,j = random.choice(AccessiblePlace)
        wall[i][j] = random.randint(1,2) * 2

def receive():
    sign = None
    for event in pygame.event.get():
        if event.type == QUIT:
            out()
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                out()
            elif event.key in (K_UP,K_w):
                sign = 'u'
            elif event.key in (K_DOWN,K_s):
                sign = 'd'
            elif event.key in (K_LEFT,K_a):
                sign = 'l'
            elif event.key in (K_RIGHT,K_d):
                sign = 'r'
            else:
                sign = None
    return sign

def move(wall,sign):
    switch = 0
    if sign == 'u':
        for x in range(level):
            for i in range(level - 1):
                for y in range(1,level):
                    if wall[y][x] == 0: continue
                    if wall[y - 1][x] == 0:
                        wall[y - 1][x] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
            for y in range(1,level):
                if wall[y][x] == 0: continue
                if wall[y][x] == wall[y - 1][x]:
                    wall[y - 1][x] += wall[y][x]
                    wall[y][x] = 0
                    switch += 1
            for i in range(level - 1):
                for y in range(1,level):
                    if wall[y][x] == 0: continue
                    if wall[y - 1][x] == 0:
                        wall[y - 1][x] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
    elif sign == 'd':
        for x in range(level):
            for i in range(level - 1):
                for y in range(level - 2,-1,-1):
                    if wall[y][x] == 0: continue
                    if wall[y + 1][x] == 0:
                        wall[y + 1][x] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
            for y in range(level - 2,-1,-1):
                if wall[y][x] == 0: continue
                if wall[y][x] == wall[y + 1][x]:
                    wall[y + 1][x] += wall[y][x]
                    wall[y][x] = 0
                    switch += 1
            for i in range(level - 1):
                for y in range(level - 2,-1,-1):
                    if wall[y][x] == 0: continue
                    if wall[y + 1][x] == 0:
                        wall[y + 1][x] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
    elif sign == 'l':
        for y in range(level):
            for i in range(level - 1):
                for x in range(1,level):
                    if wall[y][x] == 0: continue
                    if wall[y][x - 1] == 0:
                        wall[y][x - 1] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
            for x in range(1,level):
                if wall[y][x] == 0: continue
                if wall[y][x] == wall[y][x - 1]:
                    wall[y][x - 1] += wall[y][x]
                    wall[y][x] = 0
                    switch += 1
            for i in range(level - 1):
                for x in range(1,level):
                    if wall[y][x] == 0: continue
                    if wall[y][x - 1] == 0:
                        wall[y][x - 1] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
    elif sign == 'r':
        for y in range(level):
            for i in range(level - 1):
                for x in range(level - 2,-1,-1):
                    if wall[y][x] == 0: continue
                    if wall[y][x + 1] == 0:
                        wall[y][x + 1] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
            for x in range(level - 2,-1,-1):
                if wall[y][x] == 0: continue
                if wall[y][x] == wall[y][x + 1]:
                    wall[y][x + 1] += wall[y][x]
                    wall[y][x] = 0
                    switch += 1
            for i in range(level - 1):
                for x in range(level - 2,-1,-1):
                    if wall[y][x] == 0: continue
                    if wall[y][x + 1] == 0:
                        wall[y][x + 1] = wall[y][x]
                        wall[y][x] = 0
                        switch += 1
    if switch > 0:
        produce(wall)
    return switch

def draw(wall):
    screen.fill(bgc)
    for i in range(level):
        for j in range(level):
            if wall[i][j] == 0:
                continue
            center = ((j * size + size / 2),(i * size + size / 2))
            txt(str(wall[i][j]),center)
    pygame.display.update()

def main():
    wall = []
    init(wall)
    produce(wall)
    sign = None
    score = 0
    point = 0
    tag = 0
    while True:
        sign = receive()
        w = Pad(wall)
        sign = sl[w.evaluate(2)]
        time.sleep(cd)
        point = move(wall,sign)
        score += point
        if point == 0:
            tag += 1
            tag %= 4
        draw(wall)
        
if __name__ == "__main__":
    main()
