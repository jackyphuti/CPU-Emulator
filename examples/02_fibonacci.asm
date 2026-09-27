; =====================================================================
; Example 2: Fibonacci Sequence Generator
; Computes Fibonacci numbers up to 8-bit limit (1, 1, 2, 3, 5, 8, 13, 21, ...)
; Prints each number separated by spaces to MMIO console.
; =====================================================================

.EQU RAM_A       0x60
.EQU RAM_B       0x61
.EQU RAM_COUNT   0x62

.ORG 0x00

start:
    ; Initialize a = 1, b = 1, count = 10
    LDA #1
    STA RAM_A
    STA RAM_B
    LDA #10
    STA RAM_COUNT

    ; Print initial '1 '
    LDA #1
    STA 0xF1
    LDA #32              ; space
    STA 0xF0

fib_loop:
    ; Print current 'b'
    LDA RAM_B
    STA 0xF1
    LDA #32
    STA 0xF0

    ; Compute next = a + b
    LDA RAM_A
    LDB RAM_B
    ADD B                ; A = a + b
    PUSH A               ; Save next value on stack

    ; a = b
    LDA RAM_B
    STA RAM_A

    ; b = next
    POP A
    STA RAM_B

    ; Decrement loop counter
    LDA RAM_COUNT
    DEC A
    STA RAM_COUNT
    JNZ fib_loop         ; Loop while count > 0

    ; Print newline and halt
    LDA #10
    STA 0xF0
    HLT
