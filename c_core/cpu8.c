#include "cpu8.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void update_zn(CPU8* cpu, uint8_t val) {
    cpu8_set_flag(cpu, FLAG_Z, (val == 0));
    cpu8_set_flag(cpu, FLAG_N, (val & 0x80) != 0);
}

void cpu8_init(CPU8* cpu) {
    if (!cpu) return;
    memset(cpu->ram, 0, sizeof(cpu->ram));
    cpu->pc = 0x00;
    cpu->sp = 0xFF;
    cpu->a = 0x00;
    cpu->b = 0x00;
    cpu->flags = 0x00;
    cpu->ir = -1;
    cpu->cycles = 0;
    cpu->halted = false;
    cpu->stack_depth = 0;
    cpu->call_depth = 0;
    cpu->io_callback = NULL;
    cpu->io_user_data = NULL;
}

void cpu8_reset(CPU8* cpu) {
    cpu8_init(cpu);
}

int cpu8_load(CPU8* cpu, const uint8_t* program, size_t size, uint8_t start_addr) {
    if (!cpu || !program) return -1;
    if ((size_t)start_addr + size > 256) return -2;

    memset(cpu->ram, 0, sizeof(cpu->ram));
    memcpy(&cpu->ram[start_addr], program, size);

    cpu->pc = start_addr;
    cpu->sp = 0xFF;
    cpu->a = 0x00;
    cpu->b = 0x00;
    cpu->flags = 0x00;
    cpu->ir = -1;
    cpu->cycles = 0;
    cpu->halted = false;
    cpu->stack_depth = 0;
    cpu->call_depth = 0;
    return 0;
}

uint8_t cpu8_fetch_byte(CPU8* cpu) {
    uint8_t val = cpu->ram[cpu->pc];
    cpu->pc = (uint8_t)(cpu->pc + 1);
    return val;
}

void cpu8_push_byte(CPU8* cpu, uint8_t val) {
    if (cpu->stack_depth >= 256) {
        /* Stack overflow */
        cpu->halted = true;
        return;
    }
    cpu->ram[cpu->sp] = val;
    cpu->sp = (uint8_t)(cpu->sp - 1);
    cpu->stack_depth++;
}

uint8_t cpu8_pop_byte(CPU8* cpu) {
    if (cpu->stack_depth <= 0) {
        /* Stack underflow */
        cpu->halted = true;
        return 0;
    }
    cpu->sp = (uint8_t)(cpu->sp + 1);
    uint8_t val = cpu->ram[cpu->sp];
    cpu->stack_depth--;
    return val;
}

uint8_t cpu8_read_mem(CPU8* cpu, uint8_t addr) {
    if (addr == MMIO_RND) {
        return (uint8_t)(rand() & 0xFF);
    }
    if (addr == MMIO_TICK) {
        return (uint8_t)(cpu->cycles & 0xFF);
    }
    return cpu->ram[addr];
}

void cpu8_write_mem(CPU8* cpu, uint8_t addr, uint8_t val) {
    cpu->ram[addr] = val;

    if (addr == MMIO_PUTC || addr == MMIO_PUTNUM || addr == MMIO_PUTHEX) {
        if (cpu->io_callback) {
            cpu->io_callback(cpu->io_user_data, addr, val);
        } else {
            if (addr == MMIO_PUTC) {
                putchar((char)val);
                fflush(stdout);
            } else if (addr == MMIO_PUTNUM) {
                printf("%u", (unsigned int)val);
                fflush(stdout);
            } else if (addr == MMIO_PUTHEX) {
                printf("%02X", (unsigned int)val);
                fflush(stdout);
            }
        }
    }
}

uint8_t cpu8_opcode_size(uint8_t opcode) {
    switch (opcode) {
        case OP_LDA_IMM:
        case OP_LDB_IMM:
        case OP_ADD_IMM:
        case OP_SUB_IMM:
        case OP_AND_IMM:
        case OP_OR_IMM:
        case OP_XOR_IMM:
        case OP_CMP_IMM:
        case OP_STA_ABS:
        case OP_LDA_ABS:
        case OP_LDB_ABS:
        case OP_STB_ABS:
        case OP_JMP_ABS:
        case OP_JZ_ABS:
        case OP_JNZ_ABS:
        case OP_JC_ABS:
        case OP_JNC_ABS:
        case OP_JN_ABS:
        case OP_JNN_ABS:
        case OP_CALL_ABS:
            return 2;
        default:
            return 1;
    }
}

