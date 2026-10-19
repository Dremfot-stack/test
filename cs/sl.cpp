#include <iostream>
#include <deque>
#include <vector>
#include <queue>
#include <thread>
#include <chrono>
#include <algorithm>
#include <cstdlib>
#include <ctime>
#include <string>
using namespace std;

// 贪吃蛇：默认「哈密顿环 + 捷径」，会蛇形铺满整个棋盘且不会撞死；
// 可用 --greedy 切回原来的评估函数（BFS 找苹果 + 追尾 + 空间评估）。
//
// 交互运行：  ./sl [--greedy]
// 批量测试：  ./sl --headless <局数> <种子> [greedy] [最大步数]
//   例：      ./sl --headless 10 1          # 哈密顿环跑 10 局
//             ./sl --headless 10 1 greedy   # 贪心评估跑 10 局

#define width 60
#define height 20
#define initLength 10
#define tick 100

static_assert(height % 2 == 0, "哈密顿环要求 height 为偶数");

struct Cell {
	int x, y;
};

static deque<Cell> body;      // 蛇身：body[0] 是蛇头，body.back() 是蛇尾
static char direction = 'd';  // 当前方向
static Cell apple;            // 苹果位置

// 哈密顿环：把整个棋盘串成一个环，蛇沿环前进就永远不会撞死
static int order[height][width];
static Cell cycleCell[width * height];
static int cycleN = 0;

enum Strategy { STRATEGY_HAM, STRATEGY_GREEDY };
static Strategy strategy = STRATEGY_HAM;

// ---------------- 基础判断 ----------------

bool isInside(int x,int y) {
	return 0 <= x && x < width && 0 <= y && y < height;
}

bool trial(int x,int y) {
	for (const Cell& c : body) {
		if (c.x == x && c.y == y) return true;
	}
	return false;
}

int cellId(int x,int y) {
	return y * width + x;
}

// 碰撞判断：蛇头下一步到 (x,y) 是否会撞墙或撞到自己
// grow：本步是否吃到苹果。吃到时尾巴不移动，尾巴也算障碍；
//       否则尾巴同时移开，允许蛇头进入原尾巴所在格。
bool collide(int x,int y,bool grow) {
	if (!isInside(x,y)) {
		return true;                        // 撞墙
	}
	int n = (int)body.size();
	int upto = grow ? n : n - 1;            // 不增长时排除即将移走的尾巴
	for (int i = 0 ; i < upto ; ++i) {
		if (body[i].x == x && body[i].y == y) {
			return true;                    // 撞到自己
		}
	}
	return false;
}

// 按当前方向计算下一格
Cell nextHead(char d) {
	Cell h = body.front();
	if (d == 'u') {
		h.y--;
	} else if (d == 'd') {
		h.y++;
	} else if (d == 'l') {
		h.x--;
	} else {
		h.x++;
	}
	return h;
}

// 方向字符转下标，顺序 u,d,l,r
int dirIndex(char d) {
	if (d == 'u') return 0;
	if (d == 'd') return 1;
	if (d == 'l') return 2;
	return 3;
}

// 由 a 指向 b 的方向（保证 b 与 a 相邻）
char dirTo(Cell a,Cell b) {
	if (b.y == a.y - 1) return 'u';
	if (b.y == a.y + 1) return 'd';
	if (b.x == a.x - 1) return 'l';
	return 'r';
}

// 尝试移动一步；发生碰撞则返回 false（游戏结束），否则返回 true
bool move(bool grow) {
	Cell h = nextHead(direction);
	if (collide(h.x,h.y,grow)) {
		return false;
	}
	body.push_front(h);
	if (!grow) {
		body.pop_back();                    // 没吃到就丢掉尾巴，长度不变
	}
	return true;
}

// 构造哈密顿环：
//   第 0 行从左到右；第 1..height-1 行在 x=1..width-1 之间蛇形往返；
//   最后沿第 0 列从下往上回到起点。要求 height 为偶数。
void buildCycle() {
	int n = 0;
	auto add = [&](int x,int y) {
		order[y][x] = n;
		cycleCell[n] = {x,y};
		++n;
	};

	for (int x = 0 ; x < width ; ++x) add(x,0);
	for (int y = 1 ; y < height ; ++y) {
		if (y % 2 == 1) {
			for (int x = width - 1 ; x >= 1 ; --x) add(x,y);
		} else {
			for (int x = 1 ; x <= width - 1 ; ++x) add(x,y);
		}
	}
	for (int y = height - 1 ; y >= 1 ; --y) add(0,y);

	cycleN = n;
}

