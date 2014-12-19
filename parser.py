#!/usr/bin/env python

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


##### Parser

from kw import *

import lexer
import sys


class parse_error(Exception):
    pass



class variable:
    def __init__(self, name, var_type, initial=None,
                 q_static=None, q_extern=None):
        self.name = name
        self.type = var_type

        self.q_static = q_static
        self.q_extern = q_extern
        self.initial = initial

        if var_type == type_void:
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

    pass


class procedure:
    def __init__(self, name, decl_type):
        self.name = name
        self.type = decl_type

        self.return_var = None if decl_type is type_void else \
                             variable('.retval', decl_type)

        self.done_label = get_temp_label()
        return


    def show(self):
        print 'Procedure', self.name

        print 'Arglist:',
        args = self.args.values()
        args.sort(cmp=lambda x, y: cmp(x.n, y.n))

        for a in args:
            print '%s %s  ' % (a.type.name, a.name),
            pass

        print
        self.block.show()
        pass

    pass


class jump:
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

    pass


class label:
    def __init__(self, name):
        self.name = name
        self.defined = False
        self.jumps = []
        return


    def show(self):
        print '%s (%d):' % (self.name, len(self.jumps)),
        return

    pass


def get_temp_label(index=[0]):
    index[0] += 1
    return label('L.%d' % index[0])


# Blocks contain variable declarations and statements.  The namespace
# is a dictionary of variables and labels keyed by name.  The body is
# a list of instances, which can be expression instances, label
# instances (user and compiler generated) and jumps (conditional or
# not).

class block:
    def __init__(self, parent):
        self.namespace = {}
        self.body = []
        self.parent = parent
        return


    def show(self, indent=0):
        ns = self.namespace.values()
        ns.sort(cmp=lambda x, y: cmp(x.name, y.name))

        print 4*indent*' ' + '{',

        for sym in ns:
            if isinstance(sym, label):
                continue

            print sym.type.name,
            sym.show(True)
            print ';',
            pass

        print
        indent = indent + 1

        for st in self.body:
            if st is None:
                continue

            if isinstance(st, block):
                st.show(indent)

            else:
                print 4*indent*' ',
                st.show()

                if not isinstance(st, label):
                    print ';',
                    pass

                print
                pass

            pass

        indent = indent - 1
        print 4*indent*' ' + '}'
        return


# flatten()-- Return a body list, expanding block instances into other
# statements, filtering out the Nones.

    def flatten(self):
        result = []

        for st in self.body:
            if isinstance(st, block):
                result += st.flatten()

            elif st is not None:
                result.append(st)
                pass

            pass

        return result


# flatten0()-- Top level flattening.  The recursive version returns a
# list.  We take the list, link things together through a 'next'
# member and return the entry node.

    def flatten0(self):
        result = self.flatten()

        prev = None
        for st in result:
            if prev is not None:
                prev.next = st
                pass

            pass

        st.next = None
        return result[0]

    pass



class expr:
    pass



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

    pass



#########################

class expr_binary(expr):
    def __init__(self, *args):
        self.a, self.b = args
        return


    def show(self):
        self.a.show()
        sys.stdout.write(self.op)
        self.b.show()
        return

    pass



class expr_mult(expr_binary):
    op = '*'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant):
            if self.a.value == 0:
                return constant(0)

            if self.a.value == 1:
                return self.b

            if self.a.value == -1:
                return expr_uminus(self.b).simplify()

            pass

        if isinstance(self.b, constant):
            if self.b.value == 0:
                return constant(0)

            if self.b.value == 1:
                return self.a

            if self.b.value == -1:
                return expr_uminus(self.a).simplify()

            pass

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value + self.b.value)

        return self

    pass


class expr_quotient(expr_binary):
    op = '/'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant):
            if self.a.value == 0:
                return constant(0)

            pass

        if isinstance(self.b, constant):
            if self.b.value == 1:
                return self.a

            if self.b.value == -1:
                return expr_uminus(self.a).simplify()

            pass

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value / self.b.value)

        return self

    pass


