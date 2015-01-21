
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


from ir_nodes import jump, label, ir_node, expr_assign, expr_binary
from ir_nodes import expr, phi, phi_arg, constant, variable, expr_ternary
from ir_nodes import expr_compare, expr_unary, expr_intrinsic, show_flowgraph

### Subroutines for converting the flow graph to SSA form.


###### Initial IR optimizations


# label_optimize()-- Label-related optimizations, mostly just to get
# them out of the way.

def label_optimize(st):
    temp = ir_node()       # Can't be removed
    st.insert_prev(temp)

    while st is not None:
        next_st = st.next

        if not isinstance(st, label):
            st = next_st
            continue

        if len(st.jumps) == 0:  # Remove never used labels
            st.remove()
            st = next_st
            continue

        if not isinstance(next_st, label):
            st = next_st
            continue

# Replace two adjacent labels with a single label.  st stays the same
# thing so that we can collapse multiple labels.

        for j in next_st.jumps:
            j.label = st
            st.jumps.append(j)
            pass

        next_st.remove()
        pass

    temp.remove()
    return temp.next


# jump_optimize()-- Optimize jumps in a code block.

def jump_optimize(st):
    temp = ir_node()
    st.insert_prev(temp)

# Optimize jumps around other jumps

    j1 = st

    while j1 is not None:
        next_st = j1.next

        if not isinstance(j1, jump):
            j1 = next_st
            continue

        j2 = j1.next
        if j2 is None or (not isinstance(j2, jump)):
            j1 = next_st
            continue

        lbl = j2.next

        if lbl is None or (not isinstance(lbl, label)) or j1.label is not lbl:
            j1 = next_st
            continue

        lbl.jumps.remove(j1)
        if len(lbl.jumps) == 0:
            lbl.remove()
            pass

        j1.label = j2.label
        j1.cond = invert_condition(j1.cond)

        j2.label.jumps.remove(j2)
        j2.label.jumps.append(j1)

        j2.remove()
        pass


# Optimize jumps to unconditional jumps

    j1 = temp.next

    while j1 is not None:
        if not isinstance(j1, jump):
            j1 = j1.next
            continue

        j2 = j1.label.next

        if isinstance(j2, jump) and j2.cond is None:
            j1.label.jumps.remove(j1)

            j1.label = j2.label
            j1.label.jumps.append(j1)
            pass

        j1 = j1.next
        pass

# Remove jumps to labels that immediately follow the jump.

    j1 = temp.next

    while j1 is not None:
        if not isinstance(j1, jump):
            j1 = j1.next
            continue

        lbl = j1.next
        if isinstance(lbl, label) and j1.label is lbl:
            lbl.jumps.remove(j1)
            j1.remove()
            pass

        j1 = lbl
        pass

    temp.remove()
    return temp.next


# remove_dead_code()-- Remove statements following unconditional
# jumps, until the next label.

def remove_dead_code(st):
    temp = ir_node()
    st.insert_prev(temp)

    while st is not None:
        next_st = st.next

        if (not isinstance(st, jump)) or (st.cond is not None):
            st = next_st
            continue

        st = next_st

        while st is not None:
            next_st = st.next
            if isinstance(st, label):
                break

            st.remove()
            st = next_st
            pass

        st = next_st
        pass

    temp.remove()
    return temp.next



# get_temp_var()-- Get a temporary variable of the same type as the
# passed one.

def get_temp_var(var_type, index=[0]):
    index[0] += 1
    return variable('T.%d' % index[0], var_type)


# ssa_expr0()-- Recursive function for expanding an expression node
# into ssa form.  The new assignment statements are inserted prior to
# the st statement.  This is a depth-first traversal.

def ssa_expr0(e, st):

    if isinstance(e, ( constant, variable )):
        pass

    elif isinstance(e, ( expr_binary, expr_compare )):
        ssa_expr0(e.a, st)
        ssa_expr0(e.b, st)

        if not isinstance(e.a, ( constant, variable )):
            t = get_temp_var(e.a.type)
            st.insert_prev(expr_assign(t, e.a))
            e.a = t
            pass

        if not isinstance(e.b, ( constant, variable )):
            t = get_temp_var(e.b.type)
            st.insert_prev(expr_assign(t, e.b))
            e.b = t
            pass

        pass

    elif isinstance(e, expr_assign):
        ssa_expr0(e.value, st)

    elif isinstance(e, expr_ternary):
        e.predicate = ssa_expr0(e.predicate, st)
        e.a = ssa_expr0(e.a, st)
        e.b = ssa_expr0(e.b, st)

    elif isinstance(e, ( expr_unary, expr_intrinsic )):
        ssa_expr0(e.arg, st)

        if not isinstance(e.arg, ( constant, variable )):
            t = get_temp_var(e.arg.type)
            st.insert_prev(expr_assign(t, e.arg))
            e.arg = t
            pass

        pass

    else:
        raise RuntimeError, 'ssa_expr0 Unknown expr type: ' + str(type(e))

    return