// 重新开始一局
void reset() {
	body.clear();
	if (strategy == STRATEGY_HAM) {
		// 沿环的起点铺开，蛇头在 initLength-1 号格，朝环的前进方向
		for (int i = initLength - 1 ; i >= 0 ; --i) {
			body.push_back(cycleCell[i]);
		}
		direction = 'r';
	} else {
		direction = 'd';
		for (int i = 0 ; i < initLength ; ++i) {
			body.push_back({0,0});
		}
	}
	do {
		apple.x = rand() % width;
		apple.y = rand() % height;
	} while (trial(apple.x,apple.y));
}

// 吃苹果后重新生成，保证不落在蛇身上
void respawnApple() {
	if ((int)body.size() >= width * height) return;   // 已经铺满，没有空格了
	do {
		apple.x = rand() % width;
		apple.y = rand() % height;
	} while (trial(apple.x,apple.y));
}

// ---------------- 局面评估 ----------------

struct Reach {
	int area;   // 新蛇头能到达的空格数
	int food;   // 到苹果的最短距离，-1 表示到不了
	int tail;   // 到蛇尾的最短距离，-1 表示到不了
};

// 对新蛇身 nb 做一次 BFS，同时算出可达空间、到苹果/蛇尾的距离
Reach analyze(const deque<Cell>& nb) {
	Reach r = {0,-1,-1};

	vector<char> blocked(width * height,0);
	// 尾巴下一步会移开，所以视为可通行
	for (int i = 0 ; i + 1 < (int)nb.size() ; ++i) {
		blocked[cellId(nb[i].x,nb[i].y)] = 1;
	}

	vector<int> dist(width * height,-1);
	deque<Cell> q;
	int sid = cellId(nb.front().x,nb.front().y);
	dist[sid] = 0;
	q.push_back(nb.front());

	static const int dx[4] = {0,1,0,-1};
	static const int dy[4] = {-1,0,1,0};

	while (!q.empty()) {
		Cell c = q.front();
		q.pop_front();
		int d = dist[cellId(c.x,c.y)];
		for (int k = 0 ; k < 4 ; ++k) {
			int nx = c.x + dx[k];
			int ny = c.y + dy[k];
			if (!isInside(nx,ny)) continue;
			int id = cellId(nx,ny);
			if (dist[id] != -1 || blocked[id]) continue;
			dist[id] = d + 1;
			++r.area;
			q.push_back({nx,ny});
		}
	}

	r.food = dist[cellId(apple.x,apple.y)];
	r.tail = dist[cellId(nb.back().x,nb.back().y)];
	return r;
}

// 模拟走出一步后的蛇身
deque<Cell> simulate(Cell h,bool grow) {
	deque<Cell> nb;
	nb.push_back(h);
	int keep = grow ? (int)body.size() : (int)body.size() - 1;
	for (int i = 0 ; i < keep ; ++i) {
		nb.push_back(body[i]);
	}
	return nb;
}

// ---------------- 控制函数 ----------------

// 评估四个方向并选一个（贪心评估版）：
//   1. 优先选「安全且能吃到苹果」的方向（BFS 最短路，越短越好）
//   2. 吃不到就追自己的尾巴（会自然盘绕，把身体收拢、给后面留空间）
//   3. 连安全走法都没有时，选可达空间最大的方向尽量多活几步
char chooseGreedy() {
	bool grow = (body.front().x == apple.x && body.front().y == apple.y);

	static const char dirs[4] = {'u','d','l','r'};
	static const int dx[4] = {0,0,-1,1};
	static const int dy[4] = {-1,1,0,0};

	int cur = 0;
	if (direction == 'u') cur = 0;
	else if (direction == 'd') cur = 1;
	else if (direction == 'l') cur = 2;
	else cur = 3;

	bool hasBest = false;
	char bestDir = direction;
	int bestRank = -1;       // 2=安全且吃得到，1=安全但吃不到，0=不安全
	int bestFood = 0;
	int bestTail = 0;
	int bestArea = 0;
	bool bestStraight = false;

	for (int k = 0 ; k < 4 ; ++k) {
		if ((k ^ 1) == cur) continue;       // 不能 180 度掉头

		Cell h = {body.front().x + dx[k],body.front().y + dy[k]};
		if (collide(h.x,h.y,grow)) continue;

		deque<Cell> nb = simulate(h,grow);
		Reach r = analyze(nb);

		// 安全：还能追到自己的尾巴（追尾是永远不会困死自己的走法）
		bool safe = (r.tail >= 0);
		int rank = safe ? (r.food >= 0 ? 2 : 1) : 0;
		bool straight = (dirs[k] == direction);

		bool better;
		if (!hasBest) {
			better = true;
		} else if (rank != bestRank) {
			better = rank > bestRank;
		} else if (rank == 2) {
			better = (r.food < bestFood)
			      || (r.food == bestFood && r.area > bestArea)
			      || (r.food == bestFood && r.area == bestArea && straight && !bestStraight);
		} else if (rank == 1) {
			int t1 = (r.tail < 0 ? (1 << 30) : r.tail);
			int t2 = (bestTail < 0 ? (1 << 30) : bestTail);
			better = (t1 < t2)
			      || (t1 == t2 && r.area > bestArea)
			      || (t1 == t2 && r.area == bestArea && straight && !bestStraight);
		} else {
			better = (r.area > bestArea)
			      || (r.area == bestArea && straight && !bestStraight);
		}

		if (better) {
			hasBest = true;
			bestDir = dirs[k];
			bestRank = rank;
			bestFood = r.food;
			bestTail = r.tail;
			bestArea = r.area;
			bestStraight = straight;
		}
	}

	return hasBest ? bestDir : direction;
}

