// Fibonacci sequence in C for 8-bit CPU Emulator
void main() {
    int a = 0;
    int b = 1;
    int n = 7;
    int t = 0;

    while (n > 0) {
        print_num(a);
        putchar(32); // Space ' '
        t = a + b;
        a = b;
        b = t;
        n = n - 1;
    }
    putchar(10); // Newline '\n'
}
