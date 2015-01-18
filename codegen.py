
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

import string

from ir_nodes import expr_assign, expr_binary, expr_unary, expr_compare
from ir_nodes import integer_subreg, memory, variable

from kw import constant

from kw import type_void, type_float4, type_float8, type_int8, type_int4
from kw import type_int2, type_int1, type_uint8, type_uint4, type_uint2
from kw import type_uint1, type_float8_2, type_float4_4, type_int8_2
from kw import type_int4_4, type_int2_8, type_int1_16


invert_jmp = {
    'je': 'jne',    'jne': 'je',
    'jz': 'jnz',    'jnz': 'jz',

    'jb': 'jae',    'jae': 'jb',
    'ja': 'jbe',    'jbe': 'ja',

    'jg': 'jle',    'jle': 'jg',
    'jl': 'jge',    'jge': 'jl',  }


# get_temp_reg()-- Given a type node, return the designated temporary
# register.

def get_temp_reg(t):
    if t.level > 0:
        return '%rax'

    bt = t.basic_type

    if bt in [ type_float4, type_float8, type_float8_2, type_float4_4,
               type_int8_2, type_int4_4, type_int2_8, type_int1_16 ]:
        return '%xmm0'

    if bt in [ type_int8, type_uint8 ]:
        return '%rax'

    if bt in [ type_int4, type_uint4 ]:
        return '%eax'

    if bt in [ type_int2, type_uint2 ]:
        return '%ax'

    if bt in [ type_int1, type_uint1 ]:
        return '%al'

    raise RuntimeError, 'get_temp_reg(): Bad type'


def replace_insn(insn, repl):
    for k, v in repl.items():
        if isinstance(v, variable):
            v = v.register
            pass

        insn = string.replace(insn, k, str(v))
        pass

    return insn




s1  = [ 'op $2, $1' ]
s2  = [ 'op $1, $2' ]
s3  = [ 'mov $2, $1', 'op $3, $1' ]
s4  = [ 'op $3, $1' ]
s5  = [ 'mov $3, $1', 'op $2, $1' ]
s6  = [ 'op $3, $2', 'mov $2, $1' ]
s7  = [ 'op $2, $3', 'mov $3, $1' ]
s8  = [ 'mov $2, $t', 'op $3, $t', 'mov $t, $1' ]
s9  = [ 'mov $3, $t', 'op $t, $1' ]
s10 = [ 'mov $2, $t', 'op $t, $1' ]

commutative_seq = {
    1: s1,  2: s2,   3: s3,   4: s1,   5: s2,   6: s4,   7: s3,
    8: s1,  9: s5,  10: s3,  11: s3,  12: s1,  13: s5,  14: s3,

    15: s6,   16: s7,  17: s8,  18: s1,  19: s6,  20: s8,
    21: s6,   22: s8,  23: s4,  24: s6,  25: s8,  26: s9,
    27: s10,  28: s8,  29: s7,  30: s8,  31: s1,  32: s8, }

del s1, s2, s3, s4, s5, s6, s7, s8, s9, s10


s1 = [ 'sub $1, $3' ]
s2 = [ 'sub $1, $3', 'neg $1' ]
s3 = [ 'mov $2, $1', 'sub $1, $3' ]



subtract_seq = {
    1: s1,
    2: s2,
    3: s3,

    }




# classify_binary()-- Classify a binary assignment node.  This
# classification determines what kind of assembler is generated.  The
# expression is an SSA style triple
#
#     x = y op z
#
# x can be a memory or register.  y and z can be register, memory or
# constant.  y and z cannot both be constants.  x might be equivalent
# to y and/or z.  In some cases, it matters whether y and z are dead
# after this instruction.  Returns a number, which is used to dispatch
# somewhere in the caller.

def classify_binary(st):

    x = st.var.register

    y = st.value.a
    if not isinstance(y, constant):
        y = y.register
        pass

    z = st.value.b
    if not isinstance(z, constant):
        z = z.register
        pass

    y_dead = True
    z_dead = True

    for n in st.successor():
        y_dead = y_dead and y in n.live
        z_dead = z_dead and z in n.live
        pass

