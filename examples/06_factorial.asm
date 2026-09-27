; =====================================================================
; Example 6: Factorial Calculator with Nested Calls
; Computes 5! = 120
; Demonstrates stack usage, subroutines, and MMIO output.
; =====================================================================

.EQU N_VAL     0x80
.EQU RESULT    0x81
.EQU MUL_A     0x82
.EQU MUL_B     0x83
.EQU MUL_RES   0x84

.ORG 0x00

start:
    ; Calculate factorial of 5
    LDA #5
    STA N_VAL
    LDA #1
    STA RESULT

fact_loop:
    LDA [N_VAL]
    CMP #1
    JZ print_result      ; when N == 1, we are done

    ; Call multiply: RESULT = RESULT * N
    LDA [RESULT]
    STA MUL_A
    LDA [N_VAL]
    STA MUL_B
    CALL multiply
    LDA [MUL_RES]
    STA RESULT

    ; N = N - 1
    LDA [N_VAL]
    DEC A
    STA N_VAL
    JMP fact_loop

print_result:
    ; Print "5! = "
    LDA #'5'
    STA 0xF0
    LDA #'!'
    STA 0xF0
    LDA #' '
    STA 0xF0
    LDA #'='
    STA 0xF0
    LDA #' '
    STA 0xF0

    ; Print 120 to MMIO number port
    LDA [RESULT]
    STA 0xF1

    LDA #10              ; newline
    STA 0xF0
    HLT

; Subroutine multiply: MUL_RES = MUL_A * MUL_B
multiply:
    LDA #0
    STA MUL_RES
    LDA [MUL_B]

mul_step:
    CMP #0
    JZ mul_exit
    DEC A
    PUSH A

    LDA [MUL_RES]
    LDB [MUL_A]
    ADD B
    STA MUL_RES

    POP A
    JMP mul_step

mul_exit:
    RET
