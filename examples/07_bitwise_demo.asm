; =====================================================================
; Example 7: Bitwise Logic & Shift Operations
; Demonstrates:
; - AND, OR, XOR, NOT operations
; - SHL, SHR, ROL, ROR operations
; - Hexadecimal MMIO display (port 0xF2)
; =====================================================================

.ORG 0x00

start:
    ; 1. AND demonstration: 0xF0 & 0x3C = 0x30
    LDA #0xF0
    AND #0x3C
    STA 0xF2             ; Print hex: 30
    LDA #' '
    STA 0xF0

    ; 2. OR demonstration: 0x0F | 0x80 = 0x8F
    LDA #0x0F
    OR #0x80
    STA 0xF2             ; Print hex: 8F
    LDA #' '
    STA 0xF0

    ; 3. XOR demonstration: 0xAA ^ 0xFF = 0x55
    LDA #0xAA
    XOR #0xFF
    STA 0xF2             ; Print hex: 55
    LDA #' '
    STA 0xF0

    ; 4. Shift Left (SHL): 0x07 << 1 = 0x0E
    LDA #0x07
    SHL A
    STA 0xF2             ; Print hex: 0E
    LDA #' '
    STA 0xF0

    ; 5. Shift Right (SHR): 0x80 >> 1 = 0x40
    LDA #0x80
    SHR A
    STA 0xF2             ; Print hex: 40
    LDA #10              ; newline
    STA 0xF0

    HLT
