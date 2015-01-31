
# (C) 2014-2015 Andrew Vaught
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Intermediate representation nodes

import sys

from kw import constant, type_node

from kw import type_void, type_float4, type_float8, type_int8, type_int4
from kw import type_int2, type_int1, type_uint8, type_uint4, type_uint2
from kw import type_uint1, type_float8_2, type_float4_4, type_int8_2
from kw import type_int4_4, type_int2_8, type_int1_16


class parse_error(Exception):
    pass


# ir_nodes are expressions, labels and jumps linked together in a
# double linked list.  The links are through the 'next' and 'prev'
# members.

class ir_node:

# remove()-- Remove this node from the linked list.

    def remove(self):
        if self.next is not None:
            self.next.prev = self.prev
            pass

        if self.prev is not None:
            self.prev.next = self.next
            pass

        return


# insert_next()-- Insert a node after this one.

    def insert_next(self, node):
        if self.next is not None:
            self.next.prev = node
            pass

        node.next = self.next
        node.prev = self

        self.next = node
        return


# insert_prev()-- Insert a node previous to this one.

    def insert_prev(self, node):
        if self.prev is not None:
            self.prev.next = node
            pass

        node.next = self
        node.prev = self.prev

        self.prev = node
        return


    def successor(self):
        return [] if self.next is None else [ self.next ]


    def predecessor(self):
        if self.prev is None or \
               (isinstance(self.prev, jump) and self.prev.cond is None):
            return []

        return [ self.prev ]

    pass


# jumps represent control transfers to other nodes.  The target is the
# 'label' member.  If 'cond' is non-None, then it must be an
# expression.  The branch is taken if the expression is true.

class jump(ir_node):
    def __init__(self, label, cond=None):
        self.label = label
        self.cond = cond

        label.jumps.append(self)
        return


    def show(self):
        print 'jump %s' % self.label.name,

        if self.cond is not None:
            print '  cond=',
            self.cond.show()
            pass

        return


    def successor(self):
        if self.cond is None:
            return [ self.label ]

        return [ self.label ] + ir_node.successor(self)


    def replace_vars(self, repl):
        if self.cond in repl:
            self.cond = repl[self.cond]

        else:
            self.cond.replace_vars(repl)
            pass

        return

    pass


# Labels are jump targets in the code.  They have a string 'name'.
# The 'jumps' member is a list of jump nodes that jump to this label,
# conditionally or unconditionally.

class label(ir_node):
    def __init__(self, name):
        self.name = name
        self.defined = False
        self.jumps = []
        self.phi_list = []
        return

    def show(self):
        print '%s (%d):' % (self.name, len(self.jumps)),
        for p in self.phi_list:
            p.show()
            sys.stdout.write('  ')
            pass

        return

    def predecessor(self):
        return ir_node.predecessor(self) + self.jumps

    pass



def get_temp_label(index=[0]):
    index[0] += 1
    return label('L.%d' % index[0])


class variable:
    def __init__(self, name, var_type, initial=None,
                 q_static=None, q_extern=None):

        assert(isinstance(var_type, type_node))

        self.name = name
        self.type = var_type

        self.q_static = q_static
        self.q_extern = q_extern
        self.initial = initial

        if var_type.basic_type is type_void:
            raise parse_error, 'Variable cannot have a void type'

        return

    def show(self, show_initial=False):
        print self.name,

        if show_initial and self.initial is not None:
            print '= ',
            self.initial.show()
            pass

        return

    def simplify(self):
        return self

    def replace_vars(self, repl):
        return

    def used_vars(self, result):
        result[self] = True
        return

# next_variant()-- Return the next variant on the base variable.  The
# variants don't have the c or stack members.  The variant is
# automatically put on the stack.

    def next_variant(self):
        self.c += 1

        v = variable('%s.%d' % ( self.name, self.c ), self.type)
        self.stack.append(v)
        return v

    pass


class phi:
    def __init__(self, var):
        self.var = var
        self.lhs = None
        self.args = []
        return

    def show(self):
        arglist = ', '.join([ a.var.name for a in self.args ])
        print '%s = phi(%s)' % ( self.lhs.name, arglist ),
        return

    pass


# Phi arguments consist of variable instances and the statement node
# that the control associated with that variable comes from.