const char* cpu8_opcode_name(uint8_t opcode) {
    switch (opcode) {
        case OP_NOP: return "NOP";
        case OP_LDA_IMM: return "LDA_IMM";
        case OP_LDB_IMM: return "LDB_IMM";
        case OP_ADD_IMM: return "ADD_IMM";
        case OP_SUB_IMM: return "SUB_IMM";
        case OP_AND_IMM: return "AND_IMM";
        case OP_OR_IMM: return "OR_IMM";
        case OP_XOR_IMM: return "XOR_IMM";
        case OP_CMP_IMM: return "CMP_IMM";
        case OP_ADD_B: return "ADD_B";
        case OP_SUB_B: return "SUB_B";
        case OP_AND_B: return "AND_B";
        case OP_OR_B: return "OR_B";
        case OP_XOR_B: return "XOR_B";
        case OP_NOT_A: return "NOT_A";
        case OP_INC_A: return "INC_A";
        case OP_DEC_A: return "DEC_A";
        case OP_INC_B: return "INC_B";
        case OP_DEC_B: return "DEC_B";
        case OP_SHL_A: return "SHL_A";
        case OP_SHR_A: return "SHR_A";
        case OP_ROL_A: return "ROL_A";
        case OP_ROR_A: return "ROR_A";
        case OP_CMP_B: return "CMP_B";
        case OP_TEST_B: return "TEST_B";
        case OP_STA_ABS: return "STA_ABS";
        case OP_LDA_ABS: return "LDA_ABS";
        case OP_LDB_ABS: return "LDB_ABS";
        case OP_STB_ABS: return "STB_ABS";
        case OP_MOV_A_B: return "MOV_A_B";
        case OP_MOV_B_A: return "MOV_B_A";
        case OP_LDA_IND_B: return "LDA_IND_B";
        case OP_STA_IND_B: return "STA_IND_B";
        case OP_JMP_ABS: return "JMP_ABS";
        case OP_JZ_ABS: return "JZ_ABS";
        case OP_JNZ_ABS: return "JNZ_ABS";
        case OP_JC_ABS: return "JC_ABS";
        case OP_JNC_ABS: return "JNC_ABS";
        case OP_JN_ABS: return "JN_ABS";
        case OP_JNN_ABS: return "JNN_ABS";
        case OP_PUSH_A: return "PUSH_A";
        case OP_PUSH_B: return "PUSH_B";
        case OP_POP_A: return "POP_A";
        case OP_POP_B: return "POP_B";
        case OP_PUSHF: return "PUSHF";
        case OP_POPF: return "POPF";
        case OP_CALL_ABS: return "CALL_ABS";
        case OP_RET: return "RET";
        case OP_HLT: return "HLT";
        default: return "UNKNOWN";
    }
}