// ---------------- 哈密顿环控制 ----------------

// 沿哈密顿环走，并在安全时抄近路：直接跳到环上更靠前的相邻格，
// 一次跳过一大段，从而快速接近苹果。跳过的整段必须是空的。
char chooseHamiltonian() {
	bool grow = (body.front().x == apple.x && body.front().y == apple.y);
	int h = order[body.front().y][body.front().x];
	int target = order[apple.y][apple.x];
	int dFood = (target - h + cycleN) % cycleN;

	static const char dirs[4] = {'u','d','l','r'};
	static const int dx[4] = {0,0,-1,1};
	static const int dy[4] = {-1,1,0,0};

	int bestJump = 0;
	char bestDir = direction;

	// 一次性标记身体（尾巴下一步会移开，所以不标记），
	// 后面判断捷径是否畅通时就是 O(1)，不用每格都扫一遍蛇身
	vector<char> occ(width * height,0);
	int upto = grow ? (int)body.size() : (int)body.size() - 1;
	for (int i = 0 ; i < upto ; ++i) {
		occ[cellId(body[i].x,body[i].y)] = 1;
	}

	for (int k = 0 ; k < 4 ; ++k) {
		if ((k ^ 1) == dirIndex(direction)) continue;   // 不能 180 度掉头

		int nx = body.front().x + dx[k];
		int ny = body.front().y + dy[k];
		if (!isInside(nx,ny)) continue;

		int j = order[ny][nx];
		int jump = (j - h + cycleN) % cycleN;
		if (jump == 0 || jump > dFood) continue;        // 不能跳过苹果
		if (occ[cellId(nx,ny)]) continue;               // 目标格是身体

		// 跳过的环上区段必须没有身体，否则会把自己切断
		bool clear = true;
		for (int s = 1 ; s < jump ; ++s) {
			Cell c = cycleCell[(h + s) % cycleN];
			if (occ[cellId(c.x,c.y)]) {
				clear = false;
				break;
			}
		}
		if (!clear) continue;

		if (jump > bestJump) {
			bestJump = jump;
			bestDir = dirs[k];
		}
	}

	if (bestJump == 0) {
		// 没有捷径，沿环走下一格
		Cell c = cycleCell[(h + 1) % cycleN];
		bestDir = dirTo(body.front(),c);
		if (collide(c.x,c.y,grow)) {
			// 兜底：环被身体挡住时，任选一个不碰撞的方向
			for (int k = 0 ; k < 4 ; ++k) {
				int nx = body.front().x + dx[k];
				int ny = body.front().y + dy[k];
				if (isInside(nx,ny) && !collide(nx,ny,grow)) {
					bestDir = dirs[k];
					break;
				}
			}
		}
	}

	return bestDir;
}

// 统一入口：默认哈密顿环，可用 --greedy 切回贪心评估
char chooseDirection() {
	return strategy == STRATEGY_HAM ? chooseHamiltonian() : chooseGreedy();
}

// ---------------- 渲染 ----------------

void gotoxy(int x,int y) {
	printf("\033[%d;%dH",y,x);
	fflush(stdout);
}

