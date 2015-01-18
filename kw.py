

# (C) 2014 Andrew Vaught
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

import sys


# Definitions of keywords, tokens, intrinsics, etc.

class token:
    def __init__(self, name):
        self.name = name
        return

    def __str__(self):
        return 'TOKEN(%s)' % self.name

    pass


class constant:
    def __init__(self, value, decl_type):
        self.value = value
        self.type = decl_type
        return

    def __str__(self):
        return str(self.value)

    def show(self):
        sys.stdout.write(str(self.value))
        return

    def simplify(self):
        return self

    def used_vars(self, result):
        return

    def replace_vars(self, repl):
        return

    pass


class word:
    def __init__(self, name):
        self.name = name
        return

    def __str__(self):
        return 'WORD(%s)' % self.name

    pass


class keyword:
    def __init__(self, name):
        self.name = name
        return

    def __str__(self):
        return 'KEYWORD(%s)' % self.name

    pass


class type_name:
    def __init__(self, name):
        self.name = name
        return

    def __str__(self):
        return 'TYPENAME(%s)' % self.name

    pass


class type_node:
    def __init__(self, basic_type, level=0):
        self.basic_type = basic_type
        self.level = level
        return


    def __cmp__(self, other):
        assert(isinstance(other, type_node))

        if self.basic_type is other.basic_type:
            return 0

        return 1

    pass


class intrinsic_name:
    def __init__(self, name):
        self.name = name
        return

    def __str__(self):
        return 'INTRINSIC(%s)' % self.name

    pass


# Tokens

tok_equal = token('==')
tok_not_equal = token('!=')
tok_greater = token('>')
tok_greater_eq = token('>=')
tok_less = token('<')
tok_less_eq = token('<=')
tok_logical_and = token('&&')
tok_logical_or = token('||')
tok_lshift = token('<<')
tok_rshift = token('>>')

tok_logical_not = token('!')
tok_assign = token('=')

tok_bit_and = token('&')
tok_bit_or = token('|')
tok_bit_not = token('~')

tok_plus = token('+')
tok_minus = token('-')
tok_star = token('*')
tok_slash = token('/')
tok_mod = token('%')
tok_not = token('~')

tok_dot = token('.')
tok_comma = token(',')
tok_question = token('?')
tok_colon = token(':')
tok_semi = token(';')
tok_caret = token('^')

tok_lbrace = token('{')
tok_rbrace = token('}')

tok_lparen = token('(')
tok_rparen = token(')')

tok_eof = token('EOF')   # Doesn't go in token_list


token_list = [
    tok_assign, tok_equal, tok_not_equal, tok_greater, tok_greater_eq,
    tok_less, tok_less_eq, tok_bit_and, tok_bit_or, tok_logical_and,
    tok_logical_or, tok_logical_not, tok_plus, tok_minus, tok_star,
    tok_slash, tok_mod, tok_bit_not, tok_logical_not, tok_dot,
    tok_comma, tok_question, tok_colon, tok_semi, tok_caret,
    tok_lshift, tok_rshift, tok_lbrace, tok_rbrace, tok_lparen,
    tok_rparen, ]

# Keywords

kw_static = keyword('static')
kw_extern = keyword('extern')

kw_if = keyword('if')
kw_else = keyword('else')
kw_return = keyword('return')
kw_goto = keyword('goto')
kw_for = keyword('for')
kw_do = keyword('do')
kw_while = keyword('while')
kw_break = keyword('break')
kw_continue = keyword('continue')
kw_switch = keyword('switch')
kw_default = keyword('default')
kw_case = keyword('case')


keyword_list = [
    kw_static, kw_extern, kw_return, kw_for, kw_do, kw_if, kw_else,
    kw_while, kw_goto, kw_break, kw_continue, kw_switch, kw_case,
    kw_default, ]

# Type names

type_void = type_name('void')

type_float4 = type_name('float4')
type_float8 = type_name('float8')

type_int8 = type_name('int8')
type_int4 = type_name('int4')
type_int2 = type_name('int2')
type_int1 = type_name('int1')

type_uint8 = type_name('uint8')
type_uint4 = type_name('uint4')
type_uint2 = type_name('uint2')
type_uint1 = type_name('uint1')

type_float8_2 = type_name('float8_2')
type_float4_4 = type_name('float4_4')

type_int8_2 = type_name('int8_2')
type_int4_4 = type_name('int4_4')
type_int2_8 = type_name('int2_8')
type_int1_16 = type_name('int1_16')

type_names = [
    type_void, type_float4, type_float8,
    type_int8, type_int4, type_int2, type_int1,
    type_uint8, type_uint4, type_uint2, type_uint1,
    type_float8_2,type_float4_4,
    type_int8_2, type_int4_4, type_int2_8, type_int1_16 ]


# Intrinsics

intr_sqrt = intrinsic_name('sqrt')
intr_sum = intrinsic_name('sum')
intr_abs = intrinsic_name('abs')
intr_min = intrinsic_name('min')
intr_max = intrinsic_name('max')

intrinsic_names = [ intr_sqrt, intr_sum, intr_abs, intr_min, intr_max, ]

