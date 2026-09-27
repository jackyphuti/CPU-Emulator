#include "cpu8.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>

static int g_assertions = 0;
#define TEST_ASSERT(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "Assertion failed: %s at %s:%d\n", #cond, __FILE__, __LINE__); \
        exit(1); \
    } \
    g_assertions++; \
} while(0)

static void test_initialization(void) {
    CPU8 cpu;
    cpu8_init(&cpu);
    TEST_ASSERT(cpu.pc == 0x00);
    TEST_ASSERT(cpu.sp == 0xFF);
    TEST_ASSERT(cpu.a == 0x00);
    TEST_ASSERT(cpu.b == 0x00);
    TEST_ASSERT(cpu.flags == 0x00);
    TEST_ASSERT(cpu.cycles == 0);
    TEST_ASSERT(!cpu.halted);
}

static void test_alu_add_sub(void) {
    CPU8 cpu;
    cpu8_init(&cpu);

    /* LDA #250; ADD #10 -> 260 => A=4, C=1, Z=0 */
    uint8_t prog[] = {
        OP_LDA_IMM, 250,
        OP_ADD_IMM, 10,
        OP_HLT
    };
    cpu8_load(&cpu, prog, sizeof(prog), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.a == 4);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_C) == true);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_Z) == false);

    /* SUB #4 -> A=0, C=0 (no borrow), Z=1 */
    uint8_t prog_sub[] = {
        OP_LDA_IMM, 10,
        OP_SUB_IMM, 10,
        OP_HLT
    };
    cpu8_load(&cpu, prog_sub, sizeof(prog_sub), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.a == 0);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_Z) == true);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_C) == false);

    /* Borrow: 5 - 10 => 251, C=1 (borrow) */
    uint8_t prog_borrow[] = {
        OP_LDA_IMM, 5,
        OP_SUB_IMM, 10,
        OP_HLT
    };
    cpu8_load(&cpu, prog_borrow, sizeof(prog_borrow), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.a == 251);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_C) == true);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_N) == true);
}

static void test_logic_and_shifts(void) {
    CPU8 cpu;
    cpu8_init(&cpu);

    /* AND, OR, XOR, NOT */
    uint8_t prog[] = {
        OP_LDA_IMM, 0x0F,
        OP_AND_IMM, 0x33, /* A = 0x03 */
        OP_OR_IMM,  0x80, /* A = 0x83 */
        OP_XOR_IMM, 0x01, /* A = 0x82 */
        OP_NOT_A,         /* A = 0x7D */
        OP_HLT
    };
    cpu8_load(&cpu, prog, sizeof(prog), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.a == 0x7D);

    /* SHL and SHR */
    uint8_t prog_sh[] = {
        OP_LDA_IMM, 0x81,
        OP_SHL_A,         /* A = 0x02, C = 1 */
        OP_HLT
    };
    cpu8_load(&cpu, prog_sh, sizeof(prog_sh), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.a == 0x02);
    TEST_ASSERT(cpu8_get_flag(&cpu, FLAG_C) == true);
}

static void test_stack_call_ret(void) {
    CPU8 cpu;
    cpu8_init(&cpu);

    /* Subroutine: LDA #5; CALL 0x07; STA 0x50; HLT; 0x07: ADD #10; RET */
    uint8_t prog[] = {
        OP_LDA_IMM, 5,
        OP_CALL_ABS, 0x07,
        OP_STA_ABS, 0x50,
        OP_HLT,
        /* 0x07 */
        OP_ADD_IMM, 10,
        OP_RET
    };
    cpu8_load(&cpu, prog, sizeof(prog), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.ram[0x50] == 15);
    TEST_ASSERT(cpu.sp == 0xFF);
    TEST_ASSERT(cpu.stack_depth == 0);
    TEST_ASSERT(cpu.call_depth == 0);
}

static void test_indirect_memory(void) {
    CPU8 cpu;
    cpu8_init(&cpu);

    /* LDA #99; LDB #0x80; STA [B]; LDA #0; LDA [B]; HLT */
    uint8_t prog[] = {
        OP_LDA_IMM, 99,
        OP_LDB_IMM, 0x80,
        OP_STA_IND_B,
        OP_LDA_IMM, 0,
        OP_LDA_IND_B,
        OP_HLT
    };
    cpu8_load(&cpu, prog, sizeof(prog), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(cpu.ram[0x80] == 99);
    TEST_ASSERT(cpu.a == 99);
}

static char g_io_buf[64];
static size_t g_io_len = 0;

static void test_io_cb(void* ctx, uint8_t port, uint8_t val) {
    (void)ctx;
    if (port == MMIO_PUTC) {
        if (g_io_len < sizeof(g_io_buf) - 1) {
            g_io_buf[g_io_len++] = (char)val;
            g_io_buf[g_io_len] = '\0';
        }
    }
}

static void test_mmio(void) {
    CPU8 cpu;
    cpu8_init(&cpu);
    g_io_len = 0;
    cpu8_set_io_callback(&cpu, test_io_cb, NULL);

    uint8_t prog[] = {
        OP_LDA_IMM, 'O',
        OP_STA_ABS, MMIO_PUTC,
        OP_LDA_IMM, 'K',
        OP_STA_ABS, MMIO_PUTC,
        OP_HLT
    };
    cpu8_load(&cpu, prog, sizeof(prog), 0x00);
    cpu8_run(&cpu, 100);
    TEST_ASSERT(strcmp(g_io_buf, "OK") == 0);
}

int main(void) {
    printf("Running C native CPU unit tests...\n");

    test_initialization();
    test_alu_add_sub();
    test_logic_and_shifts();
    test_stack_call_ret();
    test_indirect_memory();
    test_mmio();

    printf("SUCCESS: All native CPU unit tests passed (%d assertions)!\n", g_assertions);
    return 0;
}