# ssa_expr()-- Expand expression nodes into SSA form.

def ssa_expr(st):
    temp = ir_node()
    st.insert_prev(temp)

    while st is not None:
        if isinstance(st, expr):
            ssa_expr0(st, st)

        elif isinstance(st, jump) and st.cond is not None:
            ssa_expr0(st.cond, st)
            pass

        st = st.next
        pass

    temp.remove()
    return temp.next



# Compute the immediate dominators of each node
#
# Node m is said to dominate node n if all paths from entry to n must
# pass through node m.  An immediate dominator is the closest such m
# to n.  The algorithm is given by "A Fast Algorithm for Finding
# Dominators in a Flowgraph", by Lengauer and Tarjan in "ACM
# Transactions on Programming Languages and Systems" v1 n1 July 1979,
# p121-141.
#
# Our implementation is a class that takes the input flowgraph as
# input, creates a bunch of its own auxiliarly data structures,
# determines the tree and then adds members to the flowgraph nodes.
# Arrays in the original paper are implemented as temporary members in
# the original nodes.  After exit, the auxiliary structures vanish
# leaving the augmented flowgraph.

class find_dominators:
    def __init__(self, graph):
        if graph is None:
            return

        self.graph = graph

        st = graph
        while st is not None:
            st.bucket = []
            st.pred = []
            st.semi = 0
            st.ancestor = None
            st.d_label = st
            st.size = 1
            st.child = 0

            st = st.next
            pass

# The vertex dictionary translates vertex number to the vertex, 1-based.

        self.vertex = {}
        self.n = 0
        self.depth_search()

        i = self.n

        while i >= 2:
            w = self.vertex[i]

            for v in w.pred:
                u = self.EVAL(v)
                if u.semi < w.semi:
                    w.semi = u.semi
                    pass

                self.vertex[w.semi].bucket.append(w)
                self.LINK(w.parent, w)

                while w.parent.bucket:
                    v = w.parent.bucket.pop(0)
                    u = self.EVAL(v)

                    v.dom = u if u.semi < v.semi else w.parent
                    pass

                pass

            i = i - 1
            pass

        i = 2
        while i <= self.n:
            w = self.vertex[i]
            if w.dom is not self.vertex[w.semi]:
                w.dom = w.dom.dom
                pass

            i = i + 1
            pass

        self.graph.dom = None

        self.cleanup()
        return


# depth_search()-- Depth search of the flow graph.  Python's default
# recursion limit is 1000 frames, which is not very good long term.
# We instead opt for maintaining a queue of unexplored nodes.  Doing
# it this way doesn't result in a deep stack like a recursive
# depth_search() would.

    def depth_search(self):
        queue = []
        queue.append(self.graph)
        self.graph.parent = None

        while len(queue) > 0:
            v = queue.pop(0)
            self.n += 1

            self.vertex[self.n] = v
            v.semi = self.n

            for w in v.successor():
                if w.semi == 0:
                    w.parent = v
                    queue.append(w)
                    pass

                w.pred.append(v)
                pass

            pass

        return


# compress()-- The compress() function.

    def compress(self, v):
        if v.ancestor.ancestor is None:
            return

        self.compress(v.ancestor)
        if v.ancestor.d_label.semi < v.d_label.semi:
            v.d_label = v.ancestor.d_label
            pass

        v.ancestor = v.ancestor.ancestor
        return


    def EVAL(self, v):
        if v.ancestor is None:
            return v

        self.compress(v)
        return v.d_label


    def LINK(self, v, w):
        w.ancestor = v
        return

# cleanup()-- Remove unneeded members from graph nodes.

    def cleanup(self):
        st = self.graph

        while st is not None:
            del st.parent, st.semi, st.pred, st.bucket, st.d_label
            del st.ancestor, st.size, st.child
            st = st.next
            pass

        return

    pass


# The next few subroutines come from "Efficiently computing static
# single assignment form and the control dependence graph", by Cytron
# et al in "ACM Transactions on Programming Languages and Systems" v13
# n4, October 1991 p451-490.


# dominance_tree()-- Given flowgraph nodes with immediate dominators,
# compute the dominator tree.  The 'children' list contains the list
# of nodes that are dominated by that node.

