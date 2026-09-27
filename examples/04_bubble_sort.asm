; =====================================================================
; Example 4: In-Place Bubble Sort on RAM Array
; Sorts an array of 5 unsigned numbers in RAM [0x80..0x84]
; Initial unsorted data: 55, 12, 89, 4, 33
; Expected sorted:       4, 12, 33, 55, 89
; Prints each sorted number to MMIO console.
; =====================================================================

.EQU ARR_BASE   0x80
.EQU ARR_LEN    5
.EQU VAR_OUTER  0x90
.EQU VAR_PTR    0x91
.EQU VAR_INNER  0x92
.EQU VAR_VAL1   0x93
.EQU VAR_VAL2   0x94

.ORG 0x00

start:
    ; Populate initial unsorted array in RAM
    LDA #55
    STA 0x80
    LDA #12
    STA 0x81
    LDA #89
    STA 0x82
    LDA #4
    STA 0x83
    LDA #33
    STA 0x84

    ; Outer loop: 4 passes
    LDA #4
    STA VAR_OUTER

outer_loop:
    LDA #ARR_BASE
    STA VAR_PTR          ; ptr = 0x80
    LDA #4
    STA VAR_INNER        ; inner comparisons = 4

inner_loop:
    ; Read val1 = RAM[ptr]
    LDB [VAR_PTR]
    LDA [B]
    STA VAR_VAL1

    ; Read val2 = RAM[ptr + 1]
    INC B
    LDA [B]
    STA VAR_VAL2

    ; Compare val1 with val2
    LDA [VAR_VAL1]
    LDB [VAR_VAL2]
    CMP B
    JC no_swap           ; if val1 < val2, already sorted
    JZ no_swap           ; if val1 == val2, already sorted

    ; Swap elements in RAM: RAM[ptr] = val2, RAM[ptr+1] = val1
    LDB [VAR_PTR]
    LDA [VAR_VAL2]
    STA [B]              ; RAM[ptr] = val2
    INC B
    LDA [VAR_VAL1]
    STA [B]              ; RAM[ptr+1] = val1

no_swap:
    ; Advance ptr: ptr = ptr + 1
    LDA [VAR_PTR]
    INC A
    STA VAR_PTR

    ; Decrement inner counter
    LDA [VAR_INNER]
    DEC A
    STA VAR_INNER
    JNZ inner_loop

    ; Decrement outer counter
    LDA [VAR_OUTER]
    DEC A
    STA VAR_OUTER
    JNZ outer_loop

    ; Print sorted array to MMIO
    LDB #ARR_BASE
    LDA #5
    STA VAR_INNER

print_loop:
    LDA [B]
    STA 0xF1             ; MMIO decimal number output
    LDA #32              ; space
    STA 0xF0
    INC B
    LDA [VAR_INNER]
    DEC A
    STA VAR_INNER
    JNZ print_loop

    LDA #10              ; newline
    STA 0xF0
    HLT
