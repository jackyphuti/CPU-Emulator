#ifndef CPU8_H
#define CPU8_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* CPU Flags */
#define FLAG_Z 0x01  /* Zero flag */
#define FLAG_C 0x02  /* Carry flag */
#define FLAG_N 0x04  /* Negative flag */

/* Memory-Mapped I/O Addresses */
#define MMIO_PUTC   0xF0  /* Console character output */
#define MMIO_PUTNUM 0xF1  /* Console unsigned number output */
#define MMIO_PUTHEX 0xF2  /* Console 2-digit hex output */
#define MMIO_RND    0xFE  /* Pseudo-random byte generator */
#define MMIO_TICK   0xFF  /* Low 8 bits of CPU cycle counter */

/* Instruction Opcodes */
typedef enum {
    OP_NOP     = 0x00,

    /* Immediate operations (0x10..0x17) */
    OP_LDA_IMM = 0x10,
    OP_LDB_IMM = 0x11,
    OP_ADD_IMM = 0x12,
    OP_SUB_IMM = 0x13,
    OP_AND_IMM = 0x14,
    OP_OR_IMM  = 0x15,
    OP_XOR_IMM = 0x16,
    OP_CMP_IMM = 0x17,

    /* Register ALU & Bitwise operations (0x20..0x2F) */
    OP_ADD_B   = 0x20,
    OP_SUB_B   = 0x21,
    OP_AND_B   = 0x22,
    OP_OR_B    = 0x23,
    OP_XOR_B   = 0x24,
    OP_NOT_A   = 0x25,
    OP_INC_A   = 0x26,
    OP_DEC_A   = 0x27,
    OP_INC_B   = 0x28,
    OP_DEC_B   = 0x29,
    OP_SHL_A   = 0x2A,
    OP_SHR_A   = 0x2B,
    OP_ROL_A   = 0x2C,
    OP_ROR_A   = 0x2D,
    OP_CMP_B   = 0x2E,
    OP_TEST_B  = 0x2F,

    /* Memory & Register Transfers (0x30..0x37) */
    OP_STA_ABS   = 0x30,
    OP_LDA_ABS   = 0x31,
    OP_LDB_ABS   = 0x32,
    OP_STB_ABS   = 0x33,
    OP_MOV_A_B   = 0x34,
    OP_MOV_B_A   = 0x35,
    OP_LDA_IND_B = 0x36,
    OP_STA_IND_B = 0x37,

    /* Jumps & Branches (0x40..0x46) */
    OP_JMP_ABS = 0x40,
    OP_JZ_ABS  = 0x41,
    OP_JNZ_ABS = 0x42,
    OP_JC_ABS  = 0x43,
    OP_JNC_ABS = 0x44,
    OP_JN_ABS  = 0x45,
    OP_JNN_ABS = 0x46,

    /* Stack operations (0x50..0x55) */
    OP_PUSH_A  = 0x50,
    OP_PUSH_B  = 0x51,
    OP_POP_A   = 0x52,
    OP_POP_B   = 0x53,
    OP_PUSHF   = 0x54,
    OP_POPF    = 0x55,

    /* Subroutine & Control (0x60..0xFF) */
    OP_CALL_ABS = 0x60,
    OP_RET      = 0x61,
    OP_HLT      = 0xFF
} OpCode8;

typedef void (*CPU8_OutputCallback)(void* user_data, uint8_t port, uint8_t val);

typedef struct {
    uint8_t  ram[256];
    uint8_t  pc;
    uint8_t  sp;
    uint8_t  a;
    uint8_t  b;
    uint8_t  flags;
    int16_t  ir;          /* -1 if no instruction fetched */
    uint64_t cycles;
    bool     halted;
    int16_t  stack_depth;
    int16_t  call_depth;

    /* I/O Callback */
    CPU8_OutputCallback io_callback;
    void*               io_user_data;
} CPU8;

/* CPU Lifecycle and Execution */
void        cpu8_init(CPU8* cpu);
void        cpu8_reset(CPU8* cpu);
int         cpu8_load(CPU8* cpu, const uint8_t* program, size_t size, uint8_t start_addr);
uint8_t     cpu8_fetch_byte(CPU8* cpu);
void        cpu8_push_byte(CPU8* cpu, uint8_t val);
uint8_t     cpu8_pop_byte(CPU8* cpu);
uint8_t     cpu8_read_mem(CPU8* cpu, uint8_t addr);
void        cpu8_write_mem(CPU8* cpu, uint8_t addr, uint8_t val);
uint8_t     cpu8_step(CPU8* cpu);
void        cpu8_run(CPU8* cpu, uint64_t max_cycles);

/* Flags helpers */
static inline bool cpu8_get_flag(const CPU8* cpu, uint8_t mask) {
    return (cpu->flags & mask) != 0;
}

static inline void cpu8_set_flag(CPU8* cpu, uint8_t mask, bool enabled) {
    if (enabled) cpu->flags |= mask;
    else cpu->flags &= (uint8_t)~mask;
}

/* Inspection & Disassembly */
const char* cpu8_opcode_name(uint8_t opcode);
uint8_t     cpu8_opcode_size(uint8_t opcode);
size_t      cpu8_disasm(const uint8_t* ram, uint8_t addr, char* buf, size_t buf_size);

/* I/O Configuration */
void        cpu8_set_io_callback(CPU8* cpu, CPU8_OutputCallback callback, void* user_data);

#ifdef __cplusplus
}
#endif

#endif /* CPU8_H */
