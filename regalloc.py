
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


from ir_nodes import expr, expr_assign, label, jump



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


# color_graph()-- Color registers.  We start be considering all
# variables to not be part of the interference graph, then add one
# node at a time, in the reverse of the perfect-elimination-order,
# looking at the present variables to find a unique color.

def color_graph(graph):
    peo = var_dominance(graph)

    for v in peo:
        v.present = False
        if not hasattr(v, 'interference'):
            v.interference = []
            pass

        pass

    peo.reverse()

    for v in peo:
        colors = {}

        for w in v.interference:
            if w.present:
                colors[w.color] = True
                pass

            pass

        c = 0
        while True:
            if c not in colors:
                break

            c = c + 1
            pass

        v.color = c
        v.present = True
        pass

    for v in peo:
        del v.present
        print v.name, v.color
        pass

    return