class expr_modulus(expr_binary):
    op = '%'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value % self.b.value)

        return self

    pass


class expr_plus(expr_binary):
    op = '+'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and self.a.value == 0:
            return self.b

        if isinstance(self.b, constant) and self.b.value == 0:
            return self.a

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value + self.b.value)

        return self

    pass


class expr_minus(expr_binary):
    op = '-'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and self.a.value == 0:
            return expr_uminus(self.b).simplify()

        if isinstance(self.b, constant) and self.b.value == 0:
            return self.a

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value - self.b.value)

        return self

    pass


class expr_lshift(expr_binary):
    op = '<<'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value << self.b.value)

        return self

    pass


class expr_rshift(expr_binary):
    op = '>>'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value >> self.b.value)

        return self

    pass


class expr_bitwise_and(expr_binary):
    op = '&'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value & self.b.value)

        return self

    pass


class expr_bitwise_xor(expr_binary):
    op = '^'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value ^ self.b.value)

        return self

    pass


class expr_bitwise_or(expr_binary):
    op = '|'

    def simplify(self):
        self.a = self.a.simplify()
        self.b = self.b.simplify()

        if isinstance(self.a, constant) and isinstance(self.b, constant):
            return constant(self.a.value | self.b.value)

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
            return self.b if self.a.value == 0 else constant(1)

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

            return constant(rc)

        return self

    pass



class expr_equal(expr_compare):
    op = '=='
    pass

class expr_not_equal(expr_compare):
    op = '!='
    pass

class expr_less(expr_compare):
    op = '<'
    pass

class expr_less_equal(expr_compare):
    op = '<='
    pass

class expr_greater(expr_compare):
    op = '>'
    pass

class expr_greater_equal(expr_compare):
    op = '>='
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
        return

    def show(self):
        sys.stdout.write(self.op)
        self.arg.show()
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

    pass


# invert_condition()-- Invert the condition, simplifying.

def invert_condition(e):
    e = expr_logical_not(e)
    return e.simplify()



# Statement classes

class stmt_if:
    def __init__(self, expr, main_clause, else_clause):
        self.expr = expr
        self.main_clause = main_clause
        self.expr_clause = expr_clause
        return

    pass


class stmt_for:
    def __init__(self, initial, cont, final, body):
        self.initial = initial
        self.cont = cont
        self.final = final
        self.body = body
        return

    pass


class stmt_do:
    def __init__(self, body, cond):
        self.body = body
        self.cond = cond
        return

    pass



# Main parser

class parser:

    def error(self, msg):
        self.lexer.error(msg)
        pass


# find_symbol()-- Try to find a symbol, looking in parent block,
# finally the argument list.  Returns None if not found.

    def find_symbol(self, name, search_args=True):
        b = self.current_block
        while b is not None:
            if name in b.namespace:
                return b.namespace[name]

            b = b.parent
            pass

        if not search_args:
            return None

        return self.current_proc.args.get(name, None)