class phi_arg:
    def __init__(self, var, node):
        self.var = var
        self.node = node
        return

    pass




# Expressions are assignment statements and other binary/unary
# expressions.

class expr(ir_node):
    def jump_opcode(self):
        return 'jnz'

    pass


# Sub-classes of expressions

class expr_assign(expr):
    def __init__(self, *args):
        self.var, self.value = args
        return


    def show(self):
        self.var.show()
        sys.stdout.write(' = ')
        self.value.show()
        return


    def simplify(self):
        self.var = self.var.simplify()
        self.value = self.value.simplify()
        return self


    def used_vars(self, result):
        result[self.var] = True
        self.value.used_vars(result)
        return


    def replace_vars(self, repl):
        if self.value in repl:
            self.value = repl[self.value]

        else:
            self.value.replace_vars(repl)
            pass

        return

    pass


# swaps always have variables for arguments, they are produced
# deep in the phi-merging code.

class swap(expr):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        return

    def show(self):
        sys.stdout.write('swap ')
        self.a.show()
        sys.stdout.write(', ')
        self.b.show()
        return

    pass


class expr_ternary(expr):
    def __init__(self, *args):
        self.predicate, self.a, self.b = args
        return

    def show(self):
        self.predicate.show()
        sys.stdout.write(' ? ')
        self.a.show()
        sys.stdout.write(' : ')
        self.b.show()
        return

    def simplify(self):
        if not isinstance(self.predicate, constant):
            return self

        self.a.simplify()
        self.b.simplify()
        return self.a if self.predicate.value else self.b

    def used_vars(self, result):
        self.predicate.used_vars(result)
        self.predicate.a(result)
        self.predicate.b(result)
        return


    def replace_vars(self, repl):
        if self.predicate in repl:
            self.predicate = repl[self.predicate]

        else:
            self.predicate.replace_vars(repl)
            pass

        if self.a in repl:
            self.a = repl[self.a]

        else:
            self.a.replace_vars(repl)
            pass

        if self.b in repl:
            self.b = repl[self.b]

        else:
            self.b.replace_vars(repl)
            pass

        return

    pass


#########################

binary_type_map = {}
bitwise_type_map = {}
logical_type_map = {}

def init_btm():
    btm = binary_type_map

    for t in [ type_float8, type_float4, type_int8, type_int4, type_int2,
               type_int1, type_uint8, type_uint4, type_uint2, type_uint1 ]:
        btm[type_float8_2, t] = type_float8_2
        btm[type_float4_4, t] = type_float4_4
        btm[type_float8, t] = type_float8
        pass

    tlist = [ type_float4, type_uint8, type_int8, type_uint4, type_int4,
              type_uint2, type_int2, type_uint1, type_int1 ]

    while len(tlist) > 0:
        t1 = tlist.pop(0)
        btm[t1, t1] = t1

        for t2 in tlist:
            btm[t1, t2] = t1
            pass

        pass

    for t1, t2 in btm.keys():
        btm[t2, t1] = btm[t1, t2]
        pass

    btm = bitwise_type_map

    tlist = [ type_uint8, type_int8, type_uint4, type_int4,
              type_uint2, type_int2, type_uint1, type_int1 ]

    while len(tlist) > 0:
        t1 = tlist.pop(0)
        btm[t1, t1] = t1
        logical_type_map[t1, t1] = type_int4

        for t2 in tlist:
            btm[t1, t2] = t1
            logical_type_map[t1, t2] = type_int4
            pass

        pass

    for t1, t2 in btm.keys():
        btm[t2, t1] = btm[t1, t2]
        logical_type_map[t2, t1] = type_int4
        pass

    return

init_btm()


class expr_binary(expr):

    type_map = { '+': binary_type_map, '-': binary_type_map,
                 '*': binary_type_map, '/': binary_type_map,
                 '%': binary_type_map,

                 '>>': bitwise_type_map, '<<': bitwise_type_map,
                 '&':  bitwise_type_map, '^':  bitwise_type_map,
                 '|':  bitwise_type_map,

                 '&&': logical_type_map, '||': logical_type_map,
                 '==': logical_type_map, '!=': logical_type_map,
                 '<=': logical_type_map, '<':  logical_type_map,
                 '>=': logical_type_map, '>':  logical_type_map,
               }

    def __init__(self, *args):
        self.a, self.b = args

