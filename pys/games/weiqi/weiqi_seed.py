#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
weiqi_seed — 用 GNU Go 自战棋谱预训练 weiqi_ai 的知识库

原理: 让 GNU Go (GTP 协议) 与自己对弈, 每局结束后用
weiqi_ai.extract_moves 提取落子棋形, 按胜负更新棋形胜率先验
(监督学习, 类似 AlphaGo 的第一阶段)。棋谱同时存为 SGF。

用法: python3 weiqi_seed.py [9路局数] [13路局数] [19路局数]
默认: 400 / 60 / 20 局
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weiqi_ai

COLS = "ABCDEFGHJKLMNOPQRST"
KOMI = 7.5


# ---------------- GTP 协议封装 ----------------

def gtp_engine(level):
    return subprocess.Popen(
        ["gnugo", "--mode", "gtp", "--chinese-rules",
         "--level", str(level)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        text=True, bufsize=1)


def gtp_cmd(p, cmd):
    """发送 GTP 命令, 返回状态行 "= result" 或 "? error"。
    GNU Go 把结果直接放在状态行, 例如 "= D4"、 "= B+3.5"。"""
    p.stdin.write(cmd + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if line == "":
            raise RuntimeError("GTP 引擎意外退出")
        line = line.rstrip("\n")
        if line == "":
            continue
        return line


def parse_move(s, size):
    """GTP 走子 → (x,y) 或 None(停一手) 或 'resign'"""
    s = s.strip().upper()
    if s == "PASS":
        return None
    if s.startswith("RESIGN"):
        return "resign"
    col = COLS.index(s[0])
    row = int(s[1:])
    return (col, size - row)


def play_game(p, size):
    """让 GNU Go 自战一局, 返回 (记录, 胜方 1/2/0)"""
    gtp_cmd(p, f"boardsize {size}")
    gtp_cmd(p, f"komi {KOMI}")
    gtp_cmd(p, "clear_board")
    record = []
    winner = 0
    for step in range(size * size + 20):
        color = "black" if step % 2 == 0 else "white"
        c = 1 if color == "black" else 2
        line = gtp_cmd(p, f"genmove {color}")
        res = line[1:].strip() if line.startswith("=") else None
        mv = parse_move(res, size) if res else None
        if mv == "resign":
            winner = 3 - c
            break
        if mv is None:
            record.append((None, None, c))
        else:
            record.append((mv[0], mv[1], c))
        # 双方连续停一手 → 终局
        if len(record) >= 2 and record[-1][0] is None and record[-2][0] is None:
            line2 = gtp_cmd(p, "final_score")
            val = line2[1:].strip() if line2.startswith("=") else ""
            if val.startswith("B+"):
                winner = 1
            elif val.startswith("W+"):
                winner = 2
            else:
                winner = 0
            break
    return record, winner


def save_sgf(size, record, winner, path):
    lines = [f"(;FF[4]GM[1]SZ[{size}]KM[{KOMI}]PB[GNU Go]PW[GNU Go]"]
    for x, y, c in record:
        col = COLS[x] if x is not None else ""
        row = size - y if y is not None else ""
        lines.append(f"{'B' if c == 1 else 'W'}[{col}{row}]")
    res = {1: "B+R", 2: "W+R"}.get(winner, "0")
    lines.append(f"RE[{res}]")
    lines.append(")")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(lines))


# ---------------- 主流程 ----------------

def main():
    counts = {
        9: int(sys.argv[1]) if len(sys.argv) > 1 else 400,
        13: int(sys.argv[2]) if len(sys.argv) > 2 else 60,
        19: int(sys.argv[3]) if len(sys.argv) > 3 else 20,
    }
    levels = {9: 5, 13: 5, 19: 4}
    kb = weiqi_ai.Knowledge()
    os.makedirs(weiqi_ai.GAMES_DIR, exist_ok=True)
    total = 0
    for size in (9, 13, 19):
        count = counts[size]
        if count <= 0:
            continue
        print(f"=== 开始 {size} 路 × {count} 局 (GNU Go level {levels[size]}) ===",
              flush=True)
        p = gtp_engine(levels[size])
        done = 0
        t0 = time.time()
        for i in range(count):
            try:
                record, winner = play_game(p, size)
            except Exception as e:
                print(f"  [{i + 1}/{count}] 出错: {e}, 重启引擎", flush=True)
                try:
                    p.terminate()
                except OSError:
                    pass
                p = gtp_engine(levels[size])
                continue
            if winner:
                feats = weiqi_ai.extract_moves(size, record)
                kb.update(feats, winner)
                name = time.strftime("%Y%m%d-%H%M%S") + f"-gnugo-{size}x{size}.sgf"
                save_sgf(size, record, winner,
                         os.path.join(weiqi_ai.GAMES_DIR, name))
            done += 1
            total += 1
            if done % 10 == 0:
                rate = done / max(time.time() - t0, 0.1)
                print(f"  {size}路 {done}/{count} 局 "
                      f"({rate:.1f} 局/分), 累计棋形 {len(kb)}, "
                      f"胜方 {1 if winner == 1 else 2 if winner == 2 else '-'}",
                      flush=True)
        try:
            p.terminate()
        except OSError:
            pass
        kb.save()
        print(f"=== {size} 路完成, 知识库 {len(kb)} 种棋形 (已保存) ===",
              flush=True)
    kb.save()
    print(f"全部完成: 共 {total} 局, 知识库 {len(kb)} 种棋形", flush=True)


if __name__ == "__main__":
    main()