### Expression parsers.  The numbers are the standard C precedence levels.

    def parse_expr_1(self):
        t = self.lexer.next_token()

        if isinstance(t, word):
            sym = self.find_symbol(t.name)
            if sym is None:
                raise parse_error, "Symbol '%s' not declared" % t.name

            return sym

        if isinstance(t, constant):
            return t

        if t == tok_lparen:
            e = expr_paren(self.parse_expr())

            if not self.lexer.peek_token(tok_rparen):
                raise parse_error, 'Missing right paren'

            return e

        if isinstance(t, intrinsic_name):
            if not self.lexer.peek_token(tok_lparen):
                raise parse_error, 'Missing left paren'

            e = self.parse_expr()

            if not self.lexer.peek_token(tok_rparen):
                raise parse_error, 'Missing right paren'

            return expr_intrinsic(t.name, e)

        raise parse_error, 'Syntax error in expression'


    def parse_expr_2(self):
        t = self.lexer.next_token()

        try:
            cons = {
                tok_plus: expr_uplus,  tok_minus:       expr_uminus,
                tok_star: expr_load,   tok_logical_not: expr_logical_not }[t]

            e = cons(self.parse_expr_2())

        except KeyError:
            self.lexer.push(t)
            e = self.parse_expr_1()
            pass

        return e


    def parse_expr_3(self):
        a = self.parse_expr_2()

        while True:
            t = self.lexer.next_token()

            try:
                cons = {
                    tok_star: expr_mult,  tok_slash: expr_quotient,
                    tok_mod:  expr_modulus,  }[t]

            except KeyError:
                break

            a = cons(a, self.parse_expr_2())
            pass

        self.lexer.push(t)
        return a


    def parse_expr_4(self):
        a = self.parse_expr_3()

        while True:
            t = self.lexer.next_token()

            try:
                cons = {
                    tok_plus: expr_plus,  tok_minus: expr_minus }[t]

            except KeyError:
                break

            a = cons(a, self.parse_expr_3())
            pass

        self.lexer.push(t)
        return a


    def parse_expr_5(self):
        a = self.parse_expr_4()

        while True:
            t = self.lexer.next_token()

            try:
                cons = {
                    tok_lshift: expr_lshift,  tok_rshift: expr_rshift }[t]

            except KeyError:
                break

            a = cons(a, self.parse_expr_4())
            pass

        self.lexer.push(t)
        return a


    def parse_expr_6(self):
        a = self.parse_expr_5()

        while True:
            t = self.lexer.next_token()

            try:
                cons = {
                    tok_greater:     expr_greater,
                    tok_greater_eq:  expr_greater_equal,
                    tok_less:        expr_less,
                    tok_less_eq:     expr_less_equal }[t]

            except KeyError:
                break

            a = cons(a, self.parse_expr_5())
            pass

        self.lexer.push(t)
        return a


    def parse_expr_7(self):
        a = self.parse_expr_6()

        while True:
            t = self.lexer.next_token()

            try:
                cons = {
                    tok_equal:      expr_equal,
                    tok_not_equal:  expr_not_equal }[t]

            except KeyError:
                break

            a = cons(a, self.parse_expr_6())
            pass

        self.lexer.push(t)
        return a


    def parse_expr_8(self):
        a = self.parse_expr_7()

        while self.lexer.peek_token(tok_bit_and):
            a = expr_bitwise_and(a, self.parse_expr_7())
            pass

        return a


    def parse_expr_9(self):
        a = self.parse_expr_8()

        while self.lexer.peek_token(tok_caret):
            a = expr_bitwise_xor(a, self.parse_expr_8())
            pass

        return a


    def parse_expr_10(self):
        a = self.parse_expr_9()

        while self.lexer.peek_token(tok_bit_or):
            a = expr_bitwise_xor(a, self.parse_expr_9())
            pass

        return a


    def parse_expr_11(self):
        a = self.parse_expr_10()

        while self.lexer.peek_token(tok_logical_and):
            a = expr_logical_and(a, self.parse_expr_10())
            pass

        return a


    def parse_expr_12(self):
        a = self.parse_expr_11()

        while self.lexer.peek_token(tok_logical_or):
            a = expr_logical_or(a, self.parse_expr_11())
            pass

        return a


    def parse_expr_13(self):
        e = self.parse_expr_12()
        if not self.lexer.peek_token(tok_question):
            return e

        a = self.parse_expr_13()

        if not self.lexer.peek_token(tok_colon):
            raise parse_error, 'Missing : after ?'

        b = self.parse_expr_13()
        return expr_ternary(e, a, b)


    def parse_expr_14(self):
        e = self.parse_expr_13()
        while self.lexer.peek_token(tok_assign):
            e = expr_assign(e, self.parse_expr_13())
            pass

        return e


