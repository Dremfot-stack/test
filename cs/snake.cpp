#include <iostream>
#include <vector>
#include <thread>
#include <chrono>
using namespace std;

#define width 60
#define height 20
#define initLength 10
#define tick 10

static vector<int*> body = {};
static char direction = 'd';
static int apple[2] = {rand() % width,rand() % height};

void gotoxy(int x,int y) {
	printf("\033[%d;%dH",y,x);
	fflush(stdout);
}

void init() {
	for (int i = 0 ; i < initLength ; ++i) {
		int* head = new int[2];
		*head = 0;
		*(head+1) = 0;
		body.push_back(head);
	}
}

bool trial(vector<int*> list,int x,int y) {
	for (int i = 0 ; i < list.size() ; ++i) {
		if (list[i][0] == x && list[i][1] == y) {
			return true;
		}
	}
	return false;
}

void move() {
	int* head = new int[2];
	head[0] = body[0][0];
	head[1] = body[0][1];
	if (direction == 'u') {
		(*(head+1))--;
	} else if (direction == 'd') {
		(*(head+1))++;
	} else if (direction == 'l') {
		(*head)--;
	} else {
		(*head)++;
	}
	body.insert(body.begin(),head);
	body.pop_back();
}

void eat() {
	if (body[0][0] == apple[0] && body[0][1] == apple[1]) {
		int* plus = new int[2];
		plus[0] = apple[0];
		plus[1] = apple[1];
		body.push_back(plus);
		apple[0] = rand() % width;
		apple[1] = rand() % height;
	}
}

void ac() {
	int* head = body[0];
	if (head[0] < apple[0]) {
		direction = 'r';
	} else if (head[0] > apple[0]) {
		direction = 'l';
	} else if (head[1] > apple[1]) {
		direction = 'u';
	} else {
		direction = 'd';
	}
}

void draw() {
	gotoxy(0,0);
	for (int y = 0 ; y < height ; ++y) {
		for (int x = 0 ; x < width ; ++x) {
			int* element = new int[2];
			if (trial(body,x,y)) {
				cout << 'O';
			} else if (x == apple[0] && y == apple[1]) {
			       	cout << '@';
			} else {
				cout << ' ';
			}
		}
		cout << "|\n";
	}
	for (int x = 0 ; x < width ; ++x) {
		cout << '-';
	}
	cout << "+\n";
	cout << body[0][0] << ' ' << body[0][1] << endl;
}

int main() {
	cout << "\033[?25l]";
	init();
	system("clear");
	while (1) {
		ac();
		this_thread::sleep_for(chrono::milliseconds(1000 / tick));
		eat();
		move();
		draw();
	}
	return 0;
}
