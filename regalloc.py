
# (C) 2014-2915 Andrew Vaught
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


# Register allocation

from ir_nodes import expr, expr_swap, expr_assign, label, jump, show_flowgraph
from ir_nodes import get_temp_label, invert_condition, integer_register

from ir_nodes import reg_a, reg_b, reg_c, reg_d, reg_src, reg_dst, reg_base
from ir_nodes import reg_8, reg_9, reg_10, reg_11, reg_12, reg_13, reg_14
from ir_nodes import reg_15, xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7
from ir_nodes import xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15

from kw import type_int8, type_int4, type_int2, type_int1, type_uint8
from kw import type_uint4, type_uint2, type_uint1, type_float4, type_float8
from kw import type_float8_2,type_float4_4, type_int8_2, type_int4_4
from kw import type_int2_8, type_int1_16


import sys

def show_live(st, info):

    if isinstance(st, expr_assign):
        print 'Assign to', st.var.name, [ v.name for v in info ]

    elif isinstance(st, jump):
        print 'Jump to', st.label.name, [ v.name for v in info ]

    elif isinstance(st, label):
        print 'label', st.name, [ v.name for v in info ]

    else:
        print '????'
        pass

    sys.stdin.readline()
    return


# liveness()-- Compute the list of live variables for each node.
# There are specific algorithms for ssa, but we use the more general
# algorithm.  The algorithm works by first setting the live-list for
# all nodes to the empty list. Variables that are used in a node must
# be live in predecessor nodes, unless the predecessor sets that
# variable.  Liveness flows from a use backwards.  Since nodes can be
# reached by successors on different paths, more than one pass through
# the flow graph is often necessary.

# We implement this by a stack of 'walkers'.  Each walker is a
# two-tuple of an ir_node and a list of live variables.  Walkers are
# popped off the stack and add their live variables to the ir_node,
# All nodes must be visited at least once.  After that, Walkers which
# don't add any new information are dropped.  Walkers that do add new
# information have any assignment variables removed and propagate
# multiple new walkers to predecessor ir_nodes, When the stack is
# empty, we're done.

# The live[] list indicates live variables immediately preceding the
# statement that it lives on.

def liveness(graph):

    tail = None
    st = graph
    while st is not None:
        tail = st
        st.live = {}
        st.mark = False
        st = st.next
        pass

    stack = [ (tail, [] ) ]

    while len(stack) > 0:
        st, info = stack.pop()

        if isinstance(st, label):
            liveness_label(st, info, stack)

        else:
            liveness_regular(st, info, stack)
            pass

        pass

# Remove the mark member

    st = graph
    while st is not None:
        st.live = st.live.keys()
        del st.mark
        st = st.next
        pass

    return


# liveness_regular()-- process a non-label node for liveness.

def liveness_regular(st, info, stack):

# Add used-variables to the live list.

    used = {}

    if isinstance(st, expr_assign):
        st.value.used_vars(used)

    elif isinstance(st, jump) and st.cond is not None:
        st.cond.used_vars(used)
        pass

    for v in used.keys():
        if v not in info:
            info.append(v)
            pass

        pass

# Remove set variables from the live list

    if isinstance(st, expr_assign):
        if st.var in info:
            info.remove(st.var)
            pass

        pass

# Update the current node

    changed = False

    for v in info:
        if v in st.live:
            continue

        st.live[v] = True
        changed = True
        pass

    if changed or (not st.mark):
        st.mark = True

        for st in st.predecessor():
            stack.append((st, info[:]))
            pass

        pass

    return


# liveness_label()-- Process liveness for a phi node.  Very different
# than other nodes.  We don't worry about stopping walkers, just
# spawning them.

def liveness_label(st, info, stack):

    for phi_node in st.phi_list:
        v = phi_node.lhs
        if v in info:
            info.remove(v)
            pass

        pass

    for v in info:
        if v not in st.live:
            st.live[v] = True
            pass

        pass        

    pred = st.predecessor()

    for phi_node in st.phi_list:
        for arg in phi_node.args:
            if arg.node is st.prev:
                st.live[arg.var] = True
                pass

            new_info = info[:]
            if arg.var not in new_info:
                new_info.append(arg.var)
                pass

            stack.append((arg.node, new_info))

            if arg.node in pred:
                pred.remove(arg.node)
                pass

            pass

        pass

# Add predecessors that aren't phi functions

    for st in pred:
        stack.append((st, info))
        pass

    return


# interference_graph()-- Given the program flow graph with liveness
# information at each node, create an interference graph.  Variables
# are the nodes, edges are pairs of variables that are simultaneously
# live.  Links variable instances with each other through the
# interferes[] list on each variable.  Returns a list of live
# variables.

def interference_graph(graph):
    result = {}

    st = graph
    while st is not None:
        for v in st.live:
            result[v] = True
            pass

        st = st.next
        pass

    result = result.keys()

    for v in result:
        v.interference = {}
        pass

    st = graph
    while st is not None:
        for a in st.live:
            for b in st.live:
                if a is not b:
                    a.interference[b] = True
                    pass

                pass
            pass

        st = st.next
        pass

    for v in result:
        v.interference = v.interference.keys()
        pass

    return result


def show_interference(graph):
    variables = {}
    st = graph

    while st is not None:
        for v in st.live:
            variables[v] = True
            pass

        st = st.next
        pass

    for v in variables.keys():
        print v.name, '-->',
        for w in v.interference:
            print w.name,
            pass

        print
        pass

    return



# var_dominance()-- Create a list of variable dominance order.  This
# means traversing the dominance tree, adding variable definitions in
# post-order.  This forms a perfect elimination order for coloring,