# Keep constants typeless.

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return

        if isinstance(self.a, constant):
            self.type = self.b.type
            return

        if isinstance(self.b, constant):
            self.type = self.a.type
            return

        ta = self.a.type.basic_type
        tb = self.b.type.basic_type

        try:
            self.type = type_node(self.type_map[self.op][ta, tb], 0)

        except KeyError:
            msg = 'Operator "%s" cannot use arguments %s/%s' % \
                  (self.op, ta.name, tb.name)
            raise parse_error, msg

        if self.type.basic_type != ta:
            self.a = expr_type_conv(self.type, self.a)
            pass

        if self.type.basic_type != tb:
            self.b = expr_type_conv(self.type, self.b)
            pass

        return


    def show(self):
        self.a.show()
        sys.stdout.write(self.op)
        self.b.show()
        return


    def used_vars(self, result):
        self.a.used_vars(result)
        self.b.used_vars(result)
        return


    def replace_vars(self, repl):
        if self.a in repl:
            self.a = repl[self.a]

        else:
            self.a.replace_vars(repl)
            pass

        if self.b in repl:
            self.b = repl[self.b]

        else:
            self.b.replace_vars(repl)
            pass

        return


class expr_mult(expr_binary):
    op = '*'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant):
            if self.a.value == 0:
                return constant(0, self.a.type)

            if self.a.value == 1:
                return self.b

            if self.a.value == -1:
                return expr_uminus(self.b).simplify()

            pass

        if isinstance(self.b, constant):
            if self.b.value == 0:
                return constant(0, self.b.type)

            if self.b.value == 1:
                return self.a

            if self.b.value == -1:
                return expr_uminus(self.a).simplify()

            pass

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value + self.b.value, self.a.type)

        return self

    pass


class expr_quotient(expr_binary):
    op = '/'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant):
            if self.a.value == 0:
                return constant(0, self.a.type)

            pass

        if isinstance(self.b, constant):
            if self.b.value == 1:
                return self.a

            if self.b.value == -1:
                return expr_uminus(self.a).simplify()

            pass

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value / self.b.value, self.a.type)

        return self

    pass


class expr_modulus(expr_binary):
    op = '%'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value % self.b.value, self.a.type)

        return self

    pass


class expr_plus(expr_binary):
    op = '+'
    arith_op = 'add'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and self.a.value == 0:
            return self.b

        if isinstance(self.b, constant) and self.b.value == 0:
            return self.a

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value + self.b.value, self.a.type)

        return self

    pass


class expr_minus(expr_binary):
    op = '-'
    arith_op = 'sub'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and self.a.value == 0:
            return expr_uminus(self.b).simplify()

        if isinstance(self.b, constant) and self.b.value == 0:
            return self.a

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value - self.b.value, self.a.type)

        return self

    pass


class expr_lshift(expr_binary):
    op = '<<'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value << self.b.value, self.a.type)

        return self

    pass


class expr_rshift(expr_binary):
    op = '>>'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value >> self.b.value, self.a.type)

        return self

    pass


class expr_bitwise_and(expr_binary):
    op = '&'
    arith_op = 'and'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value & self.b.value, self.a.type)

        return self

    pass


class expr_bitwise_xor(expr_binary):
    op = '^'
    arith_op = 'xor'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value ^ self.b.value, self.a.type)

        return self

    pass


class expr_bitwise_or(expr_binary):
    op = '|'
    arith_op = 'or'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value | self.b.value, self.a.type)

        return self

    pass


class expr_logical_and(expr_binary):
    op = '&&'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and self.a.value != 0:
            return self.b

        return self

    pass


class expr_logical_or(expr_binary):
    op = '||'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant):
            return self.b if self.a.value == 0 else constant(1, self.a.type)

        return self

    pass


class expr_compare(expr_binary):

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            a = self.value.a
            b = self.value.b

            if self.op == '==':
                rc = 1 if a == b else 0

            elif self.op == '<':
                rc = 1 if a < b else 0

            elif self.op == '<=':
                rc = 1 if a <= b else 0

            elif self.op == '>':
                rc = 1 if a > b else 0

            elif self.op == '<=':
                rc = 1 if a >= b else 0

            else:
                raise SystemExit, 'expr_compare.simplify(): Bad operator'

            return constant(rc, type_node(type_int4, 0))

        return self

    pass