char getimg(int x,int y) {
	int tag = 0;
	for (int i = 0 ; i < (int)body.size() ; ++i) {
		if ((body[i].x == x) && (body[i].y == y)) {
			tag = i;
		}
	}
	if (tag == 0) {
		return 'X';
	} else if (tag == (int)body.size() - 1) {
		if (body[tag-1].x == body[tag].x) {
			return '|';
		} else {
			return '-';
		}
	} else {
		if (body[tag-1].x == body[tag+1].x) return '|';
		int k = - (body[tag-1].y - body[tag+1].y) / (body[tag-1].x - body[tag+1].x);
		if (k == -1) {
			return '\\';
		} else if (k == 1) {
			return '/';
		} else {
			return '-';
		}
	}
}

void draw() {
	gotoxy(0,0);
	for (int x = 0 ; x <= width ; ++x) {
		cout << '#';
	}
	cout << "#\n";
	for (int y = 0 ; y < height ; ++y) {
		cout << '#';
		for (int x = 0 ; x < width ; ++x) {
			if (trial(x,y)) {
				cout << getimg(x,y);
			} else if (x == apple.x && y == apple.y) {
				cout << '@';
			} else {
				cout << ' ';
			}
		}
		cout << "#\n";
	}
	for (int x = 0 ; x <= width ; ++x) {
		cout << '#';
	}
	cout << "#\n";
}

// 调试用：不带光标控制地打印一帧
void printBoard() {
	for (int y = 0 ; y < height ; ++y) {
		for (int x = 0 ; x < width ; ++x) {
			if (trial(x,y)) {
				cout << getimg(x,y);
			} else if (x == apple.x && y == apple.y) {
				cout << '@';
			} else {
				cout << ' ';
			}
		}
		cout << '\n';
	}
	cout << "length=" << body.size() << " apple=(" << apple.x << "," << apple.y << ")\n";
}

// ---------------- 主程序 ----------------

// 无终端批量跑，用来验证不同种子下的分数
int playHeadless(int episodes,unsigned seed,int maxSteps) {
	long long total = 0;
	int best = 0;
	for (int e = 0 ; e < episodes ; ++e) {
		srand(seed + e);
		reset();
		int score = 0;
		int steps = 0;
		while (steps < maxSteps) {
			direction = chooseDirection();
			bool grow = (body.front().x == apple.x && body.front().y == apple.y);
			if (!move(grow)) break;
			if (grow) {
				++score;
				if ((int)body.size() >= width * height) break;   // 铺满，胜利
				respawnApple();
			}
			++steps;
			if (episodes == 1 && steps % 100000 == 0) {
				cout << "  ... steps=" << steps << " score=" << score
				     << " length=" << body.size() << endl;
			}
		}
		total += score;
		if (score > best) best = score;
		cout << "episode " << e << ": score=" << score
		     << " length=" << body.size() << " steps=" << steps << endl;
		if (episodes == 1) {
			printBoard();
		}
	}
	cout << "平均分=" << (double)total / episodes << "  最高分=" << best << endl;
	return 0;
}

int main(int argc,char** argv) {
	if (argc > 1 && string(argv[1]) == "--headless") {
		int episodes = (argc > 2 ? atoi(argv[2]) : 20);
		unsigned seed = (argc > 3 ? (unsigned)atoi(argv[3]) : 1);
		if (argc > 4 && string(argv[4]) == "greedy") {
			strategy = STRATEGY_GREEDY;
		}
		int maxSteps = (argc > 5 ? atoi(argv[5]) : 200000);
		buildCycle();
		return playHeadless(episodes,seed,maxSteps);
	}

	for (int i = 1 ; i < argc ; ++i) {
		if (string(argv[i]) == "--greedy") {
			strategy = STRATEGY_GREEDY;
		}
	}

	srand((unsigned)time(nullptr));
	buildCycle();
	cout << "\033[?25l";
	reset();
	cout << "\033[2J\033[H";

	int score = 0;
	while (1) {
		direction = chooseDirection();
		//this_thread::sleep_for(chrono::milliseconds(1000 / tick));
		bool grow = (body.front().x == apple.x && body.front().y == apple.y);
		if (!move(grow)) {
			break;
		}
		if (grow) {
			++score;
			if ((int)body.size() >= width * height) break;   // 铺满，胜利
			respawnApple();
		}
		draw();
	}

	gotoxy(0,height + 2);
	cout << "\033[?25h";
	if ((int)body.size() >= width * height) {
		cout << "Perfect! 铺满棋盘！长度=" << body.size()
		     << "  得分=" << score << endl;
	} else {
		cout << "Game Over! 长度=" << body.size()
		     << "  得分=" << score << endl;
	}
	return 0;
}
