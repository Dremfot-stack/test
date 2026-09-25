import pygame
from pygame.locals import *
import math
import sys

width = 300
height = width

white = (255,255,255)
black = (0,0,0)

bgc = black
color = white

rate = 2
stdv = 0.0005
swap = 0
v1 = stdv
v2 = rate * stdv
d1 = 0
d2 = 0

radius = width / 4
size = 5

pygame.init()

screen = pygame.display.set_mode((width,height))

pygame.display.set_caption("loading...")

def out():
    pygame.quit()
    sys.exit()

def draw_arc():
    global d1,d2,v1,v2,swap

    d1 += v1
    d2 += v2

    if abs(d1 - d2) >= math.pi:
        temp = v1
        v1 = v2
        v2 = temp

    screen.fill(bgc)
    rect = pygame.rect.Rect(width / 2 - radius,height / 2 - radius,2 * radius,2 * radius)

    if abs(d1 - d2) < stdv:
        swap += 1
        temp = d1
        d1 = d2
        d2 = temp

    if swap % 2 == 1:
        pygame.draw.arc(screen,color,rect,d2,d1,width=size)
    else:
        pygame.draw.arc(screen,color,rect,d1,d2,width=size)
    
    pygame.display.update()

def main():
    while True:

        for event in pygame.event.get():
            if event.type == QUIT:
                out()
            elif event.type == KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    out()
        draw_arc()
    return 0

if __name__ == "__main__":
    main()