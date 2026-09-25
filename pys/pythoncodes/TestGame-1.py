import os
import sys
import random
import time
import ctypes
from keyboard import is_pressed

Width = 100
Height = 20
UpSpace = 17
DownSpace = 2
Name = "SamKing"

class Actor:
    def __init__(self,name):
        self.x = 0
        self.y = 0
        self.level = 1
        self.heart = self.level * 10
        self.weapon = self.level * 5
        self.armor = self.level * 2
        self.shell = []
        self.direction = "RIGHT"
        self.name = name
        self.shape = "A"
        self.ShellShape = "o"
        self.speed = 1

    def move(self,direction,step):
        if "UP" in direction and self.y >= 1:
            self.y -= step
            self.direction = "UP"
        elif "DOWN" in direction and self.y <= Height - 2:
            self.y += step
            self.direction = "DOWN"
        elif "LEFT" in direction and self.x >= 1:
            self.x -= step
            self.direction = "LEFT"
        elif "RIGHT" in direction and self.x <= Width - 2:
            self.x += step
            self.direction = "RIGHT"

    def shout(self):
        self.shell.append(Shell(self.x,self.y,self.name,direction=self.direction))

    def update(self):
        for i in range(len(self.shell) - 1,0,-1):
            if self.shell[i].exists == False:
                del self.shell[i]
            else:
                self.shell[i].update()

class Shell:
    def __init__(self,x,y,owner,power=1,speed=1,direction="RIGHT"):
        self.power = power
        self.x = x
        self.y = y
        self.speed = speed
        self.direction = direction
        self.owner = owner
        self.exists = True

    def update(self):
        if self.direction == "UP":
            self.y -= self.speed
        elif self.direction == "DOWN":
            self.y += self.speed
        elif self.direction == "LEFT":
            self.x -= self.speed
        elif self.direction == "RIGHT":
            self.x += self.speed
        if self.x >= Width or self.x <= -1 or self.y >= Height or self.y <= -1:
            self.exists = False

class COORD(ctypes.Structure):
    _fields_ = [("X",ctypes.c_short),("Y",ctypes.c_short)]
    def __init__(self,x,y):
        self.X = x
        self.Y = y

actor = Actor(Name)
actor.x = 0
actor.y = UpSpace - 1

def gotoxy(x,y):
    STD_OUTPUT_HANDLE = -11
    hOut = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    INIT_POS = COORD(x,y)
    ctypes.windll.kernel32.SetConsoleCursorPosition(hOut,INIT_POS)

def Quit():
    sys.exit(0)

def Stop(seconds=0):
    Draw(0)
    if seconds == 0:
        time.sleep(1)
        while True:
            if ip(" "):
                time.sleep(1)
                return 0
    else:
        time.sleep(seconds)

def get_fps(old_time,new_time):
    delta_time = new_time - old_time
    fps = 1 / delta_time
    return int(fps)

def ip(key):
    if is_pressed(key):
        return True
    else:
        return False

def CheckInput():
    if ip("w") or ip("W"):
        actor.move("UP",actor.speed)
    elif ip("s") or ip("S"):
        actor.move("DOWN",actor.speed)
    elif ip("a") or ip("A"):
        actor.move("LEFT",actor.speed)
    elif ip("d") or ip("D"):
        actor.move("RIGHT",actor.speed)

def Draw(fps):
    gotoxy(0,0)
    temp = ""
    temp += ("+" + "-" * (Width) + "+\n")
    for y in range(Height):
        temp += "|"
        actor_shell_x_list = []
        actor_shell_y_list = []
        if len(actor.shell):
            for i in actor.shell:
                actor_shell_x_list.append(i.x)
                actor_shell_y_list.append(i.y)
        for x in range(Width):
            if x == actor.x and y == actor.y:
                temp += actor.shape
            elif x in actor_shell_x_list and y in actor_shell_y_list:
                temp += actor.ShellShape
            else:
                temp += " "
        temp += "|\n"
    temp += ("+" + "-" * (Width) + "+\nfps:" + str(fps))
    print(temp,end="")

def main():
    os.system("mode con cols=%s lines=%s" % (str(Width + 10), str(Height + 10)))
    fps = 0
    while True:
        if fps > 300:
            time.sleep(0.01)
        old_time = time.time()
        CheckInput()
        if ip("j"):
            actor.shout()
        actor.update()
        Draw(fps)
        if ip(" "):
            Stop()
        if ip("q") or ip("Q"):
            Quit()
        new_time = time.time()
        fps = get_fps(old_time,new_time)

if __name__ == "__main__":
    main()