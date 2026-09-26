import tkinter as tk
import random


SIZE = 4


class Game2048:

    def __init__(self):
        self.board = [[0 for _ in range(SIZE)] for _ in range(SIZE)]
        self.score = 0
        self.new_tile()
        self.new_tile()


    # 随机生成2或4
    def new_tile(self):
        empty = []

        for i in range(SIZE):
            for j in range(SIZE):
                if self.board[i][j] == 0:
                    empty.append((i, j))

        if empty:
            x, y = random.choice(empty)
            self.board[x][y] = 2 if random.random() < 0.9 else 4



    # 压缩一行
    def compress(self, row):

        new = []

        for x in row:
            if x != 0:
                new.append(x)

        while len(new) < SIZE:
            new.append(0)

        return new



    # 合并一行
    def merge(self, row):

        for i in range(SIZE-1):

            if row[i] != 0 and row[i] == row[i+1]:

                row[i] *= 2
                self.score += row[i]

                row[i+1] = 0

        return row



    # 左移动
    def move_left(self):

        changed = False

        for i in range(SIZE):

            old = self.board[i][:]

            row = self.compress(old)

            row = self.merge(row)

            row = self.compress(row)

            self.board[i] = row

            if old != row:
                changed = True

        return changed



    # 旋转棋盘
    def rotate(self):

        self.board = [
            list(row)
            for row in zip(*self.board[::-1])
        ]



    # 利用旋转实现四个方向
    def move(self, direction):

        if direction == "left":

            changed = self.move_left()


        elif direction == "right":

            self.rotate()
            self.rotate()

            changed = self.move_left()

            self.rotate()
            self.rotate()


        elif direction == "up":

            self.rotate()
            self.rotate()
            self.rotate()

            changed = self.move_left()

            self.rotate()


        elif direction == "down":

            self.rotate()

            changed = self.move_left()

            self.rotate()
            self.rotate()
            self.rotate()


        if changed:
            self.new_tile()


        return changed



    # 判断是否结束
    def game_over(self):

        # 有空位
        for row in self.board:
            if 0 in row:
                return False


        # 横向可合并
        for i in range(SIZE):
            for j in range(SIZE-1):
                if self.board[i][j] == self.board[i][j+1]:
                    return False


        # 纵向可合并
        for i in range(SIZE-1):
            for j in range(SIZE):
                if self.board[i][j] == self.board[i+1][j]:
                    return False


        return True





class GUI2048:


    def __init__(self):

        self.game = Game2048()


        self.root = tk.Tk()

        self.root.title("2048")

        self.root.geometry("400x500")


        self.score_label = tk.Label(
            self.root,
            text="Score: 0",
            font=("Arial",20)
        )

        self.score_label.pack()


        self.cells = []

        frame = tk.Frame(self.root)

        frame.pack()


        for i in range(SIZE):

            row=[]

            for j in range(SIZE):

                label=tk.Label(
                    frame,
                    text="",
                    width=5,
                    height=2,
                    font=("Arial",25),
                    relief="solid"
                )

                label.grid(
                    row=i,
                    column=j,
                    padx=5,
                    pady=5
                )

                row.append(label)


            self.cells.append(row)


        self.root.bind("<Key>", self.key)

        self.root.focus_force()


        self.update()



    def key(self,event):

        keys={
            "Left":"left",
            "Right":"right",
            "Up":"up",
            "Down":"down"
        }


        if event.keysym in keys:

            changed=self.game.move(
                keys[event.keysym]
            )


            if changed:
                self.update()


            if self.game.game_over():

                self.score_label.config(
                    text="Game Over"
                )



    def update(self):

        for i in range(SIZE):

            for j in range(SIZE):

                value=self.game.board[i][j]

                if value==0:
                    text=""
                else:
                    text=str(value)


                self.cells[i][j].config(
                    text=text
                )


        self.score_label.config(
            text=f"Score: {self.game.score}"
        )




    def run(self):

        self.root.mainloop()



if __name__=="__main__":

    app=GUI2048()

    app.run()