class expr_equal(expr_compare):
    op = '=='

    def jump_opcode(self):
        return 'je'
    
    pass

class expr_not_equal(expr_compare):
    op = '!='

    def jump_opcode(self):
        return 'jne'
    
    pass

class expr_less(expr_compare):
    op = '<'

    def jump_opcode(self):
        return 'jlt'

    pass

class expr_less_equal(expr_compare):
    op = '<='

    def jump_opcode(self):
        return 'jle'

    pass

class expr_greater(expr_compare):
    op = '>'

    def jump_opcode(self):
        return 'jgt'

    pass

class expr_greater_equal(expr_compare):
    op = '>='

    def jump_opcode(self):
        return 'jge'

    pass


opposite_cond = {
    expr_equal:          expr_not_equal,
    expr_not_equal:      expr_equal,
    expr_less:           expr_greater_equal,
    expr_less_equal:     expr_greater,
    expr_greater:        expr_less_equal,
    expr_greater_equal:  expr_less,
}



################

class expr_unary(expr):
    def __init__(self, arg):
        self.arg = arg
        self.type = arg.type
        return


    def show(self):
        sys.stdout.write(self.op)
        sys.stdout.write('(')
        self.arg.show()
        sys.stdout.write(')')
        return


    def used_vars(self, result):
        self.arg.used_vars(result)
        return


    def replace_vars(self, repl):
        if self.arg in repl:
            self.arg = repl[self.arg]

        else:
            self.arg.replace_vars(repl)
            pass

        return

    pass


class expr_uplus(expr_unary):
    op = '+'

    def simplify(self):
        self.arg.simplify()
        return self.arg

    pass


class expr_uminus(expr_unary):
    op = '-'
    arith_op = 'neg'

    def simplify(self):
        self.arg = self.arg.simplify()

        if isinstance(self.arg, expr_uminus):
            return self.arg.arg

        if not isinstance(self.arg, constant):
            return self

        self.arg.value *= -1
        return self.arg

    pass


class expr_load(expr_unary):
    op = '*'

    def simplify(self):
        self.arg = self.arg.simplify()
        return self

    pass


class expr_logical_not(expr_unary):
    op = '!'

    def simplify(self):
        self.arg = a = self.arg.simplify()
        if isinstance(a, expr_compare):
            return opposite_cond[a.__class__](a.a, a.b)

        return self

    pass


class expr_paren(expr_unary):

    def show(self):
        sys.stdout.write('(')
        self.arg.show()
        sys.stdout.write(')')
        return


    def simplify(self):
        return self.arg.simplify()

    pass



class expr_intrinsic(expr):
    def __init__(self, *args):
        self.name, self.arg = args
        return

    def show(self):
        sys.stdout.write(self.name + '(')
        self.arg.show()
        sys.stdout.write(')')
        return

    def used_vars(self, result):
        self.arg.used_vars(result)
        return

    def replace_vars(self, repl):
        if self.arg in repl:
            self.arg = repl[self.arg]

        else:
            self.arg.replace_vars(repl)
            pass

        return

    pass


class expr_type_conv(expr_intrinsic):
    def __init__(self, type_decl, arg):
        self.type = type_decl
        self.arg = arg
        return

    def show(self):
        sys.stdout.write('type_' + self.type.basic_type.name + '(')
        self.arg.show()
        sys.stdout.write(')')
        return

    def simplify(self):
        self.arg = self.arg.simplify()

        if not isinstance(self.arg, constant):
            return self

        self.arg.type = self.type
        return self.arg

    pass


# invert_condition()-- Invert the condition, simplifying.

def invert_condition(e):
    e = expr_logical_not(e)
    return e.simplify()



### Machine registers

class register:
    def __str__(self):
        return self.name

    pass


# Constants like reg_a represent the rax register, the sub-registers
# are the ones actually used inside insn nodes.  The 'name' member is
# the name that shows up on the assembler output.

class integer_subreg(register):
    memory = False

    def __init__(self, name):
        self.name = '%' + name
        return

    pass


