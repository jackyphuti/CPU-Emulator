// Array summation in Mini-C
int numbers[5];

void main() {
    numbers[0] = 10;
    numbers[1] = 20;
    numbers[2] = 30;
    numbers[3] = 40;
    numbers[4] = 50;

    int sum = 0;
    int i = 0;

    while (i < 5) {
        sum = sum + numbers[i];
        i = i + 1;
    }

    // Output result (150)
    print_num(sum);
    putchar(10);
}