# For sanity the comparison sequence is always integer_subreg, memory,
# constant, x is y/z, dead y/z.

    if isinstance(x, integer_subreg):
        if isinstance(y, integer_subreg):
            if isinstance(z, integer_subreg):
                if x is y:
                    case = 1    # r1 = r1 op r2

                elif x is z:
                    case = 2    # r1 = r2 op r1

                else:
                    case = 3    # r1 = r2 op r3
                    pass

                pass

            elif isinstance(z, memory):
                if x is y:
                    case = 4    # r1 = r1 op m1

                else:
                    case = 5    # r1 = r2 op m1
                    pass

                pass

            elif isinstance(z, constant):
                if x is y:
                    case = 6    # r1 = r1 op c1

                else:
                    case = 7    # r1 = r2 op c1
                    pass

                pass

            else:
                raise RuntimeError, 'classify_binary(): Bad case 1'

            pass

        elif isinstance(y, memory):
            if isinstance(z, integer_subreg):
                if x is z:
                    case = 8    # r1 = m1 op r1

                else:
                    case = 9    # r1 = m1 op r2
                    pass

                pass

            elif isinstance(z, memory_subreg):
                case = 10       # r1 = m1 op m2

            elif isinstance(z, constant):
                case = 11       # r1 = m1 op c1

            else:
                raise RuntimeError, 'classify_binary(): Bad case 2'

            pass

        elif isinstance(y, constant):
            if isinstance(z, integer_subreg):
                if x is z:
                    case = 12   # r1 = c1 op r1

                else:
                    case = 13   # r1 = c1 op r2
                    pass

                pass

            elif isinstance(z, memory):
                case = 14       # r1 = c1 op m1

            else:
                raise RuntimeError, 'classify_binary(): Base case 3'

            pass

        else:
            raise RuntimeError, 'classify_binary(): Bad case 4'

        pass

    elif isinstance(x, memory):
        if isinstance(y, integer_subreg):
            if isinstance(z, integer_subreg):
                if y_dead:
                    case = 15      # m1 = r1 op r2,  r1 dead

                elif z_dead:
                    case = 16      # m1 = r1 op r2,  r2 dead

                else:
                    case = 17      # m1 = r1 op r2,  r1 & r2 remain live
                    pass

                pass                

            elif isinstance(z, memory):
                if x is z:
                    case = 18       # m1 = r1 op m1

                elif y_dead:
                    case = 19   # m1 = r1 op m2,  r1 dead

                else:
                    case = 20   # m1 = r1 op m2,  r1 remains live
                    pass

                pass

            elif isinstance(z, constant):
                if y_dead:
                    case = 21       # m1 = r1 op c1,  r1 dead

                else:
                    case = 22       # m1 = r1 op c1,  r1 remains live
                    pass

                pass

            else:
                raise RuntimeError, 'classify_binary(): Base case 5'

            pass

        elif isinstance(y, memory):
            if isinstance(z, integer_subreg):
                if x is y:
                    case = 23   # m1 = m1 op r1

                elif z_dead:
                    case = 24   # m1 = m2 op r1,  r1 dead

                else:
                    case = 25   # m1 = m2 op r1,  r1 remains live
                    pass

                pass

            elif isinstance(z, memory):
                if x is y:
                    case = 26   # m1 = m1 op m2

                elif x is z:
                    case = 27   # m1 = m2 op m1

                else:
                    case = 28   # m1 = m2 op m3
                    pass

                pass

            else:
                raise RuntimeError, 'classify_binary(): Bad case 6'

            pass

        elif isinstance(y, constant):
            if isinstance(z, integer_subreg):
                if z_dead:
                    case = 29   # m1 = c1 op r1,  r1 dead

                else:
                    case = 30   # m1 = c1 op r1,  r1 remains live
                    pass

                pass

            elif isinstance(z, memory):
                if x is z:
                    case = 31   # m1 = c1 op m1

                else:
                    case = 32   # m1 = c1 op m2
                    pass

                pass

            else:
                raise RuntimeError, 'classify_binary(): Bad case 7'

            pass

        else:
            raise RuntimeError, 'classif_binary(): Base case 8'

        pass

    else:
        raise RuntimeError, 'classify_binary(): Base case 9'

    return case


# classify_unary()-- Classify a unary expression.  Way, way fewer
# cases than classify_binary().  We have x = op y

def classify_unary(st):

    x = st.var
    y = st.value.arg

    y_dead = True

    for n in st.successor():
        y_dead = y_dead and y in n.live
        pass

    if isinstance(integer_subreg, x):
        if isinstance(integer_subreg, y):
            if x is y:
                case = 1  # r1 = op r1

            else:
                case = 2  # r1 = op r2
                pass

            pass

        elif isinstance(memory_subreg, y):
            case = 3      # r1 = op m1

        else:
            raise RuntimeError, 'classify_unary(): Bad case 1'

        pass

    elif isinstance(memory, x):
        if isinstance(integer_subreg, y):
            if y_dead:
                case = 4  # m1 = op r1,  r1 dead

            else:
                case = 5  # m1 = op r1,  r1 remains live
                pass

            pass

        elif isinstance(memory_subreg, y):
            if x is y:
                case = 6  # m1 = op m1

            else:
                case = 7  # m1 = op m2
                pass

            pass

        else:
            raise RuntimeError, 'classify_unary(): Bad case 2'

        pass

    else:
        raise RuntimeError, 'classify_unary(): Bad case 3'

    return case


# The real object-oriented method would be to have methods on ir_nodes
# that generate instructions.  Going that way ends up with all the
# code generation in ir_nodes, which means a huge file.


# insn_assign()-- Generate assembler from an assignment statement.

def insn_assign(st):
    if isinstance(st.value, expr_binary):
        repl = { '$1': st.var, '$2': st.value.a, '$3': st.value.b,
                 '$t': get_temp_reg(st.value.type),
                 'op': st.value.arith_op }

        case = classify_binary(st)
        r = [ replace_insn(i, repl) for i in commutative_seq[case] ]
            
    elif isinstance(st.value, expr_unary):
        pass

    elif isinstance(st.value, constant):
        r = [ 'mov $%s, %s' % ( st.value.value, st.var.register ) ]

    elif isinstance(st.value, register):
        if isinstance(st.value, memory) and isinstance(st.var, memory):
            t = get_temp_reg(st.value.type)
            r = [ 'mov %s, %s' % (st.value, t), 'mov %s, %s', (t, st.var) ]

        else:
            r = [ 'mov %s, %s' % (st.value, st.var) ]
            pass

        pass

    else:
        raise RuntimeError, 'expr_assign.get_insn(): Bad case'

    return r


def insn_jump(st):
    if st.cond is None:
        result = []
        op = 'jmp'

    else:
        result = self.cond.get_insn(None)
        op = st.cond.jump_opcode()
        pass

    result.append('%s %s' % (op, st.label.name))
    return result


def generate_assembler(graph):
    insn_list = []
    st = graph

    while st is not None:
        if isinstance(st, expr_assign):
            insns = insn_assign(st)

        elif isinstance(st, jump):
            insns = insn_jump(st)

        elif isinstance(st, label):
            insns = [ st.name + ':' ]

        else:
            raise RuntimeError, 'get_omsm'

        insn_list.extend(insns)
        st = st.next
        pass

    for insn in insn_list:
        print insn
        pass

    return

