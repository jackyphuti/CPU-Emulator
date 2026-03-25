; Sample program for the 8-bit CPU emulator
; Demonstrates PUSH/POP and CALL/RET

start:
    LDA #7
    LDB #5
    CALL add_numbers
    STA 0x0F
    HLT

add_numbers:
    PUSH B
    POP B
    ADD B
    RET