size_t cpu8_disasm(const uint8_t* ram, uint8_t addr, char* buf, size_t buf_size) {
    if (!ram || !buf || buf_size == 0) return 0;

    uint8_t op = ram[addr];
    uint8_t next = ram[(uint8_t)(addr + 1)];

    switch (op) {
        case OP_NOP: return snprintf(buf, buf_size, "NOP");
        case OP_LDA_IMM: return snprintf(buf, buf_size, "LDA #0x%02X", next);
        case OP_LDB_IMM: return snprintf(buf, buf_size, "LDB #0x%02X", next);
        case OP_ADD_IMM: return snprintf(buf, buf_size, "ADD #0x%02X", next);
        case OP_SUB_IMM: return snprintf(buf, buf_size, "SUB #0x%02X", next);
        case OP_AND_IMM: return snprintf(buf, buf_size, "AND #0x%02X", next);
        case OP_OR_IMM:  return snprintf(buf, buf_size, "OR #0x%02X", next);
        case OP_XOR_IMM: return snprintf(buf, buf_size, "XOR #0x%02X", next);
        case OP_CMP_IMM: return snprintf(buf, buf_size, "CMP #0x%02X", next);
        case OP_ADD_B: return snprintf(buf, buf_size, "ADD B");
        case OP_SUB_B: return snprintf(buf, buf_size, "SUB B");
        case OP_AND_B: return snprintf(buf, buf_size, "AND B");
        case OP_OR_B:  return snprintf(buf, buf_size, "OR B");
        case OP_XOR_B: return snprintf(buf, buf_size, "XOR B");
        case OP_NOT_A: return snprintf(buf, buf_size, "NOT A");
        case OP_INC_A: return snprintf(buf, buf_size, "INC A");
        case OP_DEC_A: return snprintf(buf, buf_size, "DEC A");
        case OP_INC_B: return snprintf(buf, buf_size, "INC B");
        case OP_DEC_B: return snprintf(buf, buf_size, "DEC B");
        case OP_SHL_A: return snprintf(buf, buf_size, "SHL A");
        case OP_SHR_A: return snprintf(buf, buf_size, "SHR A");
        case OP_ROL_A: return snprintf(buf, buf_size, "ROL A");
        case OP_ROR_A: return snprintf(buf, buf_size, "ROR A");
        case OP_CMP_B: return snprintf(buf, buf_size, "CMP B");
        case OP_TEST_B: return snprintf(buf, buf_size, "TEST B");
        case OP_STA_ABS: return snprintf(buf, buf_size, "STA 0x%02X", next);
        case OP_LDA_ABS: return snprintf(buf, buf_size, "LDA [0x%02X]", next);
        case OP_LDB_ABS: return snprintf(buf, buf_size, "LDB [0x%02X]", next);
        case OP_STB_ABS: return snprintf(buf, buf_size, "STB 0x%02X", next);
        case OP_MOV_A_B: return snprintf(buf, buf_size, "MOV A, B");
        case OP_MOV_B_A: return snprintf(buf, buf_size, "MOV B, A");
        case OP_LDA_IND_B: return snprintf(buf, buf_size, "LDA [B]");
        case OP_STA_IND_B: return snprintf(buf, buf_size, "STA [B]");
        case OP_JMP_ABS: return snprintf(buf, buf_size, "JMP 0x%02X", next);
        case OP_JZ_ABS:  return snprintf(buf, buf_size, "JZ 0x%02X", next);
        case OP_JNZ_ABS: return snprintf(buf, buf_size, "JNZ 0x%02X", next);
        case OP_JC_ABS:  return snprintf(buf, buf_size, "JC 0x%02X", next);
        case OP_JNC_ABS: return snprintf(buf, buf_size, "JNC 0x%02X", next);
        case OP_JN_ABS:  return snprintf(buf, buf_size, "JN 0x%02X", next);
        case OP_JNN_ABS: return snprintf(buf, buf_size, "JNN 0x%02X", next);
        case OP_PUSH_A: return snprintf(buf, buf_size, "PUSH A");
        case OP_PUSH_B: return snprintf(buf, buf_size, "PUSH B");
        case OP_POP_A:  return snprintf(buf, buf_size, "POP A");
        case OP_POP_B:  return snprintf(buf, buf_size, "POP B");
        case OP_PUSHF:  return snprintf(buf, buf_size, "PUSHF");
        case OP_POPF:   return snprintf(buf, buf_size, "POPF");
        case OP_CALL_ABS: return snprintf(buf, buf_size, "CALL 0x%02X", next);
        case OP_RET: return snprintf(buf, buf_size, "RET");
        case OP_HLT: return snprintf(buf, buf_size, "HLT");
        default: return snprintf(buf, buf_size, "DB 0x%02X", op);
    }
}

