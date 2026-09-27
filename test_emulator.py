import unittest
from cpu_emulator import (
    CPU8Bit,
    OpCode,
    FLAG_Z,
    FLAG_C,
    FLAG_N,
    IO_PUTC,
    IO_PUTNUM,
    IO_PUTHEX,
    IO_RND,
    IO_TICK,
)
from assembler import assemble, AssemblerError


class TestCPUInstructions(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU8Bit()

    def test_immediate_and_flags(self):
        code = """
        LDA #0x00
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 0x00)
        self.assertTrue(self.cpu.get_flag(FLAG_Z))
        self.assertFalse(self.cpu.get_flag(FLAG_N))

        code_neg = """
        LDA #0x85
        HLT
        """
        self.cpu.load_program(assemble(code_neg))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 0x85)
        self.assertFalse(self.cpu.get_flag(FLAG_Z))
        self.assertTrue(self.cpu.get_flag(FLAG_N))

    def test_alu_operations(self):
        code = """
        LDA #10
        ADD #15
        SUB #5
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 20)

        # Logic operations
        code_logic = """
        LDA #0x0F
        AND #0x33
        OR #0x80
        XOR #0x01
        NOT A
        HLT
        """
        # 0x0F & 0x33 = 0x03
        # 0x03 | 0x80 = 0x83
        # 0x83 ^ 0x01 = 0x82
        # ~0x82 & 0xFF = 0x7D
        self.cpu.load_program(assemble(code_logic))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 0x7D)

    def test_shifts_and_rotates(self):
        code = """
        LDA #0x81
        SHL A
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 0x02)
        self.assertTrue(self.cpu.get_flag(FLAG_C))

        code_shr = """
        LDA #0x05
        SHR A
        HLT
        """
        self.cpu.load_program(assemble(code_shr))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 0x02)
        self.assertTrue(self.cpu.get_flag(FLAG_C))

    def test_inc_dec_and_mov(self):
        code = """
        LDA #10
        INC A
        MOV B, A
        DEC B
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.a, 11)
        self.assertEqual(self.cpu.b, 10)

    def test_cmp_and_branches(self):
        code = """
        LDA #25
        CMP #25
        JZ equal
        HLT
        equal:
        LDB #100
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.b, 100)

        code_jnz = """
        LDA #10
        CMP #20
        JNZ not_equal
        HLT
        not_equal:
        LDB #50
        HLT
        """
        self.cpu.load_program(assemble(code_jnz))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.b, 50)
        self.assertTrue(self.cpu.get_flag(FLAG_C))

    def test_indirect_memory(self):
        code = """
        .ORG 0x00
        LDA #42
        LDB #0x80
        STA [B]
        LDA #0
        LDA [B]
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.ram[0x80], 42)
        self.assertEqual(self.cpu.a, 42)

    def test_stack_and_flags(self):
        code = """
        LDA #0x00
        CMP #0x00     ; Sets Zero flag
        PUSHF
        LDA #0xFF
        CMP #0x01     ; Clears Zero flag
        POPF
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertTrue(self.cpu.get_flag(FLAG_Z))

    def test_mmio_output(self):
        code = """
        LDA #'H'
        STA 0xF0
        LDA #123
        STA 0xF1
        LDA #0xAB
        STA 0xF2
        HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.io_output, ['H', '123', 'AB'])

    def test_assembler_strings_and_words(self):
        code = """
        .ORG 0x00
        DB "OK", 0
        DW 0x1234
        """
        binary = assemble(code)
        self.assertEqual(binary[:3], [ord('O'), ord('K'), 0])
        self.assertEqual(binary[3:5], [0x34, 0x12])


