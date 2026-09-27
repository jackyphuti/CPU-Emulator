#include "cpu8.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

#define MAX_BREAKPOINTS 32

typedef struct {
    CPU8 cpu;
    uint8_t breakpoints[MAX_BREAKPOINTS];
    size_t bp_count;
    bool trace;
} Debugger;

static void print_registers(const CPU8* cpu) {
    printf("PC: 0x%02X | SP: 0x%02X | A: 0x%02X (%3u) | B: 0x%02X (%3u) | FLAGS: [Z:%d C:%d N:%d]\n",
           cpu->pc, cpu->sp, cpu->a, cpu->a, cpu->b, cpu->b,
           cpu8_get_flag(cpu, FLAG_Z) ? 1 : 0,
           cpu8_get_flag(cpu, FLAG_C) ? 1 : 0,
           cpu8_get_flag(cpu, FLAG_N) ? 1 : 0);
    printf("Cycles: %llu | Stack Depth: %d | Call Depth: %d | Status: %s\n",
           (unsigned long long)cpu->cycles,
           cpu->stack_depth,
           cpu->call_depth,
           cpu->halted ? "HALTED" : "RUNNING");
}

static void print_memory(const CPU8* cpu, uint8_t start, uint8_t count) {
    uint16_t end = (uint16_t)start + count;
    if (end > 256) end = 256;

    for (uint16_t base = start & 0xF0; base < end; base += 16) {
        printf("%02X: ", (unsigned int)base);
        for (int i = 0; i < 16; i++) {
            uint16_t addr = base + i;
            if (addr >= start && addr < end) {
                printf("%02X ", cpu->ram[addr]);
            } else {
                printf(".. ");
            }
        }
        printf(" |");
        for (int i = 0; i < 16; i++) {
            uint16_t addr = base + i;
            if (addr >= start && addr < end) {
                char c = (char)cpu->ram[addr];
                printf("%c", (isprint((unsigned char)c) ? c : '.'));
            } else {
                printf(" ");
            }
        }
        printf("|\n");
    }
}

static void print_disasm_range(const CPU8* cpu, uint8_t start, int count) {
    uint8_t addr = start;
    char line[64];

    for (int i = 0; i < count; i++) {
        cpu8_disasm(cpu->ram, addr, line, sizeof(line));
        const char* marker = (addr == cpu->pc) ? "==> " : "    ";
        printf("%s0x%02X: %s\n", marker, addr, line);
        uint8_t sz = cpu8_opcode_size(cpu->ram[addr]);
        addr = (uint8_t)(addr + sz);
    }
}

static bool is_breakpoint(const Debugger* dbg, uint8_t addr) {
    for (size_t i = 0; i < dbg->bp_count; i++) {
        if (dbg->breakpoints[i] == addr) return true;
    }
    return false;
}

static void add_breakpoint(Debugger* dbg, uint8_t addr) {
    if (is_breakpoint(dbg, addr)) {
        printf("Breakpoint already exists at 0x%02X\n", addr);
        return;
    }
    if (dbg->bp_count < MAX_BREAKPOINTS) {
        dbg->breakpoints[dbg->bp_count++] = addr;
        printf("Breakpoint added at 0x%02X\n", addr);
    } else {
        printf("Maximum breakpoints reached (%d)\n", MAX_BREAKPOINTS);
    }
}

static void remove_breakpoint(Debugger* dbg, uint8_t addr) {
    for (size_t i = 0; i < dbg->bp_count; i++) {
        if (dbg->breakpoints[i] == addr) {
            dbg->breakpoints[i] = dbg->breakpoints[dbg->bp_count - 1];
            dbg->bp_count--;
            printf("Breakpoint removed at 0x%02X\n", addr);
            return;
        }
    }
    printf("No breakpoint found at 0x%02X\n", addr);
}

static void io_handler(void* user_data, uint8_t port, uint8_t val) {
    (void)user_data;
    if (port == MMIO_PUTC) {
        putchar((char)val);
        fflush(stdout);
    } else if (port == MMIO_PUTNUM) {
        printf("[OUT:%u]", (unsigned int)val);
        fflush(stdout);
    } else if (port == MMIO_PUTHEX) {
        printf("[OUT:0x%02X]", (unsigned int)val);
        fflush(stdout);
    }
}

