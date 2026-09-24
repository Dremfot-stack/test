#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#define width 100
#define height 25

void gotoxy(int x, int y) {
	printf("\033[%d;%dH", y, x);
	fflush(stdout);
}

int randint()
{
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dis(0,1);

    return dis(gen);
}

void generate(std::vector<std::vector<int>>& map) {
	for (int i = 0;i < height;++i) {
		std::vector<int> temp;
		for (int j = 0;j < width;++j) {
			temp.push_back(rand() % 2);
		}
		map.push_back(temp);
	}
}

int get(std::vector<std::vector<int>>& map,int x,int y) {
	int sum = 0;
	for (int i = -1;i <= 1;++i) {
		for (int j = -1;j <=1;++j) {
			if (i + j == 0 || i == j) continue;
			if ((0 <= y+i) && (y+i < height) && (0 <= x+j) && (x+j < width)) {
				sum += map[y+i][x+j];
			}
		}
	}
	return sum;
}

void draw(std::vector<std::vector<int>>& map);

bool clean(std::vector<std::vector<int>>& map) {
	draw(map);
	for (int y = 0;y < height;++y) {
		for (int x = 0;x < width;++x) {
			int sum = get(map,x,y);
			if (sum <= 1) {
				map[y][x] = 0;
				return true;
			}
		}
	}
	return false;
}

char gec(std::vector<std::vector<int>>& map,int x,int y) {
	int sum = get(map,x,y);
	if (sum == 0 || map[y][x] == 0) {
		return ' ';
	}
	if (x == 0 || x == width-1 || y == 0 || y == height-1) {
		return '*';
	}
	if (sum == 1) {
		return '*';
	} else if (sum == 2) {
		if (map[y-1][x]) {
			if (map[y+1][x]) return '|';
			if (map[y][x-1]) return '/';
			if (map[y][x+1]) return '\\';
		} else if (map[y+1][x]) {
			if (map[y][x-1]) return '\\';
			if (map[y][x+1]) return '/';
		} else {
			return '-';
		}
	} else {
		return '+';
	}
	return ' ';
}

void draw(std::vector<std::vector<int>>& map) {
	gotoxy(0,0);
	for (int x = 0;x <= width+1;++x) {
		std::cout << '#';
	}
	std::cout << '\n';
	for (int y = 0;y < height;++y) {
		std::cout << '#';
		for (int x = 0;x < width;++x) {
			std::cout << gec(map,x,y);
		}
		std::cout << "#\n";
	}
	for (int x = 0;x <= width+1;++x) {
		std::cout << '#';
	}
	std::cout << '\n';
}

int main() {
	std::vector<std::vector<int>> map;
	generate(map);
	while (clean(map));
	return 0;
}

