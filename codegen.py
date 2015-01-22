
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

from ir_nodes import expr_assign, expr_binary, expr_unary, expr_compare, label
from ir_nodes import jump, integer_subreg, memory, variable, opposite_cond
from ir_nodes import expr_unary, swap

from ir_nodes import expr_equal, expr_not_equal, expr_less
from ir_nodes import expr_less_equal, expr_greater, expr_greater_equal


from kw import constant

from kw import type_void, type_float4, type_float8, type_int8, type_int4
from kw import type_int2, type_int1, type_uint8, type_uint4, type_uint2
from kw import type_uint1, type_float8_2, type_float4_4, type_int8_2
from kw import type_int4_4, type_int2_8, type_int1_16



def signed_type(t):
    return t.basic_type in [ type_int8, type_int4, type_int2, type_int1 ]


# Convert an expr_compare instance to assembler mnemonics.

signed_jump_map = {
    expr_equal:          'je',
    expr_not_equal:      'jne',
    expr_less:           'jlt',
    expr_less_equal:     'jle',
    expr_greater:        'jgt',
    expr_greater_equal:  'jge' }

unsigned_jump_map = {
    expr_equal:          'je',
    expr_not_equal:      'jne',
    expr_less:           'jb',
    expr_less_equal:     'jbe',
    expr_greater:        'ja',
    expr_greater_equal:  'jae' }


def convert_jump(cond, signed):
    cond_map = signed_jump_map if signed else unsigned_jump_map
    return cond_map[cond]


signed_set_map = {
    expr_equal:          'sete',
    expr_not_equal:      'setne',
    expr_less:           'setlt',
    expr_less_equal:     'setle',
    expr_greater:        'setgt',
    expr_greater_equal:  'setge' }

unsigned_set_map = {
    expr_equal:          'sete',
    expr_not_equal:      'setne',
    expr_less:           'setb',
    expr_less_equal:     'setbe',
    expr_greater:        'seta',
    expr_greater_equal:  'setae' }


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



s1 = [ 'cmp @2, @1' ]
s2 = [ 'cmp @1, @2' ]
s3 = [ 'mov @1, @t', 'cmp @t, @2' ]

cmp_map = { 1: s2,  2: s2,  3: s1,  4: s2,
            5: s3,  6: s2,  7: s1,  8: s1, }
    
del s1, s2, s3


# classify_cmp()-- Classify a comparison expression.  Because
# constants can only be on one side of the compare, we sometimes have
# to reverse the caller's sense of comparison.

def classify_cmp(y, z):
    temp_type = y.type

    if not isinstance(y, constant):
        y = y.register
        pass

    if not isinstance(z, constant):
        z = z.register
        pass

    if isinstance(y, integer_subreg):
        if isinstance(z, integer_subreg):
            case = 1      #  r1 cmp r2
            reverse = False

        elif isinstance(z, memory):
            case = 2      #  r1 cmp m1
            reverse = False

        elif isinstance(z, constant):
            case = 3      #  r1 cmp c1
            reverse = False

        else:
            raise RuntimeError, 'classify_cmp()-- Bad case 1'

        pass

    elif isinstance(y, memory):
        if isinstance(z, integer_subreg):
            case = 4      #  m1 cmp r1
            reverse = False

        elif isinstance(z, memory):
            case = 5      #  m1 cmp m2
            reverse = False

        elif isinstance(z, constant):
            case = 6      #  m1 cmp c1
            reverse = False

        else:
            raise RuntimeError, 'classify_cmp()-- Bad case 2'

        pass

    elif isinstance(y, constant):
        if isinstance(z, integer_subreg):
            case = 7      # c1 cmp r1
            reverse = True

        elif isinstance(z, memory):
            case = 8      # c1 cmp m1
            reverse = True

        else:
            raise RuntimeError, 'classify_cmp()-- Base case 3'

        pass

    else:
        raise RuntimeError, 'classify_cmp()-- Base case 4'

    repl = { '@t': get_temp_reg(temp_type), '@1': y, '@2': z }

    insn_list = [ replace_insn(i, repl) for i in cmp_map[case] ]
    return reverse, insn_list



s1 = [ 'sub @1, @3' ]
s2 = [ 'sub @1, @3', 'neg @1' ]
s3 = [ 'mov @2, @1', 'sub @1, @3' ]

subtract_seq = {
    1: s1,
    2: s2,
    3: s3 }


###


s1  = [ 'op @2, @1' ]
s2  = [ 'op @1, @2' ]
s3  = [ 'mov @2, @1', 'op @3, @1' ]
s4  = [ 'op @3, @1' ]
s5  = [ 'mov @3, @1', 'op @2, @1' ]
s6  = [ 'op @3, @2', 'mov @2, @1' ]
s7  = [ 'op @2, @3', 'mov @3, @1' ]
s8  = [ 'mov @2, @t', 'op @3, @t', 'mov @t, @1' ]
s9  = [ 'mov @3, @t', 'op @t, @1' ]
s10 = [ 'mov @2, @t', 'op @t, @1' ]

commutative_seq = {
    1: s1,  2: s2,   3: s3,   4: s1,   5: s2,   6: s4,   7: s3,
    8: s1,  9: s5,  10: s3,  11: s3,  12: s1,  13: s5,  14: s3,

    15: s6,   16: s7,  17: s8,  18: s1,  19: s6,  20: s8,
    21: s6,   22: s8,  23: s4,  24: s6,  25: s8,  26: s9,
    27: s10,  28: s8,  29: s7,  30: s8,  31: s1,  32: s8, }

