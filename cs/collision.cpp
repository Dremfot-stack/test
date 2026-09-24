#include <iostream>
#include <vector>
#include <cstdlib>
#include <cmath>
#include <thread>
#include <chrono>

#define initer 10
#define width 160
#define height 40
#define tick 10

class Ball {
public:
	int x,y,dx,dy;
	friend void operator*(Ball& a,Ball& b) {
		a.dx ^= b.dx;
		b.dx ^= a.dx;
		a.dx ^= b.dx;
		a.dy ^= b.dy;
		b.dy ^= a.dy;
		a.dy ^= b.dy;
	}
	bool operator&(const Ball& a) const {
		if (abs(a.x - this->x) <= 1 && abs(a.y - this->y) <= 1) {
			return true;
		} else {
			return false;
		}
	}
	void move() {
		this->x += this->dx;
		this->y += this->dy;
		if (this->x >= width - 1 || this->x <= 0) {
			this->dx = -this->dx;
		}
		if (this->y >= height - 1 || this->y <= 0) {
			this->dy = -this->dy;
		}
	}
	Ball(int x,int y,int dx,int dy) : x(x),y(y),dx(dx),dy(dy) {};
	~Ball() {};
};

void update(std::vector<Ball>& arr) {
	for (int i = 0;i < arr.size();++i) {
		for (int j = i + 1;j < arr.size();++j) {
			if (arr[i] & arr[j]) {
				arr[i] * arr[j];
			}
		}
	}
	for (int i = 0;i < arr.size();++i) {
		arr[i].move();
	}
}

void draw(std::vector<Ball>& arr) {
	system("clear");
	for (int y = 0;y < height;++y) {
		for (int x = 0;x < width;++x) {
			bool flag = false;
			for (int i = 0;i < arr.size();++i) {
				if (arr[i].x == x && arr[i].y == y) {
					std::cout << '@';
					flag = true;
					break;
				}
			}
			if (flag == false) {
				std::cout << ' ';
			}
			
		}
		std::cout << '|' << std::endl;
	}
	for (int x = 0;x < width;++x) {
		std::cout << '-';
	}
	std::cout << '+' << std::endl;
}


int main() {
	std::vector<Ball> arr;
	for (int i = 0;i < initer;++i) {
		arr.push_back(Ball(rand() % width,rand() % height,rand() % 3 - 2,rand() % 3 - 2));
	}
	while (true) {
		std::this_thread::sleep_for(std::chrono::milliseconds(1000 / tick));
		arr.push_back(Ball(rand() % width,rand() % height,rand() % 3 - 2,rand() % 3 - 2));
		update(arr);
		draw(arr);
	}
	return 0;
}