# parse_expr()-- Parse an expression.

    def parse_expr(self):
        e = self.parse_expr_14()
        return e.simplify()


### Statement parsers

    def parse_type_decl(self, decl_type, q_static=False):

        while True:
            n = self.lexer.next_token()
            if not isinstance(n, word):
                raise parser_error, 'Expected name of variable'

            if n.name in self.current_block.namespace:
                raise parse_error, "Multiple declaration of '%s'" % n.name

            if not self.lexer.peek_token(tok_assign):
                s = variable(n.name, decl_type, None, q_static, False)

            else:
                initial = self.parse_expr()

                if q_static:
                    if isinstance(initial, constant):
                        raise parse_error, 'Static initialization must be constant'

                    s = variable(n.name, decl_type, initial, q_static, False)

                else:
                    s = variable(n.name, decl_type, None, q_static, False)

                    e = expr_assign(s, initial)
                    self.current_block.body.append(e)
                    pass

                pass

            self.current_block.namespace[n.name] = s

            t = self.lexer.next_token()
            if t == tok_semi:
                break

            if t != tok_comma:
                raise parse_error, 'Syntax error in variable declaration'

            pass

        return


    def parse_static(self, t):
        t = self.lexer.next_token()
        if not isinstance(t, type_name):
            raise parse_error, 'Expected type name after STATIC'

        self.parse_type_decl(t, True)
        return


    def parse_if(self, t):
        self.lexer.required_token(tok_lparen)
        cond = invert_condition(self.parse_expr())
        self.lexer.required_token(tok_rparen)

        body = self.current_block.body

        a = self.parse_stmt_or_block()
        end_label = get_temp_label()

        if not self.lexer.peek_token(kw_else):
            body.append(jump(end_label, cond))
            body.append(a)
            pass

        else:
            else_label = get_temp_label()
            b = self.parse_stmt_or_block()

            body.append(jump(else_label, cond))
            body.append(a)
            body.append(jump(end_label))
            body.append(else_label)
            body.append(b)
            pass

        body.append(end_label)
        return


    def parse_goto(self, t):
        t = self.lexer.next_token()
        if not isinstance(t, word):
            raise parse_error, 'Expected a label for GOTO'

        sym = self.find_symbol(t.name)

        if sym is None:
            sym = label(t.name)
            self.current_block.namespace[t.name] = sym

        elif not isinstance(sym, label):
            raise parse_error, "Symbol '%s' is not a label" % t.name

        self.lexer.required_token(tok_semi)
        return jump(sym)


