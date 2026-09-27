; =====================================================================
; Example 5: Hello, World! with Null-Terminated String
; Demonstrates:
; - DB string directives with embedded escape sequences
; - Pointer-based string traversal using Register B and LDA [B]
; - Memory-Mapped I/O Character Console (MMIO port 0xF0)
; =====================================================================

.ORG 0x00

start:
    LDB #msg_hello       ; B points to beginning of string

print_char_loop:
    LDA [B]              ; Load character at RAM[B] into A
    JZ done              ; If character == 0 (null terminator), finish
    STA 0xF0             ; Write character to MMIO console
    INC B                ; Advance pointer B to next character
    JMP print_char_loop  ; Repeat

done:
    HLT

msg_hello:
    DB "Hello, 8-Bit CPU World!\n", 0
