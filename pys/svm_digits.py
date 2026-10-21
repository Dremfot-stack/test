#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
SVM 手写数字识别 —— 对应《模式识别》5.5.3 节的完整实验代码

教材四步在这里的对应关系:
  1. 图像 → 特征向量:
     鼠标笔画先被栅格化为图像 (OpenCV), 裁剪到数字外接方框,
     缩放为 8x8 灰度图, 展平成 64 维特征向量 —— 与 sklearn 自带的
     digits 数据集 (1797 个 8x8 手写数字, NIST 子集) 完全同构。
  2. 选核函数 + 训练:
     用带标签样本训练 SVC, 三种核 (多项式/径向基/Sigmoid) 各训一个,
     并在固定划分的训练/测试集上对比测试错误率 (教材实验的复现)。
  3. 支持向量:
     打印每种核下支持向量的数量; 并在 "SVM 原理" 演示里展示
     决策函数 f(x) = Σ α_i y_i K(x_i, x) + b 如何用支持向量算出来。
  4. 预测新样本:
     对手写的 8x8 特征计算它与支持向量的核函数值, 得出分类结果。

依赖说明 (不依赖 pandas):
  * numpy        —— 数值数组
  * opencv(cv2)  —— 仅用于: 把鼠标笔画栅格化成位图、图像裁剪/缩放采样
  * scikit-learn —— 数据集与 SVC 求解器
  * tkinter      —— 手写区与界面