class integer_register(register):
    def __init__(self, n64, n32, n16, n8):
        r8 = integer_subreg(n64)
        r4 = integer_subreg(n32)
        r2 = integer_subreg(n16)
        r1 = integer_subreg(n8)

        self.map = { type_int1: r1, type_uint1: r1,
                     type_int2: r2, type_uint2: r2,
                     type_int4: r4, type_uint4: r4,
                     type_int8: r8, type_uint8: r8, }

        for v in [ r1, r2, r4, r8 ]:
            v.parent = self
            pass

        return

    def get_subreg(self, t):
        return self.map[type_uint8] if t.level > 0 else self.map[t.basic_type]

    pass

reg_a = integer_register('rax', 'eax', 'ax', 'al')
reg_b = integer_register('rbx', 'ebx', 'bx', 'bl')
reg_c = integer_register('rcx', 'ecx', 'cx', 'cl')
reg_d = integer_register('rdx', 'edx', 'dx', 'dl')

reg_src  = integer_register('rsi', 'esi', 'si', 'sil')
reg_dst  = integer_register('rdi', 'edi', 'di', 'dil')
reg_base = integer_register('rbp', 'ebp', 'bp', 'bpl')

reg_8  = integer_register('r8', 'r8d', 'r8l', 'r8b')
reg_9  = integer_register('r9', 'r9d', 'r9l', 'r9b')
reg_10 = integer_register('r10', 'r10d', 'r10l', 'r10b')
reg_11 = integer_register('r11', 'r11d', 'r11l', 'r11b')
reg_12 = integer_register('r12', 'r12d', 'r12l', 'r12b')
reg_13 = integer_register('r13', 'r13d', 'r13l', 'r13b')
reg_14 = integer_register('r14', 'r14d', 'r14l', 'r14b')
reg_15 = integer_register('r15', 'r15d', 'r15l', 'r15b')

integer_regs = [ reg_a, reg_b, reg_c, reg_d, reg_src, reg_dst, reg_base,
                 reg_8, reg_9, reg_10, reg_11, reg_12, reg_13, reg_14, reg_15 ]

class xmm_register(register):
    mem = False

    def __init__(self, name):
        self.name = name
        return

    pass

xmm0 = xmm_register('xmm0')
xmm1 = xmm_register('xmm1')
xmm2 = xmm_register('xmm2')
xmm3 = xmm_register('xmm3')
xmm4 = xmm_register('xmm4')
xmm5 = xmm_register('xmm5')
xmm6 = xmm_register('xmm6')
xmm7 = xmm_register('xmm7')

xmm8 = xmm_register('xmm8')
xmm9 = xmm_register('xmm9')
xmm10 = xmm_register('xmm10')
xmm11 = xmm_register('xmm11')
xmm12 = xmm_register('xmm12')
xmm13 = xmm_register('xmm13')
xmm14 = xmm_register('xmm14')
xmm15 = xmm_register('xmm15')

xmm_regs = [ xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7,
             xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15 ]


# Memory registers are regular registers that happen to map to memory
# instead of a cpu register.

class memory(register):
    mem = True

    def __init__(self, n):
        self.n = n
        return

    pass


def get_memory_register(count=[0]):
    count[0] += 1
    return memory(count[0])


# number_st()-- Utility for show_flowgraph that assigns statement
# numbers to ir_nodes.

def number_st(graph):
    n = 0
    st = graph
    while st is not None:
        st.n = n
        n = n + 1
        st = st.next
        pass

    return


# show_flowgraph()-- Show the flow graph.  This subroutine is capable
# of show nodes at several different stages of compilation.

def show_flowgraph(graph):
    number_st(graph)
    st = graph

    while st is not None:
        if hasattr(st, 'live'):
            print 'Live:', ', '.join([ v.name for v in st.live ])
            pass

        if hasattr(st, 'dom'):
            d = -1 if st.dom is None else st.dom.n
            print '%3d  (%3d) ' % (st.n, d),
            pass

        if hasattr(st, 'DF'):
            df = ', '.join([ str(x.n) for x in st.DF ])
            print '[ %-15s ]' % df,
            pass

        n = 2 if isinstance(st, label) else 8
        sys.stdout.write(n*' ')
        st.show()

        print
        st = st.next
        pass

    return

