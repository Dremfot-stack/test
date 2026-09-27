import tkinter
import time
import sys
import random
import pygame
from pygame.locals import *

##############################################################

rate = 0.618
size = 20
margin_rate = 1
counter = [0,0,0,0] # u,d,l,r
history = "d"

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
        self.summary = [block(random.randint(0,int(margin.height / size) - 1) * size,size,random.randint(0,int(margin.width / size) - 1) * size,size,level_board[self.effect[i] - 1],level_board[self.effect[i] - 1],food_margin_breadth) for i in range(self.number)]
        
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
        for i in range(self.length):
            (self.body[i]).draw()
        pos = (self.body[0].left,self.body[0].up,self.body[0].width,self.body[0].height)
        pygame.draw.rect(screen,snake_head_symbol_color,pos,snake_head_symbol_breadth)
        
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
snake2 = snake('u',size,size,snake_init_length)

snakes = []
snakes.append(snake1)
snakes.append(snake2)

F = food(food_number)

def ifeat(S):
    effect = 0
    for i in range(F.number):
        if F.summary[i].left == S.body[0].left and F.summary[i].up == S.body[0].up:
            effect = F.effect[i]
            F.effect[i] = random.randint(1,9)
            x = random.randint(0,int(margin.width / size) - 1) * size
            y = random.randint(0,int(margin.height / size) - 1) * size
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
    
def kill():
    print(history)
    pygame.quit()
    sys.exit()
    exit()

def receive():
    global stoper
    for event in pygame.event.get():
        if event.type == QUIT:
            kill()
        elif event.type == KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                kill()
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
                            kill()
                        elif event.type == KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                kill()
                            elif event.key == pygame.K_SPACE:
                                stop = False

def draw():
    screen.fill(blue)
    
    pygame.display.set_caption("Snake length:%d" % snake1.length)
    margin.draw()
    F.draw()
    snake1.draw()
    snake2.draw()
    
    pygame.display.update()

def waller():
    wall_list = []
    for i in snakes:
        for j in i.body:
            pos = (j.left,j.up)
            wall_list.append(pos)
    if len(wall_list) >= int(width * height / size / size):
        kill()
    return wall_list

def permit(x,y):
    wall_list = waller()
    region = []
    dimension = 5
    for i in range(dimension):
        temp = []
        for j in range(dimension):
            temp.append(1)
        region.append(temp)
    verge = int((dimension - 1) / 2)
    for i in range(-verge,verge + 1,1):
        for j in range(-verge,verge + 1,1):
            if (x + i * size,y + j * size) in wall_list:
                region[j + 1][i + 1] = 0
    return region
    
def ac(S):                       #auto control
    global history
    x = S.body[0].left
    y = S.body[0].up

    distance_list = []
    for i in F.summary:
        distance = abs(i.left - x) + abs(i.up - y)
        distance_list.append(distance)
    min_distance = min(distance_list)
    for i in range(F.number):
        if distance_list[i] == min_distance:
            break
    X = F.summary[i].left
    Y = F.summary[i].up

    region = permit(x,y)
    decision = [0,0,0,0]
    decide_list = ['u','d','l','r']

    if x < X:
        decision[3] += 1
    if x > X:
        decision[2] += 1
    if y < Y:
        decision[1] += 1
    if y > Y:
        decision[0] += 1

    if (x + size >= width) or (S.direction == 'l'):
        decision[3] -= 10
    if (x - size < 0) or (S.direction == 'r'):
        decision[2] -= 10
    if (y + size >= height) or (S.direction == 'u'):
        decision[1] -= 10
    if (y - size < 0) or (S.direction == 'd'):
        decision[0] -= 10
    
    dimension = len(region[0])
    middle = int((dimension - 1) / 2)
    for i in range(0,middle,1):
        if region[i][middle] == 0:
            decision[0] -= ((i + 1) * 3)
    for i in range(dimension - 1,middle,-1):
        if region[i][middle] == 0:
            decision[1] -= ((dimension - i) * 3)
    for i in range(0,middle,1):
        if region[middle][i] == 0:
            decision[2] -= ((i + 1) * 3)
    for i in range(dimension - 1,middle,-1):
        if region[middle][i] == 0:
            decision[3] -= ((dimension - i) * 3)
    
    deal = max(decision)
    print(decision,end="\t")
    for i in range(4):
        if decision[i] == deal:
            break
    print(decide_list[i])
    if S.direction != decide_list[i]:
        history += decide_list[i]
        S.direction = decide_list[i]

def check():
    x = snake1.body[0].left
    y = snake1.body[0].up
    for i in range(1,len(snake1.body)):
        if (snake1.body[i].left == x and snake1.body[i].up == y) or x < 0 or x >= width or y < 0 or y >= height:
            kill()

def main():
    
    while True:
        time.sleep(0.05)
        receive()
        snake1.move()
        ac(snake2)
        snake2.move()
        snake1.increase(ifeat(snake1))
        snake2.increase(ifeat(snake2))
        draw()
        check()


if __name__ == "__main__":
    main()