static void run_benchmark(void) {
    CPU8 cpu;
    cpu8_init(&cpu);

    /* Benchmark program: tight loop counting down from 255 */
    /* 0x00: LDA #255; 0x02: DEC A; 0x03: JNZ 0x02; 0x05: HLT */
    uint8_t bench_prog[] = {
        OP_LDA_IMM, 0xFF,
        OP_DEC_A,
        OP_JNZ_ABS, 0x02,
        OP_HLT
    };

    printf("Running benchmark: 5,000,000 iterations...\n");
    clock_t start = clock();

    const int iterations = 20000;
    for (int i = 0; i < iterations; i++) {
        cpu8_load(&cpu, bench_prog, sizeof(bench_prog), 0x00);
        cpu8_run(&cpu, 1000000);
    }

    clock_t end = clock();
    double elapsed = (double)(end - start) / CLOCKS_PER_SEC;
    uint64_t total_cycles = (uint64_t)iterations * (2 + 255 * 2 + 1);

    printf("Executed %llu cycles in %.3f seconds (%.2f MHz / %.2f MIPS)\n",
           (unsigned long long)total_cycles,
           elapsed,
           (total_cycles / elapsed) / 1e6,
           (total_cycles / elapsed) / 1e6);
}

int main(int argc, char* argv[]) {
    Debugger dbg;
    cpu8_init(&dbg.cpu);
    dbg.bp_count = 0;
    dbg.trace = false;
    cpu8_set_io_callback(&dbg.cpu, io_handler, NULL);

    const char* filename = NULL;
    bool direct_run = false;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--bench") == 0) {
            run_benchmark();
            return 0;
        } else if (strcmp(argv[i], "--run") == 0) {
            direct_run = true;
        } else if (strcmp(argv[i], "--trace") == 0) {
            dbg.trace = true;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            printf("Usage: %s [options] [program.bin]\n", argv[0]);
            printf("Options:\n");
            printf("  --run       Execute program immediately until HLT and exit\n");
            printf("  --trace     Enable instruction trace logging\n");
            printf("  --bench     Run emulator performance benchmark\n");
            printf("  -h, --help  Show this help message\n");
            return 0;
        } else if (argv[i][0] != '-') {
            filename = argv[i];
        }
    }

    if (filename) {
        FILE* f = fopen(filename, "rb");
        if (!f) {
            fprintf(stderr, "Error: Could not open file '%s'\n", filename);
            return 1;
        }
        uint8_t buffer[256];
        size_t n = fread(buffer, 1, sizeof(buffer), f);
        fclose(f);
        cpu8_load(&dbg.cpu, buffer, n, 0x00);
        printf("Loaded %zu bytes from '%s'\n", n, filename);
    } else {
        /* Default demo program: Add 7 + 5 using CALL/RET and print result */
        uint8_t demo[] = {
            OP_LDA_IMM, 0x07,
            OP_LDB_IMM, 0x05,
            OP_CALL_ABS, 0x0B,
            OP_STA_ABS, MMIO_PUTNUM,
            OP_LDA_IMM, '\n',
            OP_STA_ABS, MMIO_PUTC,
            OP_HLT,
            /* 0x0B: add subroutine */
            OP_ADD_B,
            OP_RET
        };
        cpu8_load(&dbg.cpu, demo, sizeof(demo), 0x00);
        printf("Loaded built-in demo program (7 + 5 -> MMIO Console)\n");
    }

    if (direct_run) {
        cpu8_run(&dbg.cpu, 10000000);
        return 0;
    }

    printf("\n=== 8-Bit CPU Native Debugger (C/C++ Engine) ===\n");
    printf("Type 'help' for command list. Press Ctrl+C or 'q' to quit.\n\n");
    print_registers(&dbg.cpu);
    print_disasm_range(&dbg.cpu, dbg.cpu.pc, 3);

    char cmd[128];
    while (1) {
        printf("\ncpu8 [0x%02X]> ", dbg.cpu.pc);
        if (!fgets(cmd, sizeof(cmd), stdin)) break;

        char* p = cmd;
        while (isspace((unsigned char)*p)) p++;
        if (*p == '\0') continue;

        if (strncmp(p, "q", 1) == 0 || strncmp(p, "exit", 4) == 0) {
            break;
        } else if (strncmp(p, "s", 1) == 0 || strncmp(p, "step", 4) == 0) {
            if (dbg.cpu.halted) {
                printf("CPU is halted. Reset to step again.\n");
            } else {
                char dis[64];
                cpu8_disasm(dbg.cpu.ram, dbg.cpu.pc, dis, sizeof(dis));
                printf("[C:%04llu] 0x%02X: %s\n", (unsigned long long)dbg.cpu.cycles, dbg.cpu.pc, dis);
                cpu8_step(&dbg.cpu);
                print_registers(&dbg.cpu);
            }
        } else if (strncmp(p, "r", 1) == 0 || strncmp(p, "run", 3) == 0) {
            if (dbg.cpu.halted) {
                printf("CPU is halted. Reset to run again.\n");
            } else {
                printf("Running...\n");
                while (!dbg.cpu.halted) {
                    if (is_breakpoint(&dbg, dbg.cpu.pc)) {
                        printf("\n[!] Hit breakpoint at 0x%02X\n", dbg.cpu.pc);
                        break;
                    }
                    if (dbg.trace) {
                        char dis[64];
                        cpu8_disasm(dbg.cpu.ram, dbg.cpu.pc, dis, sizeof(dis));
                        printf("[C:%04llu] 0x%02X: %s\n", (unsigned long long)dbg.cpu.cycles, dbg.cpu.pc, dis);
                    }
                    cpu8_step(&dbg.cpu);
                }
                print_registers(&dbg.cpu);
            }
        } else if (strncmp(p, "reg", 3) == 0) {
            print_registers(&dbg.cpu);
        } else if (strncmp(p, "mem", 3) == 0) {
            int addr = 0, count = 32;
            sscanf(p + 3, "%i %i", &addr, &count);
            print_memory(&dbg.cpu, (uint8_t)addr, (uint8_t)count);
        } else if (strncmp(p, "dis", 3) == 0) {
            int addr = dbg.cpu.pc, count = 10;
            sscanf(p + 3, "%i %i", &addr, &count);
            print_disasm_range(&dbg.cpu, (uint8_t)addr, count);
        } else if (strncmp(p, "b ", 2) == 0 || strncmp(p, "bp ", 3) == 0) {
            int addr = 0;
            sscanf(p + (p[1] == ' ' ? 2 : 3), "%i", &addr);
            add_breakpoint(&dbg, (uint8_t)addr);
        } else if (strncmp(p, "del ", 4) == 0) {
            int addr = 0;
            sscanf(p + 4, "%i", &addr);
            remove_breakpoint(&dbg, (uint8_t)addr);
        } else if (strncmp(p, "reset", 5) == 0) {
            dbg.cpu.pc = 0x00;
            dbg.cpu.sp = 0xFF;
            dbg.cpu.a = 0x00;
            dbg.cpu.b = 0x00;
            dbg.cpu.flags = 0x00;
            dbg.cpu.cycles = 0;
            dbg.cpu.halted = false;
            dbg.cpu.stack_depth = 0;
            dbg.cpu.call_depth = 0;
            printf("CPU reset to initial state.\n");
            print_registers(&dbg.cpu);
        } else if (strncmp(p, "trace", 5) == 0) {
            dbg.trace = !dbg.trace;
            printf("Trace mode: %s\n", dbg.trace ? "ON" : "OFF");
        } else if (strncmp(p, "bench", 5) == 0) {
            run_benchmark();
        } else {
            printf("Commands:\n");
            printf("  s, step             Execute single instruction\n");
            printf("  r, run              Run program until HLT or breakpoint\n");
            printf("  reg                 Display CPU registers and flags\n");
            printf("  mem <addr> [count]  Dump memory in hex and ASCII\n");
            printf("  dis [addr] [count]  Disassemble instructions\n");
            printf("  bp <addr>           Add breakpoint at hex/dec address\n");
            printf("  del <addr>          Remove breakpoint\n");
            printf("  trace               Toggle execution tracing\n");
            printf("  reset               Reset CPU registers and cycle count\n");
            printf("  bench               Run benchmark test\n");
            printf("  q, quit             Exit debugger\n");
        }
    }

    return 0;
}
