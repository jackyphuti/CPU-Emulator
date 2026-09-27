; =====================================================================
; Example 3: 8-bit Software Multiplier
; Computes X * Y using repeated addition in a subroutine.
; Example: 6 * 7 = 42
; =====================================================================

.EQU ARG_X   0x50
.EQU ARG_Y   0x51
.EQU RESULT  0x52

.ORG 0x00

start:
    ; Set arguments: 6 * 7
    LDA #6
    STA ARG_X
    LDA #7
    STA ARG_Y

    CALL multiply

    ; Print "6 * 7 = "
    LDA #'6'
    STA 0xF0
    LDA #' '
    STA 0xF0
    LDA #'*'
    STA 0xF0
    LDA #' '
    STA 0xF0
    LDA #'7'
    STA 0xF0
    LDA #' '
    STA 0xF0
    LDA #'='
    STA 0xF0
    LDA #' '
    STA 0xF0

    ; Print result (42)
    LDA RESULT
    STA 0xF1

    LDA #10              ; newline
    STA 0xF0
    HLT

; Subroutine multiply: RESULT = ARG_X * ARG_Y
multiply:
    LDA #0
    STA RESULT           ; Product accumulator = 0
    LDA ARG_Y            ; Load multiplier as counter

mul_loop:
    CMP #0               ; Check if counter == 0
    JZ mul_done
    DEC A                ; Decrement counter
    PUSH A               ; Save counter

    ; Accumulate ARG_X into RESULT
    LDA RESULT
    LDB ARG_X
    ADD B
    STA RESULT

    POP A                ; Restore counter
    JMP mul_loop

mul_done:
    RET
