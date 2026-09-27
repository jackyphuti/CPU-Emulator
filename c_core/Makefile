CC ?= gcc
CFLAGS ?= -Wall -Wextra -O3 -std=c99 -pedantic
LDFLAGS ?=

SRC = cpu8.c
OBJS = cpu8.o

TARGET_CLI = cpu8_cli
TARGET_TEST = test_cpu8
TARGET_LIB = libcpu8.so

.PHONY: all test bench clean shared

all: $(TARGET_CLI) $(TARGET_TEST) shared

cpu8.o: cpu8.c cpu8.h
	$(CC) $(CFLAGS) -fPIC -c cpu8.c -o cpu8.o

$(TARGET_CLI): cpu8.o main.c
	$(CC) $(CFLAGS) cpu8.o main.c -o $(TARGET_CLI) $(LDFLAGS)

$(TARGET_TEST): cpu8.o test_cpu8.c
	$(CC) $(CFLAGS) cpu8.o test_cpu8.c -o $(TARGET_TEST) $(LDFLAGS)

shared: cpu8.o
	$(CC) -shared cpu8.o -o $(TARGET_LIB)

test: $(TARGET_TEST)
	./$(TARGET_TEST)

bench: $(TARGET_CLI)
	./$(TARGET_CLI) --bench

clean:
	rm -f *.o $(TARGET_CLI) $(TARGET_TEST) $(TARGET_LIB)
