""" CPU FUNCTIONALITY """

import sys
from datetime import datetime #Used for timer interrupt


#OpCodes
ADD  = 0b10100000
AND  = 0b10101000
CALL = 0b01010000
CMP  = 0b10100111
DEC  = 0b01100110
DIV  = 0b10100011
HLT  = 0b00000001
INC  = 0b01100101
IRET = 0b00010011
JEQ  = 0b01010101
JLE  = 0b01011001
JLT  = 0b01011000
JMP  = 0b01010100
JNE  = 0b01010110
LD   = 0b10000011
LDI  = 0b10000010
MUL  = 0b10100010
OR   = 0b10101010
POP  = 0b01000110
PRA  = 0b01001000
PRN  = 0b01000111
PUSH = 0b01000101
RET  = 0b00010001
SHL  = 0b10101100
ST   = 0b10000100
SUB  = 0b10100001
XOR  = 0b10101011

# Reserved general-purpose register numbers:
IM = 5
IS = 6
SP = 7

# CMP flags:
FL_LT = 0b100
FL_GT = 0b010
FL_EQ = 0b001

# IS flags
IS_TIMER    = 0b00000001
IS_KEYBOARD = 0b00000010


class CPU:
    """Main CPU class"""

    def __init__(self):
        """Construct a new CPU"""

        self.pc = 0 #Program Counter
        self.fl = 0 #Flags
        self.ie = 1 #Interrupts (on/off)

        self.halted = False #CPU is running
        self.last_interrupt = None

        self.ir_has_set_pc = False #Changes if instruction sets Program Counter
        

        self.ram = [0] * 256 #Initialize random access memory at 256 bytes
        self.reg = [0] * 8 #Initialize an 8 Bit Registry
        self.reg[SP] = 0xf4 #Set the Special registry location

        self.branch_table = {
            ADD: self.op_add,
            AND: self.op_and,
           CALL: self.op_call,
            CMP: self.op_cmp,
            DEC: self.op_dec,
            DIV: self.op_div,
            HLT: self.op_hlt,
            INC: self.op_inc,
           IRET: self.op_iret,
            JEQ: self.op_jeq,
            JLE: self.op_jle,
            JLT: self.op_jlt,
            JMP: self.op_jmp,
            JNE: self.op_jne,
             LD: self.op_ld,
            LDI: self.op_ldi,
            MUL: self.op_mul,
             OR: self.op_or,
            POP: self.op_pop,
            PRA: self.op_pra,
            PRN: self.op_prn,
           PUSH: self.op_push,
            RET: self.op_ret,
            SHL: self.op_shl,
             ST: self.op_st,
            SUB: self.op_sub,
            XOR: self.op_xor,

        }

    def ram_write(self, mdr, mar):
        self.ram[mar] = mdr

    def ram_read(self, mar):
        return self.ram[mar]

    def push_value(self, value):
        self.reg[SP] -= 1
        self.ram_write(value, self.reg[7])


    def pop_value(self):
        value = self.ram_read(self.reg[7])
        self.reg[SP] += 1
        return value


    def check_timer_interrupt(self):
        """"Check the time to see if a timer interrupt should fire"""
        if self.last_interrupt == None:
            self.last_interrupt = datetime.now()

        now = datetime.now()

        difference = now - self.last_interrupt

        if difference.seconds >= 1: #Fire
            self.last_interrupt = now
            self.reg[IS] |= IS_TIMER


    def handle_interrupts(self):
        if not self.ie: # If they are not enabled
            return
        
        #Mask out interrupts

        masked_interrupts = self.reg[IM] & self.reg[IS]

        for i in range(8):
            #If interrupt has been triggered
            if masked_interrupts & (1<< i):
                self.ie = 0 #Disable Interrupts
                self.reg[IS] &= ~(1 << i) #Clear a bit for the interrupt

                #Save the work on the stack
                self.push_value(self.pc)
                self.push_value(self.fl)
                for regBit in range(7):
                    self.push_value(self.reg[regBit])

                #Determine and jump to the address vector
                self.pc = self.ram_read(0xf8 + i)

                break


    def load(self, program):
        """Loads a program from disk into memory"""

        address = 0
        with open(program) as x:
            for line in x:
                comment_split = line.split("#")
                num = comment_split[0].strip()
                if num == '': #Ignore the blanks
                    continue
                val = int(num, 2)

                self.ram[address] = val
                address +=1




    def alu(self, op, reg_a, reg_b):

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        elif op == "AND":
            self.reg[reg_a] &= self.reg[reg_b]
        elif op == "SUB":
            self.reg[reg_a] -= self.reg[reg_b]
        elif op == "MUL":
            self.reg[reg_a] *= self.reg[reg_b]
        elif op == "DIV":
            self.reg[reg_a] /= self.reg[reg_b]
        elif op == "DEC":
            self.reg[reg_a] -= 1
        elif op == "INC":
            self.reg[reg_a] += 1
        elif op == "CMP":
            self.fl &= 0x11111000  # clear all CMP flags
            if self.reg[reg_a] < self.reg[reg_b]:
                self.fl |= FL_LT
            elif self.reg[reg_a] > self.reg[reg_b]:
                self.fl |= FL_GT
            else:
                self.fl |= FL_EQ
        elif op == "OR":
            self.reg[reg_a] |= self.reg[reg_b]
        elif op == "SHL":
            self.reg[reg_a] <<= self.reg[reg_b]
        elif op == "XOR":
            self.reg[reg_a] ^= self.reg[reg_b]
        else:
            raise Exception("Unsupported ALU operation")

    def trace(self, ir, operand_a, operand_b):
        print("\n=============TRACE============")
     
     
        print("     PC | IR | FL | IE | PC +1 +2")
        print(f"HEX: %02X | %02X | %02X |  %d | %02X  %02X  %02X |" % (
            self.pc,
            ir,
            self.fl,
            self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')
        print("\n")
        print(f"BIN: %02d | %02d | %02d | %02d | %02d  %02d  %02d |" % (
            self.pc,
            ir,
            self.fl,
            self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')

        # print(f"TRACE: %02X | %02X | %d | %02X %02X %02X |" % (
        #     self.pc,
        #     self.fl,
        #     self.ie,
        #     self.ram_read(self.pc),
        #     self.ram_read(self.pc + 1),
        #     self.ram_read(self.pc + 2)
        # ), end='')
        print("\n")
        print("Register Contents")
        print("HEX | INT")

        for i in range(8):            
            print(" %02X" % self.reg[i], end=' | ')
            print("%03d" % self.reg[i], end='\n')
        print("\n")
        print("==============================\n")
        print()

    def run(self):
        """Run the CPU"""
        
        while not self.halted:
            # Add Interrupt Code
            self.check_timer_interrupt()
            self.handle_interrupts()

            ir = self.ram[self.pc] #Set Instruction Register = the number in ram at an index == program counter
            #Set our opperands to be the two next numbers in ram after the ir
            operand_a = self.ram_read(self.pc + 1)
            operand_b = self.ram_read(self.pc + 2)

            inst_size = ((ir >> 6) & 0b11) + 1
            self.inst_set_pc = ((ir >> 4) & 0b1) == 1

            self.trace(ir, operand_a, operand_b)
            if ir in self.branch_table:
                self.branch_table[ir](operand_a, operand_b)
                
                
                
            else:
                raise Exception(f"Invalid Instruction IR: {ir} HEX: {hex(ir)} at address {hex(self.pc)}")
            
            if not self.inst_set_pc:
                self.pc += inst_size


    def op_ldi(self, operand_a, operand_b):
        
        self.reg[operand_a] = operand_b

    def op_prn(self, operand_a, operand_b):
        print(self.reg[operand_a])

    def op_pra(self, operand_a, operand_b):
        print(chr(self.reg[operand_a]), end='')
        sys.stdout.flush()

    def op_add(self, operand_a, operand_b):
        self.alu("ADD", operand_a, operand_b)

    def op_and(self, operand_a, operand_b):
        self.alu("AND", operand_a, operand_b)

    def op_sub(self, operand_a, operand_b):
        self.alu("SUB", operand_a, operand_b)

    def op_mul(self, operand_a, operand_b):
        self.alu("MUL", operand_a, operand_b)

    def op_div(self, operand_a, operand_b):
        self.alu("DIV", operand_a, operand_b)

    def op_dec(self, operand_a, operand_b):
        self.alu("DEC", operand_a, None)

    def op_inc(self, operand_a, operand_b):
        self.alu("INC", operand_a, None)

    def op_or(self, operand_a, operand_b):
        self.alu("OR", operand_a, operand_b)

    def op_xor(self, operand_a, operand_b):
        self.alu("XOR", operand_a, operand_b)

    def op_pop(self, operand_a, operand_b):
        self.reg[operand_a] = self.pop_value()

    def op_push(self, operand_a, operand_b):
        self.push_value(self.reg[operand_a])

    def op_call(self, operand_a, operand_b):
        self.push_value(self.pc + 2)
        self.pc = self.reg[operand_a]

    def op_ret(self, operand_a, operand_b):
        self.pc = self.pop_value()

    def op_ld(self, operand_a, operand_b):
        self.reg[operand_a] = self.ram_read(self.reg[operand_b])

    def op_shl(self, operand_a, operand_b):
        self.alu("SHL", operand_a, operand_b)

    def op_st(self, operand_a, operand_b):
        self.ram_write(self.reg[operand_b], self.reg[operand_a])

    def op_jmp(self, operand_a, operand_b):
        self.pc = self.reg[operand_a]
                
    def op_jeq(self, operand_a, operand_b):
        if self.fl & FL_EQ:
            self.pc = self.reg[operand_a]
        else:
            self.inst_set_pc = False

    def op_jle(self, operand_a, operand_b):
        if self.fl & FL_LT or self.fl & FL_EQ:
            self.pc = self.reg[operand_a]
        else:
            self.inst_set_pc = False

    def op_jlt(self, operand_a, operand_b):
        if self.fl & FL_LT:
            self.pc = self.reg[operand_a]
        else:
            self.inst_set_pc = False

    def op_jne(self, operand_a, operand_b):
        if not self.fl & FL_EQ:
            self.pc = self.reg[operand_a]
        else:
            self.inst_set_pc = False

    def op_cmp(self, operand_a, operand_b):
        self.alu("CMP", operand_a, operand_b)

    def op_iret(self, operand_a, operand_b):
        # restore work from stack
        for i in range(6, -1, -1):
            self.reg[i] = self.pop_value()
        self.fl = self.pop_value()
        self.pc = self.pop_value()

        # enable interrupts
        self.ie = 1

    def op_hlt(self, operand_a, operand_b):
        self.halted = True



