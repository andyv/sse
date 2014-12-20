

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

# Intermediate representation nodes

import sys

from kw import constant


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


# insert_next()-- Insert a node after this one

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

    pass


# Labels are jump targets in the code.  They have a string 'name'.
# The 'jumps' member is a list of jump nodes that jump to this label,
# conditionally or unconditionally.


class label(ir_node):
    def __init__(self, name):
        self.name = name
        self.defined = False
        self.jumps = []
        return


    def show(self):
        print '%s (%d):' % (self.name, len(self.jumps)),
        return

    pass


# Expressions are assignment statements and other binary/unary
# expressions.

class expr(ir_node):
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

