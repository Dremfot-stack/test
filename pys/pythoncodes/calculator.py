import tkinter as tk
from tkinter import ttk


class SimpleCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("简易计算器")
        self.root.geometry("300x400")
        self.root.resizable(False, False)  # 禁止调整窗口大小

        # 显示框
        self.display_var = tk.StringVar()
        self.display = ttk.Entry(
            root,
            textvariable=self.display_var,
            font=('Arial', 20),
            justify='right'
        )
        self.display.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky='nsew')

        # 按钮布局
        buttons = [
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3),
            ('0', 4, 0), ('.', 4, 1), ('=', 4, 2), ('+', 4, 3),
        ]

        # 创建按钮
        for (text, row, col) in buttons:
            btn = ttk.Button(
                root,
                text=text,
                command=lambda t=text: self.on_button_click(t)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')

        # 设置网格权重（让按钮自适应大小）
        for i in range(5):
            root.grid_rowconfigure(i, weight=1)
        for i in range(4):
            root.grid_columnconfigure(i, weight=1)

        self.current_expression = ""

    def on_button_click(self, text):
        if text == '=':
            try:
                # 计算表达式结果
                result = eval(self.current_expression)
                self.display_var.set(str(result))
                self.current_expression = str(result)
            except Exception as e:
                self.display_var.set("错误")
                self.current_expression = ""
        else:
            # 拼接表达式
            self.current_expression += text
            self.display_var.set(self.current_expression)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleCalculator(root)
    root.mainloop()