class TestAlgorithms(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU8Bit()

    def test_fibonacci(self):
        # Computes 7th Fibonacci number (1, 1, 2, 3, 5, 8, 13)
        code = """
        .ORG 0x00
        start:
            LDA #1
            STA 0x70      ; a = 1
            LDA #1
            STA 0x71      ; b = 1
            LDA #5
            STA 0x73      ; counter = 5
        fib_loop:
            LDA 0x70
            LDB 0x71
            ADD B         ; A = a + b
            PUSH A        ; save new sum
            LDA 0x71
            STA 0x70      ; a = b
            POP A
            STA 0x71      ; b = new sum
            LDA 0x73
            DEC A
            STA 0x73
            JNZ fib_loop
        done:
            LDA 0x71
            STA 0x72      ; store result
            HLT
        """
        self.cpu.load_program(assemble(code))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.ram[0x72], 13)

    def test_factorial_loop(self):
        # 4! = 24
        code = """
        .ORG 0x00
        start:
            LDA #4
            STA 0x80      ; N = 4
            LDA #1
            STA 0x81      ; result = 1

        fact_loop:
            LDA 0x80
            CMP #1
            JZ done
            ; multiply result (0x81) by N (0x80)
            LDA #0
            STA 0x82      ; temp_product = 0
            LDB 0x80      ; counter = N
        mul_loop:
            LDA 0x82
            LDB 0x81
            ADD B
            STA 0x82
            LDA 0x80
            DEC A
            STA 0x80
            CMP #1
            JNZ mul_loop

            LDA 0x82
            STA 0x81      ; result = temp_product
            JMP fact_loop

        done:
            LDA 0x81
            STA 0x8F      ; final factorial in 0x8F
            HLT
        """
        # Let's test a cleaner, simpler multiply subroutine
        code_sub = """
        .ORG 0x00
        start:
            LDA #1
            STA 0x81      ; result = 1
            LDA #4
            STA 0x80      ; N = 4
        loop:
            LDA 0x80
            CMP #1
            JZ done
            ; Call multiply: result = result * N
            LDA 0x81
            STA 0x90      ; param X = result
            LDA 0x80
            STA 0x91      ; param Y = N
            CALL multiply
            LDA 0x92      ; ret val
            STA 0x81      ; result = product
            LDA 0x80
            DEC A
            STA 0x80      ; N = N - 1
            JMP loop
        done:
            LDA 0x81
            STA 0x8F
            HLT

        ; multiply: 0x92 = 0x90 * 0x91 (X * Y)
        multiply:
            LDA #0
            STA 0x92      ; product = 0
            LDA 0x91
            STA 0x93      ; count = Y
        mul_step:
            LDA 0x93
            CMP #0
            JZ mul_ret
            LDA 0x92
            LDB 0x90
            ADD B
            STA 0x92
            LDA 0x93
            DEC A
            STA 0x93
            JMP mul_step
        mul_ret:
            RET
        """
        self.cpu.load_program(assemble(code_sub))
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.ram[0x8F], 24)


class TestMiniCCompiler(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU8Bit()

    def test_c_fibonacci(self):
        c_code = """
        void main() {
            int a = 0;
            int b = 1;
            int n = 5;
            while (n > 0) {
                int t = a + b;
                a = b;
                b = t;
                n = n - 1;
            }
            print_num(a);
        }
        """
        from c_compiler import compile_c
        asm_code = compile_c(c_code)
        binary = assemble(asm_code)
        self.cpu.load_program(binary)
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.io_output, ['5'])

    def test_c_array_sum(self):
        c_code = """
        int nums[3];
        void main() {
            nums[0] = 15;
            nums[1] = 25;
            nums[2] = 10;
            int sum = 0;
            int i = 0;
            while (i < 3) {
                sum = sum + nums[i];
                i = i + 1;
            }
            print_num(sum);
        }
        """
        from c_compiler import compile_c
        asm_code = compile_c(c_code)
        binary = assemble(asm_code)
        self.cpu.load_program(binary)
        self.cpu.run(debug=False)
        self.assertEqual(self.cpu.io_output, ['50'])


if __name__ == "__main__":
    unittest.main()