# parse_expr_list()-- Parse a list of comma-separated expressions
# given a final token.  Regular C has comma-expressions, but we don't,
# in order to allow tuples.

    def parse_expr_list(self, term):
        result = []

        if self.lexer.peek_token(term):
            return result

        while True:
            result.append(self.parse_expr())
            if self.lexer.peek_token(term):
                break

            if not self.lexer.peek_token(tok_comma):
                raise parse_error, 'Syntax error in expression list'

            pass

        return result


    def parse_while(self, t):
        self.break_save = self.break_label
        self.break_label = get_temp_label()

        self.continue_save = self.continue_label
        self.continue_label = get_temp_label()

        self.lexer.required_token(tok_lparen)
        cond = invert_condition(self.parse_expr())
        self.lexer.required_token(tok_rparen)

        a = self.parse_stmt_or_block()

        body = self.current_block.body

        body.append(self.continue_label)
        body.append(jump(self.break_label, cond))
        body.append(a)
        body.append(jump(self.continue_label))
        body.append(self.break_label)

        self.break_label = self.break_save
        self.continue_label = self.continue_save

        return


    def parse_for(self, t):
        self.lexer.required_token(tok_lparen)

        initial_list = self.parse_expr_list(tok_semi)
        cont_list = self.parse_expr_list(tok_semi)
        final_list = self.parse_expr_list(tok_rparen)

        self.break_save = self.break_label
        self.break_label = get_temp_label()
        self.continue_save = self.continue_label
        self.continue_label = get_temp_label()

        top_label = get_temp_label()

        loop_body = self.parse_stmt_or_block()
        body = self.current_block.body

        for st in initial_list:
            body.append(st)
            pass

        body.append(top_label)

        i = 0
        while i < len(cont_list):
            if i < len(cont_list) - 1:
                st = cont_list[i]

            else:
                st = invert_condition(st)
                st = jump(self.break_label, st)
                pass

            i = i + 1
            pass

        body.append(loop_body)
        body.append(self.continue_label)

        for st in final_list:
            body.append(st)
            pass

        body.append(jump(top_label))
        body.append(self.break_label)

        self.break_label = self.break_save
        self.continue_label = self.continue_save
        return


    def parse_do(self, t):
        self.break_save = self.break_label
        self.break_label = get_temp_label()
        self.continue_save = self.continue_label
        self.continue_label = get_temp_label()

        loop_body = self.parse_stmt_or_block()

        self.lexer.required_token(kw_while)
        self.lexer.required_token(tok_lparen)
        cond = self.parse_expr()
        self.lexer.required_token(tok_rparen)
        self.lexer.required_token(tok_semi)

        body = self.current_block.body

        body.append(self.continue_label)
        body.append(loop_body)

        body.append(jump(self.continue_label, cond))
        body.append(self.break_label)

        self.break_label = self.break_save
        self.continue_label = self.continue_save
        return


    def parse_continue(self, t):
        self.lexer.required_token(tok_semi)

        if self.continue_label is None:
            raise parse_error, 'continue statement outside of loop'

        return jump(self.continue_label)


    def parse_break(self, t):
        self.lexer.required_token(tok_semi);

        if self.break_label is None:
            raise parse_error, 'Break outside of loop/switch'

        return jump(self.break_label)


    def parse_return(self, t):
        body = self.current_block.body
        rv = self.current_proc.return_var

        if self.lexer.peek_token(tok_semi):
            if rv is not None:
                raise parse_error, 'Missing return value'

            pass

        else:
            if rv is None:
                raise parse_error, 'Return has a value in a void function'

            body.append(expr_assign(rv, self.parse_expr()))
            self.lexer.required_token(tok_semi)
            pass

        return jump(self.current_proc.done_label)


    def parse_switch(self, t):
        return

    def parse_case(self, t):
        return

    def parse_default(self, t):
        return


# define_label()-- Define a label, which might already exist.

    def define_label(self, name):
        lbl = self.find_symbol(name)

        if lbl is None:
            lbl = label(name)
            lbl.defined = True
            self.current_block.namespace[name] = lbl
            return lbl

        if not isinstance(lbl, label):
            raise parse_error, 'Label name already defined as non-label'

        if lbl.defined:
            raise parse_error, 'Duplicate label'

        lbl.defined = True
        return lbl


# parse_statement()-- Parse a statement, which is an assignemnt or
# keyword statement.

    def parse_statement(self):
        t = self.lexer.next_token()
        if t in self.parse_map:
            return self.parse_map[t](t)

        if isinstance(t, word):
            u = self.lexer.next_token()
            if u == tok_colon:
                return self.define_label(t.name)

            self.lexer.push(u)
            pass

        self.lexer.push(t)
        e = self.parse_expr()

        if self.lexer.next_token() != tok_semi:
            raise parse_error, 'Expected semicolon after expression'

        return e


# parse_block()-- Parse a block of program statements and
# declarations.  The left brace has already been seen.

    def parse_block(self):
        b = block(self.current_block)
        self.current_block = b

        while not self.lexer.peek_token(tok_rbrace):
            st = self.parse_statement()
            if st is not None:
                b.body.append(st)
                pass

            pass

        if b.parent is None:
            b.body.append(self.current_proc.done_label)
            pass

        self.current_block = b.parent
        return b