def dominance_tree(graph):

    st = graph
    while st is not None:
        st.children = []
        st = st.next
        pass

    st = graph
    while st is not None:
        if st.dom is not None:
            st.dom.children.append(st)
            pass

        st = st.next
        pass

    return


# dominance_frontier()-- Recursive function for computing the
# dominance frontier of each node.  The DF is computed via a bottom-up
# traversal of the dominator tree.

def dominance_frontier(x):

    for child in x.children:
        dominance_frontier(child)
        pass

    df = {}   # Dictionary avoids problem with duplicates

    for y in x.successor():
        if y.dom is not x:
            df[y] = True
            pass

        pass

    for z in x.children:
        for y in z.DF:
            if y.dom is not x:
                df[y] = True
                pass

            pass

        pass

    x.DF = df.keys()
    return


# place_phi()-- Place phi functions in the flow graph using the
# dominance frontiers.  Returns a list of variables in use by the
# program.

def place_phi(graph):
    iter_count = 0
    assignments = {}
    variables = {}

    st = graph
    while st is not None:
        st.has_already = 0
        st.work = 0

        if isinstance(st, expr_assign):  # Create assignments map
            if st.var in assignments:
                assignments[st.var].append(st)

            else:
                assignments[st.var] = [ st ]
                pass

            pass

        if isinstance(st, expr):
            st.used_vars(variables)
            pass

        st = st.next
        pass


    variables = variables.keys()

#    print 'Assignments:'
#    for k, v in assignments.items():
#        print 'Variable', k.name, '@', [ st.n for st in v ]
#        pass
#
#    print 'Variables used:', [ v.name for v in variables ]

    w = {}

    for v in variables:
        iter_count += 1
        for x in assignments[v]:
            x.work = iter_count
            w[x] = True
            pass

        while len(w) > 0:
            x = w.popitem()[0]
            for y in x.DF:
                if y.has_already < iter_count:
                    y.phi_list.append(phi(v))
                    y.has_already = iter_count
                    if y.work < iter_count:
                        y.work = iter_count
                        w[y] = True
                        pass

                    pass
                pass
            pass
        pass

    return variables


# replace_vars()-- Top level variable replacement.  Returns the new
# expression or a restructured version.

def replace_vars(e, repl):
    if e in repl:
        return repl[e]

    e.replace_vars(repl)
    return e



# replace_rhs()-- Replace variables in the right side of an
# assignment.

def replace_rhs(e):
    repl = {}
    e.used_vars(repl)

    for v in repl.keys():
        if len(v.stack) > 0:
            repl[v] = v.stack[-1]

        else:
            del repl[v]
            pass

        pass

    return replace_vars(e, repl)


# rename0()-- Recursive function for renaming ssa variables.  The
# recursion follows the dominance tree.

def rename0(st):
    lhs_vars = []

    if isinstance(st, expr_assign):
        st.value = replace_rhs(st.value)

        lhs_vars.append(st.var)      # Process LHS.
        st.var = st.var.next_variant()

# Conditional jumps are like expressions that are computed and never
# assigned.

    elif isinstance(st, jump) and st.cond is not None:
        st.cond = replace_rhs(st.cond)


    elif isinstance(st, label):
        for p in st.phi_list:
            lhs_vars.append(p.var)
            p.lhs = p.var.next_variant()
            pass

        pass

# Deal with nearby phi's

    for y in st.successor():
        if isinstance(y, label):
            for p in y.phi_list:
                p.args.append(phi_arg(p.var.stack[-1], st))
                pass

            pass
        pass

    for y in st.children:
        rename0(y)
        pass

    for v in lhs_vars:
        v.stack.pop()
        pass

    return


# rename_variables()-- Rename variables, give each variable assignment
# a version number.

def rename_variables(graph, variables):
    for v in variables:
        v.c = 0
        v.stack = []
        pass

    rename0(graph)

    for v in variables:
        del v.c, v.stack
        pass

    return


# ssa_conversion()-- Preform some initial optimization of the parsed
# IR, then convert it to ssa form.

def ssa_conversion(proc):
    st = proc.block.flatten0()

    st = label_optimize(st)
    st = jump_optimize(st)
    st = label_optimize(st)
    st = remove_dead_code(st)

    find_dominators(st)
    dominance_tree(st)
    dominance_frontier(st)


    variables = place_phi(st)
    for v in proc.args.values():
        if v not in variables:
            variables.append(v)
            pass

        pass

    rename_variables(st, variables)
    st = ssa_expr(st)

    return st

