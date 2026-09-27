; =====================================================================
; Example 1: Basic Addition & Subtraction with MMIO
; Demonstrates:
; - Immediate operands (#imm)
; - Subroutine calls (CALL / RET)
; - Memory-Mapped I/O output (0xF0 for char, 0xF1 for decimal)
; =====================================================================

.ORG 0x00

start:
    LDA #25              ; Load immediate value 25 into A
    LDB #17              ; Load immediate value 17 into B
    CALL add_numbers     ; Call subroutine

    ; Print label "Sum = "
    LDA #'S'
    STA 0xF0
    LDA #'u'
    STA 0xF0
    LDA #'m'
    STA 0xF0
    LDA #' '
    STA 0xF0
    LDA #'='
    STA 0xF0
    LDA #' '
    STA 0xF0

    ; Print result (42) to MMIO decimal port
    LDA 0x20             ; Load computed sum from RAM
    STA 0xF1

    ; Print newline
    LDA #10
    STA 0xF0
    HLT

add_numbers:
    ADD B                ; A = A + B (25 + 17 = 42)
    STA 0x20             ; Store result in RAM[0x20]
    RET