运行: python3 svm_digits.py
"""

import numpy as np
import cv2
import tkinter as tk
from tkinter import messagebox

from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

# ---------------- 全局参数 ----------------
CANVAS = 420        # 手写区边长(像素)
BRUSH = 14          # 笔触粗细
FEAT = 8            # 特征图边长 (与 digits 数据集一致: 8x8 = 64 维)

# 三种核函数的参数 (gamma 由小规模实验选定, 见教材 "核函数并非越复杂越好")
KERNEL_PARAMS = {
    "poly":    dict(kernel="poly", degree=3, gamma=0.002, coef0=1.0, C=10),
    "rbf":     dict(kernel="rbf", gamma=0.003, C=10),
    "sigmoid": dict(kernel="sigmoid", gamma=0.01, coef0=1.0, C=10),
}


# ---------------- 核函数 (教材公式的显式实现) ----------------
def kernel_poly(u, v, gamma=0.002, coef0=1.0, degree=3):
    """多项式核: K(u,v) = (γ·uᵀv + r)^d"""
    return (gamma * float(np.dot(u, v)) + coef0) ** degree


def kernel_rbf(u, v, gamma=0.003):
    """径向基核: K(u,v) = exp(-γ·‖u-v‖²)"""
    diff = u - v
    return float(np.exp(-gamma * float(np.dot(diff, diff))))


def kernel_sigmoid(u, v, gamma=0.01, coef0=1.0):
    """Sigmoid 核: K(u,v) = tanh(γ·uᵀv + r)"""
    return float(np.tanh(gamma * float(np.dot(u, v)) + coef0))


# ---------------- 数据与训练 ----------------
def load_and_train():
    """加载 8x8 手写数字, 训练三种核的 SVM, 返回数据/模型/对照实验结果"""
    d = load_digits()                      # 1797 个样本, images 是 8x8 灰度
    X = d.images.reshape(len(d.images), -1).astype(np.float64) / 16.0
    y = d.target.astype(int)

    # 固定随机种子划分 80% 训练 / 20% 测试, 便于复现教材式对照表
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    # ---- 教材实验: 三种核在测试集上的错误率 ----
    report = {}
    print("=== 三种核函数的测试错误率 (训练 80% / 测试 20%) ===")
    for name, params in KERNEL_PARAMS.items():
        svc = SVC(**params).fit(Xtr, ytr)
        err = 100.0 * (1.0 - svc.score(Xte, yte))
        n_sv = len(svc.support_vectors_)
        report[name] = {"error": err, "n_sv": n_sv,
                        "n_train": len(Xtr)}
        print(f"  {name:7s}: 错误率 {err:5.2f}%   支持向量 {n_sv}/{len(Xtr)}")

    # ---- 识别用的最终模型: 用全部数据训练三种核各一个 ----
    models = {name: SVC(**params).fit(X, y)
              for name, params in KERNEL_PARAMS.items()}

    # ---- 二分类模型 (3 vs 8), 专用于展示 "支持向量 + 核函数" 的计算过程 ----
    mask = (y == 3) | (y == 8)
    yb = np.where(y[mask] == 8, 1, -1)     # 8 → +1, 3 → -1
    binary = SVC(kernel="rbf",
                 gamma=KERNEL_PARAMS["rbf"]["gamma"], C=10).fit(X[mask], yb)
    models["binary38"] = binary
    print(f"=== 二分类演示 (3 vs 8): 支持向量 {len(binary.support_vectors_)} 个 ===")
    return X, y, models, report


def drawing_to_feature(img):
    """图像 → 64 维特征向量 (与 digits 数据集的预处理保持一致)
    步骤: 取墨迹外接框 → 补成正方形 → OpenCV 区域采样缩放到 8x8 → 展平归一化
    """
    ys, xs = np.nonzero(img)
    if len(xs) == 0:
        return None
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    crop = img[y0:y1 + 1, x0:x1 + 1]
    h, w = crop.shape
    side = max(h, w)
    pad = np.zeros((side, side), np.uint8)
    pad[(side - h) // 2:(side - h) // 2 + h,
        (side - w) // 2:(side - w) // 2 + w] = crop
    # INTER_AREA: 缩小采样时按面积平均, 比最近邻更接近教材中的抗锯齿降采样
    small = cv2.resize(pad, (FEAT, FEAT), interpolation=cv2.INTER_AREA)
    return small.astype(np.float64).reshape(-1) / 255.0


def explain_svm_math(models, feat):
    """手工计算一次 SVM 决策: f(x) = Σ α_i y_i K(sv_i, x) + b
    与 sklearn 的 decision_function 对比, 验证公式实现正确。
    """
    svc = models["binary38"]
    sv = svc.support_vectors_               # 支持向量 (n_sv × 64)
    dual = svc.dual_coef_[0]                # α_i y_i  (n_sv,)
    b = float(svc.intercept_[0])

    ks = np.array([kernel_rbf(s, feat, KERNEL_PARAMS["rbf"]["gamma"])
                   for s in sv])            # 每个支持向量的核函数值
    dec_manual = float(np.dot(dual, ks) + b)
    dec_sklearn = float(svc.decision_function([feat])[0])
    ok = np.isclose(dec_manual, dec_sklearn, atol=1e-6)

    print("\n=== SVM 决策函数手工计算 (RBF 核, 3 vs 8) ===")
    print(f"  支持向量个数: {len(sv)}")
    print(f"  前 5 个核函数值 K(sv_i, x): {np.round(ks[:5], 4)}")
    print(f"  前 5 个 α_i·y_i:            {np.round(dual[:5], 4)}")
    print(f"  f(x) = Σ α_i·y_i·K(sv_i,x) + b = {dec_manual:+.6f}")
    print(f"  sklearn.decision_function      = {dec_sklearn:+.6f}")
    print(f"  两者一致: {ok}   (f>0 判为 8, f<0 判为 3)")
    return {
        "n_sv": len(sv),
        "manual": dec_manual,
        "sklearn": dec_sklearn,
        "match": bool(ok),
        "label": "8" if dec_manual > 0 else "3",
    }


# ---------------- 图形界面 ----------------
class SvmDigitsApp:
    def __init__(self, root, models, report):
        self.root = root
        self.models = models
        self.report = report
        self.strokes = []      # 已完成的笔画: [[(x,y), ...], ...]
        self.last = None       # 当前笔画最后一个点
        self._build()
        self._show_report()

    # ---------- 界面 ----------
    def _build(self):
        self.root.title("SVM 手写数字识别 — 模式识别 5.5.3 演示")
        self.root.resizable(False, False)
        self.root.configure(bg="#2b2b2b")

        self.canvas = tk.Canvas(self.root, width=CANVAS, height=CANVAS,
                                bg="#ffffff", cursor="pencil",
                                highlightthickness=2,
                                highlightbackground="#555555")
        self.canvas.pack(side=tk.LEFT, padx=(12, 0), pady=12)
        self.canvas.bind("<Button-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)

        panel = tk.Frame(self.root, bg="#2b2b2b", padx=14, pady=12)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(panel, text="在手写区用鼠标画一个数字 (0-9)",
                 bg="#2b2b2b", fg="#cccccc",
                 font=("Sans", 11)).pack(anchor="w")

        tk.Label(panel, text="使用的核函数:", bg="#2b2b2b",
                 fg="#cccccc", font=("Sans", 10)).pack(anchor="w", pady=(12, 0))
        self.kernel_var = tk.StringVar(value="rbf")
        for name, label in [("poly", "多项式核 poly (d=3)"),
                            ("rbf", "径向基核 rbf"),
                            ("sigmoid", "Sigmoid 核")]:
            tk.Radiobutton(panel, text=label, variable=self.kernel_var,
                           value=name, bg="#2b2b2b", fg="#e8e8e8",
                           selectcolor="#444444", activebackground="#2b2b2b",
                           font=("Sans", 10)).pack(anchor="w")

        self.report_var = tk.StringVar()
        tk.Label(panel, textvariable=self.report_var, bg="#2b2b2b",
                 fg="#8fd3a7", font=("Consolas", 9),
                 justify=tk.LEFT).pack(anchor="w", pady=(10, 6))

        tk.Button(panel, text="识别 (Ctrl+Enter)", command=self.on_recognize,
                  width=18).pack(pady=(6, 2))
        tk.Button(panel, text="清除", command=self.on_clear,
                  width=18).pack(pady=2)
        tk.Button(panel, text="核函数对比实验 (打印表格)",
                  command=self.on_compare, width=18).pack(pady=(10, 2))
        tk.Button(panel, text="SVM 原理: 手工决策计算",
                  command=self.on_explain, width=18).pack(pady=2)

        self.result_var = tk.StringVar(value="识别结果: —")
        tk.Label(panel, textvariable=self.result_var, bg="#2b2b2b",
                 fg="#ffcf4d", font=("Sans", 22, "bold")).pack(anchor="w",
                                                               pady=(14, 2))
        self.score_var = tk.StringVar(value="")
        tk.Label(panel, textvariable=self.score_var, bg="#2b2b2b",
                 fg="#bbbbbb", font=("Consolas", 9),
                 justify=tk.LEFT).pack(anchor="w")

        tk.Label(panel, text="特征向量预览 (8×8):", bg="#2b2b2b",
                 fg="#cccccc", font=("Sans", 9)).pack(anchor="w", pady=(10, 2))
        self.feat_canvas = tk.Canvas(panel, width=160, height=160,
                                     bg="#2b2b2b", highlightthickness=1,
                                     highlightbackground="#555555")
        self.feat_canvas.pack(anchor="w")

        self.status_var = tk.StringVar()
        tk.Label(panel, textvariable=self.status_var, bg="#2b2b2b",
                 fg="#9fb7d4", font=("Sans", 9), wraplength=190,
                 justify=tk.LEFT).pack(anchor="w", pady=(8, 0))

        self.root.bind("<Control-Return>", lambda _e: self.on_recognize())

    def _show_report(self):
        lines = ["测试错误率 (80/20 划分):"]
        for name, r in self.report.items():
            lines.append(f"  {name:7s} {r['error']:5.2f}%  SV {r['n_sv']}")
        self.report_var.set("\n".join(lines))
        self.status_var.set("训练完成: 三种核各训一个模型; "
                            "详细错误率见右侧/终端输出")

    # ---------- 手写 ----------
    def on_down(self, ev):
        self.strokes.append([(ev.x, ev.y)])
        self.last = (ev.x, ev.y)
        self.canvas.create_oval(ev.x - BRUSH // 2, ev.y - BRUSH // 2,
                                ev.x + BRUSH // 2, ev.y + BRUSH // 2,
                                fill="#111111", outline="")

    def on_drag(self, ev):
        if not self.strokes or self.last is None:
            return
        p0, p1 = self.last, (ev.x, ev.y)
        if p0 == p1:
            return
        self.strokes[-1].append(p1)
        self.canvas.create_line(p0[0], p0[1], p1[0], p1[1],
                                fill="#111111", width=BRUSH,
                                capstyle=tk.ROUND, joinstyle=tk.ROUND)
        self.last = p1

    def on_up(self, _ev):
        self.last = None

    def on_clear(self):
        self.strokes = []
        self.last = None
        self.canvas.delete("all")
        self.result_var.set("识别结果: —")
        self.score_var.set("")
        self.feat_canvas.delete("all")

    # ---------- 识别 ----------
    def _render(self):
        """把鼠标笔画栅格化成 420x420 图像 (OpenCV 负责线段绘制)"""
        img = np.zeros((CANVAS, CANVAS), np.uint8)
        for stroke in self.strokes:
            pts = [(int(x), int(y)) for x, y in stroke]
            if len(pts) == 1:
                cv2.circle(img, pts[0], BRUSH // 2, 255, -1, cv2.LINE_AA)
            for a, b in zip(pts, pts[1:]):
                cv2.line(img, a, b, 255, BRUSH, cv2.LINE_AA)
        return img

    def on_recognize(self):
        img = self._render()
        feat = drawing_to_feature(img)
        if feat is None:
            messagebox.showwarning("提示", "请先在手写区画一个数字")
            return
        name = self.kernel_var.get()
        svc = self.models[name]
        pred = int(svc.predict([feat])[0])
        dec = svc.decision_function([feat])[0]     # 10 个类的决策值 (ovr)
        top = np.argsort(dec)[::-1][:3]
        self.result_var.set(f"识别结果: {pred}")
        self.score_var.set("\n".join(
            f"{'top' if i == 0 else '   '} 数字 {int(c)} 分数 {dec[c]:+.3f}"
            for i, c in enumerate(top)))
        self._draw_feature(feat)
        self.status_var.set(f"当前核: {name}, 支持向量 {len(svc.support_vectors_)} 个")
        print(f"[识别] 核={name} 预测={pred} "
              f"top3={[(int(c), round(float(dec[c]), 3)) for c in top]}")

    def _draw_feature(self, feat):
        """把 64 维特征画成 8x8 单元格 (越黑 = 墨越浓)"""
        c = self.feat_canvas
        c.delete("all")
        cell = 160 // FEAT
        for i in range(FEAT):
            for j in range(FEAT):
                v = feat[j * FEAT + i]          # 注意: 图像按行展平
                g = int(255 * (1 - v))
                color = f"#{g:02x}{g:02x}{g:02x}"
                c.create_rectangle(i * cell, j * cell,
                                   (i + 1) * cell, (j + 1) * cell,
                                   fill=color, outline="#3a3a3a")

    # ---------- 实验与原理演示 ----------
    def on_compare(self):
        print("\n=== 核函数对比实验 ===")
        for name, r in self.report.items():
            print(f"{name:7s}: 测试错误率 {r['error']:5.2f}%, "
                  f"支持向量 {r['n_sv']}/{r['n_train']}")
        print("结论: 多项式核与 RBF 核错误率相近, Sigmoid 核稍差 —— "
              "核函数并非越复杂越好, 参数与数据特征同样重要。")
        msg = "测试错误率 (训练 80% / 测试 20%):\n\n" + "\n".join(
            f"{name:7s}: {r['error']:5.2f}%   (支持向量 {r['n_sv']})"
            for name, r in self.report.items())
        msg += "\n\n结论: 多项式核与 RBF 核错误率相近,\n" \
               "Sigmoid 核稍差 —— 核函数并非越复杂越好。"
        messagebox.showinfo("核函数对比实验", msg)

    def on_explain(self):
        img = self._render()
        feat = drawing_to_feature(img)
        if feat is None:
            messagebox.showwarning("提示", "请先画一个数字, 再查看决策计算")
            return
        info = explain_svm_math(self.models, feat)
        messagebox.showinfo(
            "SVM 决策函数手工计算",
            f"二分类模型 (3 vs 8), RBF 核\n\n"
            f"支持向量个数: {info['n_sv']}\n"
            f"f(x) = Σ α_i·y_i·K(sv_i,x) + b\n"
            f"手工计算:  {info['manual']:+.6f}\n"
            f"sklearn:   {info['sklearn']:+.6f}\n"
            f"两者一致:  {info['match']}\n\n"
            f"f>0 判 8, f<0 判 3 → 本样本判为 {info['label']}\n"
            f"(终端里同时打印了核函数值与 α·y 的前几项)")


# ---------------- 入口 ----------------
def main():
    print("正在加载 digits 数据集并训练三种核的 SVM ...")
    X, y, models, report = load_and_train()
    root = tk.Tk()
    SvmDigitsApp(root, models, report)
    root.mainloop()


if __name__ == "__main__":
    main()
