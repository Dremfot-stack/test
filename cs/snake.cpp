#include <iostream>
#include <vector>
using namespace std;

#define width 60
#define height 20
#define initLength 10

static vector<int*> body = {};
static char direction = 'u';

void gotoxy(int x,int y) {
	printf("\033[%d;%dH",y,x);
	fflush(stdout);
}

void init() {
	for (int i = 0 ; i < initLength ; ++i) {
		int head[2] = {0,0};
		body.push_back(head);
	}
}

void move() {
	int head[2];
	head[0] = body[0][0];
	head[1] = body[0][1];
	if (direction == 'u') {
		--head[1];
	} else if (direction == 'd') {
		++head[1];
	} else if (direction == 'l') {
		--head[0];
	} else {
		++head[1];
	}
	body.insert(body.begin(),head);
	body.pop_back();
}

void draw() {
	system("clear");
	for (int y = 0 ; y < height ; ++y) {
		for (int x = 0 ; x < width ; ++x) {
			for (int i = 0 ; i < body.size() ; ++i) {
				if ((body[i][0] == x) && (body[i][1] == y)) {
					cout << 'O';
				} else {
					cout << ' ';
				}
			}
		}
		cout << '|'  << endl;
	}
	for (int x = 0 ; x <= width ; ++x) {
		cout << '-';
	}
	cout << endl;
}

int main() {
	init();
	while (1) {
		move();
		draw();
	}
	return 0;
}
