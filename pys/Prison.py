
import sys

import pygame
from pygame.locals import *

stdsize = 10

black = (0,0,0)
white = (255,255,255)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)

width = 80 * stdsize
height = 60 * stdsize

bgcolor = black

pygame.init()

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Prison")
clock = pygame.time.Clock()

class Obj:
    def __init__(self,x,y,name,color):
        self.x = x
        self.y = y
        self.name = name
        self.vel = stdsize / 2
        self.color = color
        self.heart = stdsize
        self.bulletcolor = blue
        self.direction = (0,0)

    def toward(self):
        min_distance = width ** 2 + height ** 2
        tag = 0
        for i in range(len(objs)):
            distance = objs[i].x ** 2 + objs[i].y ** 2
            if distance < min_distance and distance != 0:
                min_distance = distance
                tag = i
        self.direction = (objs[tag].x / min_distance, objs[tag].y / min_distance)

    def check1(self):
        if inputs[pygame.K_a] and self.x > 0:
            self.x -= self.vel
        if inputs[pygame.K_d] and self.x < width:
            self.x += self.vel
        if inputs[pygame.K_w] and self.y > 0:
            self.y -= self.vel
        if inputs[pygame.K_s] and self.y < height:
            self.y += self.vel
        self.toward()
        if inputs[pygame.K_j]:
            self.shoot()

    def check2(self):
        if inputs[pygame.K_UP] and self.y > 0:
            self.y -= self.vel
        if inputs[pygame.K_DOWN] and self.y < height:
            self.y += self.vel
        if inputs[pygame.K_LEFT] and self.x > 0:
            self.x -= self.vel
        if inputs[pygame.K_RIGHT] and self.x < width:
            self.x += self.vel
        self.toward()
        if inputs[pygame.K_KP1]:
            self.shoot()

    def check(self):
        pass

    def shoot(self):
        objs.append(Bullet(self.x,self.y,self.name,self.bulletcolor,self.vel,stdsize,stdsize / 4,self.heart,self.direction))

    def draw(self):
        pygame.draw.circle(screen,self.color,(self.x,self.y),stdsize / 2)

class Bullet(Obj):
    def __init__(self,x,y,name,color,vel,length,breadth,mass,direction):
        Obj.__init__(self,x,y,name,color)
        self.vel = vel
        self.length = length
        self.breadth = breadth
        self.mass = mass
        self.direction = direction

    def check(self):
        self.x += self.direction[0] * self.vel
        self.y += self.direction[1] * self.vel
        for i in objs:
            if i.name != self.name:
                if i.x == self.x and i.y == self.y:
                    i.heart -= self.mass
                    self.heart = 0

    def draw(self):
        pygame.draw.line(screen,self.color,(self.x,self.y),(self.x + self.direction[0] * self.length,self.y + self.direction[1] * self.length),self.breadth)

def out():
    pygame.quit()
    sys.exit()

def stop():
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                out()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    out()
                elif event.key == K_SPACE:
                    return

def receive():
    for event in pygame.event.get():
        if event.type == QUIT:
            out()
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                out()
            elif event.key == K_SPACE:
                stop()

def update():
    for i in objs:
        if i.name == "Player1":
            i.check1()
        elif i.name == "Player2":
            i.check2()
        else:
            i.check()

def draw():
    screen.fill(bgcolor)
    for i in objs:
        i.draw()
    pygame.display.flip()
    pygame.display.update()

objs = [Obj(width / 4, height / 4, "Player1", red),Obj(width / 4 * 3, height / 4 * 3, "Player2", green)]
inputs = pygame.key.get_pressed()

def main():
    global inputs
    while True:
        inputs = pygame.key.get_pressed()
        receive()
        update()
        draw()
        clock.tick(60)
        pygame.display.set_caption("Prion FPS:%d" % clock.get_fps())

if __name__ == '__main__':
    main()