# parse_stmt_or_block()-- Parse a single statement, or one contained
# in a block.  Returns a statement structure, or a list of statements.

    def parse_stmt_or_block(self):
        return self.parse_block() if self.lexer.peek_token(tok_lbrace) else \
               self.parse_statement()


# parse_dummy_arglist()-- Parse a dummy argument list.  The initial
# left paren has alrady been seen.
#   '(' [ <type> <name> [ , <type> <name> ] ] ')'

    def parse_dummy_arglist(self):
        if self.lexer.peek_token(tok_rparen):
            return []

        n = 0
        args = {}

        while True:
            t = self.lexer.next_token()
            if not isinstance(t, type_name):
                raise parse_error, 'Expected type name in argument list'

            decl_type = t

            w = self.lexer.next_token()
            if not isinstance(w, word):
                raise parse_error, 'Expected dummy variable name'

            name = w.name
            if name in args:
                raise parse_error, "Duplicate dummy argument '%s'" % name

            v = variable(name, decl_type)
            v.n = n
            n = n + 1

            args[name] = v

            t = self.lexer.next_token()
            if t == tok_rparen:
                break

            if t != tok_comma:
                raise parse_error, 'Syntax error in dummy argument list'

            pass

        return args


# parse_procedure()-- Parse a procedure.

    def parse_procedure(self, decl_type, name):
        self.current_proc = procedure(name, decl_type)

        if name in self.global_namespace:
            raise parse_error, "Name '%s' already declared" % name

        self.global_namespace[name] = self.current_proc
        self.current_proc.args = self.parse_dummy_arglist()

        t = self.lexer.next_token()
        if t != tok_lbrace:
            raise parse_error, 'Expected left brace in function'

        self.current_block = None
        self.current_proc.block = self.parse_block()

        return


# parse_global_var_decl()-- Parse a global variable declaration.
# We've already got part of the first one on entry.

    def parse_global_var_decl(self, q_static, q_extern, decl_type, name, t):

        while True:
            initial = None if t != tok_assign else self.parse_expr()

            if name in self.global_namespace:
                raise parse_error, "Name '%s' already declared" % name

            s = variable(name, decl_type, initial, q_static, q_extern)
            self.global_namespace[name] = s

            t = self.lexer.next_token()
            if t == tok_semi:
                break

            if t != tok_comma:
                raise parse_error, 'Syntax error in variable declaration'

            name = self.lexer.next_token()

            if not isinstance(name, word):
                raise parse_error, 'Expected name in variable declaration'

            t = self.lexer.next_token()
            pass

        return


# parse_global_var_or_proc()-- A global variable or a procedure.  This
# is either
#   [ qualifier ] <type> <name> [ = <expr> ] [ , <name> [ = expr ] ] ';'
#   [ qualifier ] <type> <name> '(' [ arglist ] ')' '{' <proc body> '}'

    def parse_global_var_or_proc(self):
        q_static = False
        q_extern = False

        while True:
            t = self.lexer.next_token()

            if t == kw_extern:
                if q_extern:
                    raise parse_error, 'Duplicate extern declaration'

                q_extern = True
                continue

            if t == kw_static:
                if q_static:
                    raise parse_error, 'Duplicate static declaration'

                q_static = True
                continue

            break

        if not isinstance(t, type_name):
            raise parse_error, 'Missing type name'

        decl_type = t

        name = self.lexer.next_token()

        if not isinstance(name, word):
            raise parse_error, 'Missing name'