uint8_t cpu8_step(CPU8* cpu) {
    if (!cpu || cpu->halted) return 0xFF;

    uint8_t opcode = cpu8_fetch_byte(cpu);
    cpu->ir = opcode;

    switch (opcode) {
        case OP_NOP:
            break;

        /* Immediate */
        case OP_LDA_IMM: {
            cpu->a = cpu8_fetch_byte(cpu);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_LDB_IMM: {
            cpu->b = cpu8_fetch_byte(cpu);
            update_zn(cpu, cpu->b);
            break;
        }
        case OP_ADD_IMM: {
            uint8_t imm = cpu8_fetch_byte(cpu);
            uint16_t res = (uint16_t)cpu->a + imm;
            cpu8_set_flag(cpu, FLAG_C, res > 0xFF);
            cpu->a = (uint8_t)(res & 0xFF);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_SUB_IMM: {
            uint8_t imm = cpu8_fetch_byte(cpu);
            bool borrow = cpu->a < imm;
            cpu8_set_flag(cpu, FLAG_C, borrow);
            cpu->a = (uint8_t)(cpu->a - imm);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_AND_IMM: {
            uint8_t imm = cpu8_fetch_byte(cpu);
            cpu->a &= imm;
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_OR_IMM: {
            uint8_t imm = cpu8_fetch_byte(cpu);
            cpu->a |= imm;
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_XOR_IMM: {
            uint8_t imm = cpu8_fetch_byte(cpu);
            cpu->a ^= imm;
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_CMP_IMM: {
            uint8_t imm = cpu8_fetch_byte(cpu);
            bool borrow = cpu->a < imm;
            uint8_t diff = (uint8_t)(cpu->a - imm);
            cpu8_set_flag(cpu, FLAG_C, borrow);
            cpu8_set_flag(cpu, FLAG_Z, diff == 0);
            cpu8_set_flag(cpu, FLAG_N, (diff & 0x80) != 0);
            break;
        }

        /* Register ALU */
        case OP_ADD_B: {
            uint16_t res = (uint16_t)cpu->a + cpu->b;
            cpu8_set_flag(cpu, FLAG_C, res > 0xFF);
            cpu->a = (uint8_t)(res & 0xFF);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_SUB_B: {
            bool borrow = cpu->a < cpu->b;
            cpu8_set_flag(cpu, FLAG_C, borrow);
            cpu->a = (uint8_t)(cpu->a - cpu->b);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_AND_B: {
            cpu->a &= cpu->b;
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_OR_B: {
            cpu->a |= cpu->b;
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_XOR_B: {
            cpu->a ^= cpu->b;
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_NOT_A: {
            cpu->a = (uint8_t)(~cpu->a);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_INC_A: {
            cpu->a = (uint8_t)(cpu->a + 1);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_DEC_A: {
            cpu->a = (uint8_t)(cpu->a - 1);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_INC_B: {
            cpu->b = (uint8_t)(cpu->b + 1);
            update_zn(cpu, cpu->b);
            break;
        }
        case OP_DEC_B: {
            cpu->b = (uint8_t)(cpu->b - 1);
            update_zn(cpu, cpu->b);
            break;
        }
        case OP_SHL_A: {
            bool bit7 = (cpu->a & 0x80) != 0;
            cpu->a = (uint8_t)(cpu->a << 1);
            cpu8_set_flag(cpu, FLAG_C, bit7);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_SHR_A: {
            bool bit0 = (cpu->a & 0x01) != 0;
            cpu->a = (uint8_t)(cpu->a >> 1);
            cpu8_set_flag(cpu, FLAG_C, bit0);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_ROL_A: {
            uint8_t old_c = cpu8_get_flag(cpu, FLAG_C) ? 1 : 0;
            bool new_c = (cpu->a & 0x80) != 0;
            cpu->a = (uint8_t)((cpu->a << 1) | old_c);
            cpu8_set_flag(cpu, FLAG_C, new_c);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_ROR_A: {
            uint8_t old_c = cpu8_get_flag(cpu, FLAG_C) ? 1 : 0;
            bool new_c = (cpu->a & 0x01) != 0;
            cpu->a = (uint8_t)((cpu->a >> 1) | (old_c << 7));
            cpu8_set_flag(cpu, FLAG_C, new_c);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_CMP_B: {
            bool borrow = cpu->a < cpu->b;
            uint8_t diff = (uint8_t)(cpu->a - cpu->b);
            cpu8_set_flag(cpu, FLAG_C, borrow);
            cpu8_set_flag(cpu, FLAG_Z, diff == 0);
            cpu8_set_flag(cpu, FLAG_N, (diff & 0x80) != 0);
            break;
        }
        case OP_TEST_B: {
            uint8_t val = (uint8_t)(cpu->a & cpu->b);
            cpu8_set_flag(cpu, FLAG_C, false);
            update_zn(cpu, val);
            break;
        }

        /* Memory & Transfers */
        case OP_STA_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            cpu8_write_mem(cpu, addr, cpu->a);
            break;
        }
        case OP_LDA_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            cpu->a = cpu8_read_mem(cpu, addr);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_LDB_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            cpu->b = cpu8_read_mem(cpu, addr);
            update_zn(cpu, cpu->b);
            break;
        }
        case OP_STB_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            cpu8_write_mem(cpu, addr, cpu->b);
            break;
        }
        case OP_MOV_A_B: {
            cpu->a = cpu->b;
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_MOV_B_A: {
            cpu->b = cpu->a;
            update_zn(cpu, cpu->b);
            break;
        }
        case OP_LDA_IND_B: {
            cpu->a = cpu8_read_mem(cpu, cpu->b);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_STA_IND_B: {
            cpu8_write_mem(cpu, cpu->b, cpu->a);
            break;
        }

        /* Jumps & Branches */
        case OP_JMP_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            cpu->pc = addr;
            break;
        }
        case OP_JZ_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            if (cpu8_get_flag(cpu, FLAG_Z)) cpu->pc = addr;
            break;
        }
        case OP_JNZ_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            if (!cpu8_get_flag(cpu, FLAG_Z)) cpu->pc = addr;
            break;
        }
        case OP_JC_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            if (cpu8_get_flag(cpu, FLAG_C)) cpu->pc = addr;
            break;
        }
        case OP_JNC_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            if (!cpu8_get_flag(cpu, FLAG_C)) cpu->pc = addr;
            break;
        }
        case OP_JN_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            if (cpu8_get_flag(cpu, FLAG_N)) cpu->pc = addr;
            break;
        }
        case OP_JNN_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            if (!cpu8_get_flag(cpu, FLAG_N)) cpu->pc = addr;
            break;
        }

        /* Stack Operations */
        case OP_PUSH_A: {
            cpu8_push_byte(cpu, cpu->a);
            break;
        }
        case OP_PUSH_B: {
            cpu8_push_byte(cpu, cpu->b);
            break;
        }
        case OP_POP_A: {
            cpu->a = cpu8_pop_byte(cpu);
            update_zn(cpu, cpu->a);
            break;
        }
        case OP_POP_B: {
            cpu->b = cpu8_pop_byte(cpu);
            update_zn(cpu, cpu->b);
            break;
        }
        case OP_PUSHF: {
            cpu8_push_byte(cpu, cpu->flags);
            break;
        }
        case OP_POPF: {
            cpu->flags = (uint8_t)(cpu8_pop_byte(cpu) & 0x07);
            break;
        }

        /* Subroutine & Control */
        case OP_CALL_ABS: {
            uint8_t addr = cpu8_fetch_byte(cpu);
            uint8_t ret_addr = cpu->pc;
            cpu8_push_byte(cpu, ret_addr);
            cpu->call_depth++;
            cpu->pc = addr;
            break;
        }
        case OP_RET: {
            cpu->pc = cpu8_pop_byte(cpu);
            if (cpu->call_depth > 0) cpu->call_depth--;
            break;
        }
        case OP_HLT: {
            cpu->halted = true;
            break;
        }

        default:
            /* Illegal opcode */
            cpu->halted = true;
            break;
    }

    cpu->cycles++;
    cpu->ir = -1;
    return opcode;
}

void cpu8_run(CPU8* cpu, uint64_t max_cycles) {
    if (!cpu) return;
    while (!cpu->halted && cpu->cycles < max_cycles) {
        cpu8_step(cpu);
    }
}

void cpu8_set_io_callback(CPU8* cpu, CPU8_OutputCallback callback, void* user_data) {
    if (!cpu) return;
    cpu->io_callback = callback;
    cpu->io_user_data = user_data;
}