def var_dominance(st):
    result = []

    for child in st.children:
        result += var_dominance(child)
        pass

    if isinstance(st, expr_assign):
        result.append(st.var)

    elif isinstance(st, label):
        for p in st.phi_list:
            result.append(p.lhs)
            pass

        pass

    return result


# pick_register()-- Given a variable v, pick a register for it.  TODO:
# memory registers not re-used like machine registers are.

def pick_register(v):
    bt = v.type.basic_type

    if bt in [ type_int8, type_int4, type_int2, type_int1,
               type_uint8, type_uint4, type_uint2, type_uint1 ]:

        reglist = [ reg_b, reg_c, reg_d, reg_src, reg_dst, reg_base, reg_8,
                    reg_9, reg_10, reg_11, reg_12, reg_13, reg_14, reg_15 ]

    elif bt in [ type_float4, type_float8, type_float8_2,type_float4_4,
                 type_int8_2, type_int4_4, type_int2_8, type_int1_16 ]:

        reglist = [ xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7,
                    xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15 ]

    else:
        raise RuntimeError, 'pick_register(): Unknown type'

    for w in v.interference:
        if v.present and (not isinstance(v.register, memory)):
            r = v.register

            if isinstance(r, integer_subreg):
                r = r.parent
                pass

            reglist.remove(r)
            pass

        pass

    r = reglist.pop(0) if len(reglist) > 0 else get_memory_register()

    if isinstance(r, integer_register):
        r = r.get_subreg(v.type)
        pass

    return r


# color_graph()-- Color registers.  We start be considering all
# variables to not be part of the interference graph, then add one
# node at a time, in the reverse of the perfect-elimination-order,
# looking at the present variables to find a unique color.

def color_graph(graph):
    peo = var_dominance(graph)
    print [ v.name for v in peo ]

    for v in peo:
        v.present = False
        if not hasattr(v, 'interference'):
            v.interference = []
            pass

        pass

    peo.reverse()

    for v in peo:
        v.register = pick_register(v)
        v.present = True
        pass

    for v in peo:
        del v.present
        pass

    return


# phi_merge()-- Insert code that implements the phi-assignments for
# each entry to a label.  One phi function at a label means a possible
# assignment.  Multiple phi functions imply a permutation of hardware
# registers.  If a control reaches a label via a conditional jump,
# then the code around the jump may need to be restructured.

def phi_merge(graph):
    st = graph
    while st is not None:
        if isinstance(st, label):
            merge_label(st)
            pass

        st = st.next
        pass

    return


# merge_label()-- Handle the phi maerging for a single label.  For
# each label entry point, we collect the phi-arguments, then pass them
# along to merge_single_entry().

def merge_label(st):
    entry = {}

    for phi in st.phi_list:
        for arg in phi.args:
            if arg.var.register == phi.lhs.register:
                continue    # Discard assignments to same register

            t = arg.var, phi.lhs

            if arg.node in entry:
                entry[arg.node].append(t)

            else:
                entry[arg.node] = [ t ]
                pass

            pass

        pass

    for entry, plist in entry.items():
        merge_single_entry(st, entry, plist)
        pass

    return


# merge_single_entry()-- Given the phi-assignment label st, the entry
# node 'entry', and the list of phi-assignments, figure out the move
# or swaps that make the phi-assignments happen.

def merge_single_entry(st, entry, plist):

    print '-------'
    for a, b in plist:
        print '%s (%d) -> %s (%d)' % (a.name, a.register, b.name, b.register)
        pass

    instructions = merge_instructions(plist)

# Now insert these instruction on the entry path.  If the entry is not
# a jump, then the phi follows this instruction, so insert the new
# instruction prior to the phi.

    if not isinstance(entry, jump):
        for n in instructions:
            st.insert_prev(n)
            pass

        pass

    elif entry.cond is None:

# For an entry via an unconditional jump, insert the instructions
# prior to the jump.
        for n in instructions:
            entry.insert_prev(n)
            pass

        pass

    else:

# Nastiness because we have to insert a new code path along the jump.
#
#   jump L1 if a
#
# becomes
#
#   jump L2 if !a
#   <new instructions>
#   jump L1
# L2:

        new_label = get_temp_label()
        new_label.insert_next(entry)

        jump(entry.label).inset_next(entry)

        for n in instructions:
            entry.insert_next(n)
            pass

        entry.label = new_label
        entry.cond = invert_condition(entry.cond)
        pass

    return


# merge_instructions()-- Take the plist, un-zip it into two vectors, a
# from vector and a 'to' vector.  We look at the register entries but
# generate instructions in terms of variables.

def merge_instructions(plist):
    if len(plist) == 1:
        a, b = plist[0]
        return [ expr_assign(b, a) ]

    v_from = []
    v_to = []

    phys_from = []
    phys_to = []

    for a, b in plist:
        v_from.append(a)
        phys_from.append(a.register)

        v_to.append(b)
        phys_to.append(b.register)
        pass

# Figure out a sequence of swaps to transform v_from to v_to.  We do a
# real simple method of bringing each element into position in
# sequence.  There is surely a more optimum way.

    n = 0
    result = []

    while n < len(v_from):
        if phys_from[n] is not phys_to[n]:
            k = phys_from.index(phys_to[n])

            e = expr_swap(v_from[k], v_to[n])
            result.append(e)

            t = v_to[n]
            v_to[n] = v_from[k]
            v_from[k] = t

            t = phys_to[n]
            phys_to[n] = phys_from[k]
            phys_from[k] = t
            pass

        n = n + 1
        pass

    return result


# allocate()-- Allocate registes

def allocate(graph):
    liveness(graph)
    interference_graph(graph)
    color_graph(graph)
    phi_merge(graph)

#    show_flowgraph(graph)

    return