# Now we can actually figure out what we have.

        t = self.lexer.next_token()

        if t == tok_assign or t == tok_semi:
            self.parse_global_var_decl(q_static, q_extern, decl_type, name.name, t)

        elif t != tok_lparen:
            raise parse_error, 'Syntax error, expected left paren'

        elif q_extern:
            raise parse_error, 'EXTERN declaration not allowed for procedure'

        elif q_static:
            raise parse_error, 'STATIC declaration not allowed for procedure'

        else:
            self.parse_procedure(decl_type, name)
            pass

        return


    def show(self):
        print 'Global namespace:'

        for k, v in self.global_namespace.items():
            v.show()
            pass

        return


    def __init__(self, filename):
        self.lexer = lexer.lexer(filename)
        self.global_namespace = {}
        self.current_block = None

        self.break_label = None
        self.continue_label = None

        self.parse_map = {
            kw_static:    self.parse_static,    kw_return:  self.parse_return,
            kw_for:       self.parse_for,       kw_do:      self.parse_do,
            kw_if:        self.parse_if,        kw_while:   self.parse_while,
            kw_goto:      self.parse_goto,      kw_break:   self.parse_break,
            kw_continue:  self.parse_continue,  kw_switch:  self.parse_switch,
            kw_case:      self.parse_case,      kw_default: self.parse_default,
        }

        for t in type_names:
            self.parse_map[t] = self.parse_type_decl
            pass

        try:
            while not self.lexer.peek_token(tok_eof):
                self.parse_global_var_or_proc()
                pass

            pass

        except (lexer.lex_error, parse_error), msg:
            self.error(msg)
            pass

        return

    pass



def show_proclist(st_list):
    for st in st_list:
        sys.stdout.write(5*' ')
        st.show()
        print
        pass

    return



# label_optimize()-- Label-related optimizations, mostly just to get
# them out of the way.

def label_optimize(seq):

    i = 0
    while i < len(seq):
        if not isinstance(seq[i], label):
            i = i + 1
            continue

        if len(seq[i].jumps) == 0:  # Remove never used labels
            del seq[i]
            continue

        if (i >= len(seq) - 1) or (not isinstance(seq[i+1], label)):
            i = i + 1
            continue

# Replace two adjacent labels with a single label.
            
        for j in seq[i+1].jumps:
            j.label = seq[i]
            pass

        del seq[i+1]
        pass

    return


# jump_optimize()-- Optimize jumps in a code block.

def jump_optimize(seq):

    i = 0
    while i < len(seq)-2:
        j1 = seq[i]           # Optimize jumps around other jumps
        j2 = seq[i+1]
        lbl = seq[i+2]

        if isinstance(j1, jump) and (j1.cond is not None) and \
           isinstance(j2, jump) and (j2.cond is None) and \
           isinstance(lbl, label) and (j1.label is lbl):

            lbl.jumps.remove(j1)
            if len(lbl.jumps) == 0:
                del seq[i+2]
                pass

            j1.label = j2.label
            j1.cond = invert_condition(j1.cond)

            j2.label.jumps.remove(j2)
            j2.label.jumps.append(j1)

            del seq[i+1]
            continue

        if isinstance(j1, jump):   # Optimize jumps to unconditional jumps
            n = seq.index(j1.label) + 1
            if n < len(seq):
                j3 = seq[n]
                if isinstance(j3, jump) and j3.cond is None:
                    j1.label.jumps.remove(j1)

                    j1.label = j3.label
                    j1.label.jumps.append(j1)
                    pass
                    
                pass

        i = i + 1
        pass

    return


# remove_dead_code()-- Remove statements following unconditional
# jumps, until the next label.

def remove_dead_code(seq):

    i = 0
    while i < len(seq):
        jmp = seq[i]

        if (not isinstance(jmp, jump)) or (jmp.cond is not None):
            i = i + 1
            continue

        i = i + 1
        while i < len(seq):
            if isinstance(seq[i], label):
                break

            del seq[i]
            pass

        pass

    return





import sys

if len(sys.argv) < 2:
    raise SystemExit, 'No filename'

p = parser(sys.argv[1])

for v in p.global_namespace.values():
    if not isinstance(v, procedure):
        continue

    print 'Procedure'

    seq = v.block.flatten0()

    label_optimize(seq)
    jump_optimize(seq)
    label_optimize(seq)
    remove_dead_code(seq)

    show_proclist(seq)
    print
    pass