del s1, s2, s3, s4, s5, s6, s7, s8, s9, s10



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



s1 = [ 'op $2' ]
s2 = [ 'mov $2, $1', 'op $1' ]
s3 = [ 'op $2', 'mov $2, $1' ]
s4 = [ 'mov $2, $t', 'op $t', 'mov $t, $1' ]

unary_seq = {
    1: s1,  2: s2,  3: s2,  4: s3,
    5: s4,  6: s1,  7: s4 }

del s1, s2, s3, s4


# classify_unary()-- Classify a unary expression.  Way, way fewer
# cases than classify_binary().  We have x = op y

def classify_unary(st):

    x = st.var
    y = st.value.arg

    if not isinstance(x, constant):
        x = x.register
        pass

    if not isinstance(y, constant):
        y = y.register
        pass

    y_dead = True

    for n in st.successor():
        y_dead = y_dead and y in n.live
        pass

    if isinstance(x, integer_subreg):
        if isinstance(y, integer_subreg):
            if x is y:
                case = 1  # r1 = op r1

            else:
                case = 2  # r1 = op r2
                pass

            pass

        elif isinstance(y, memory_subreg):
            case = 3      # r1 = op m1

        else:
            raise RuntimeError, 'classify_unary(): Bad case 1'

        pass

    elif isinstance(x, memory):
        if isinstance(y, integer_subreg):
            if y_dead:
                case = 4  # m1 = op r1,  r1 dead

            else:
                case = 5  # m1 = op r1,  r1 remains live
                pass

            pass

        elif isinstance(y, memory_subreg):
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

    return case, x, y


def insn_unary(st):
    case, x, y = classify_unary(st)

    repl = { '@t': get_temp_reg(st.var.type), 'op': st.value.arith_op,
             '$1': str(x), '$2': str(y) }

    return [ replace_insn(i, repl) for i in unary_seq[case] ]


# predicate_insn()-- Treat the expression as a predicate.  We return
# the predicate and a list of instructions.  If the expression is a
# comparison, we generate the instructions for the compare and return
# the predicate (which might be different than the original
# expression).  If the predicate is not a comparison, then the
# comparsion is with zero.

def predicate_insn(st):
    if isinstance(st, expr_compare):
        reverse, insn_list = classify_cmp(st.a, st.b)
        signed = signed_type(st.a.type) or signed_type(st.b.type)
        cond = st

    else:
        reverse, insn_list = classify_cmp(st, constant('0', st.type))
        cond = expr_not_equal
        signed = True
        pass

    if reverse:
        cond = opposite_cond[cond]
        pass

    return cond, signed, insn_list


# The real object-oriented method would be to have methods on ir_nodes
# that generate instructions.  Going that way ends up with all the
# code generation in ir_nodes, which means a huge file.


# insn_assign()-- Generate assembler from an assignment statement.

def insn_assign(st):

    if isinstance(st.value, expr_compare):
        reverse, r = classify_cmp(st.value.a, st.value.b)

        signed = signed_type(st.value.a.type) and signed_type(st.value.b.type)
        cond_map = signed_set_map if signed else unsigned_set_map

        cond = st.value.__class__
        if reverse:
            cond = opposite_cond[cond]
            pass

        insn = '%s %s' % (cond_map[cond], st.var.register)
        r.append(insn)

    elif isinstance(st.value, expr_binary):
        repl = { '@1': st.var, '@2': st.value.a, '@3': st.value.b,
                 '@t': get_temp_reg(st.value.type),
                 'op': st.value.arith_op }

        case = classify_binary(st)
        r = [ replace_insn(i, repl) for i in commutative_seq[case] ]
            
    elif isinstance(st.value, expr_unary):
        r = insn_unary(st)

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


def insn_swap(st):
    r1 = self.a.register
    r2 = self.b.register

    if (not isinstance(r1, memory)) or (not isinstance(r2, memory)):
        return [ 'xchg %s, %s' % (r1, r2) ]

# memory/memory exchange

    temp = get_temp_reg(self.r1.type)

    return [ 'mov %s, %s' % (r1, temp), 'xchg %s, %s' % (temp, r2),
             'mov %s, %s' % (temp, r2) ]


def insn_jump(st):
    if st.cond is None:
        result = []
        op = 'jmp'

    else:
        cond, signed, result = predicate_insn(st.cond)
        op = convert_jump(cond.__class__, signed)
        pass

    result.append('%s %s' % (op, st.label.name))
    return result


def generate_assembler(graph):
    insn_list = []
    st = graph

    while st is not None:
        indent = True

        if isinstance(st, expr_assign):
            insns = insn_assign(st)

        elif isinstance(st, jump):
            insns = insn_jump(st)

        elif isinstance(st, label):
            insns = [ st.name + ':' ]
            indent = False

        elif isinstance(st, swap):
            insns = insn_swap(st)

        else:
            raise RuntimeError, 'generate_assembler: Bad instruction'

        if indent:
            insns = [ '\t' + insn for insn in insns ]
            pass

        insn_list.extend(insns)
        st = st.next
        pass

    for insn in insn_list:
        print insn
        pass

    return

