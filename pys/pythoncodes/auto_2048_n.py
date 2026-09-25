import pygame
import sys
import random
from pygame.locals import *

level = 8
size = 100
width = level * size
height = level * size

txtsize = 50
bgc = (255,255,255)
txtcolor = (0,0,0)

pygame.init()

screen = pygame.display.set_mode((width,height))

def out():
    pygame.quit()
    sys.exit()
    exit()

def txt(content,center):
    myfont = pygame.font.SysFont("microsoftsansserif",txtsize,True,False)
    obj = myfont.render(content,True,txtcolor)
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
    sl = ('u','l','d','r')
    while True:
        sign = receive()
        sign = sl[tag]
        point = move(wall,sign)
        score += point
        if point == 0:
            tag += 1
            tag %= 4
        draw(wall)
        
if __name__ == "__main__":
    main()
