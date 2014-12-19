

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



# Lexical analyzer for the SSE compiler

import re
from kw import *


class lex_error(Exception):
    pass


word_re  = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
float_re = re.compile(r'\d+\.\d*([EeDd][+-]?\d+)?')
int_re   = re.compile(r'\d+')

# The lexer takes a file object and returns a sequence of tokens.

class lexer:

    def __init__(self, filename):
        self.filename = filename
        
        self.fd = open(filename, 'r')
        self.token_queue = []
        self.line = 0
        self.current_line = ''

        self.lex_map = {}     # Map characters to lexers

        for c in '0123456789':
            self.lex_map[c] = self.parse_number
            pass

        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_':
            self.lex_map[c] = self.parse_word
            self.lex_map[c.lower()] = self.parse_word
            pass

# Unigrams and digram tokens

        self.uni_map = {}
        self.di_map = {}

        for t in token_list:
            if len(t.name) == 1:
                self.uni_map[t.name] = t

                if t.name not in self.lex_map:
                    self.lex_map[t.name] = self.parse_unigram
                    pass

                pass

            elif len(t.name) == 2:
                self.lex_map[t.name[0]] = self.parse_digram

                if t.name[0] not in self.di_map:
                    self.di_map[t.name[0]] = { t.name[1]: t }

                else:
                    self.di_map[t.name[0]][t.name[1]] = t
                    pass

                pass

            else:
                raise lex_error, 'Token name with more than two characters!'
            
            pass

# keywords, typenames

        self.kw_dict = {}

        for t in keyword_list + type_names + intrinsic_names:
            self.kw_dict[t.name] = t
            pass

        return


    def current_locus(self):
        col = len(self.original_line) - len(self.current_line) + 1
        return self.current_line, col


# error()-- Come here to build an error message associated with the
# current position.  Returns the string message.

    def error(self, msg):
        line, col = self.current_locus()

        print self.original_line.rstrip()
        print (col - 1) * ' ' + '^'
        print 'In line %d of %s: %s' % (self.line, self.filename, msg)

        raise SystemExit, 1


# next_line()-- Get another non-blank line if nothing is left of the
# current line.  Returns True if we are at the end of file, False
# otherwise.

    def next_line(self):
        while len(self.current_line) == 0:
            self.line += 1
            line = self.fd.readline()
            if len(line) == 0:
                self.at_eof = True
                return True

            line = line.rstrip()
            self.original_line = line
            self.current_line  = line.lstrip()
            pass

        return False

# eat_comment()-- Eat a /* to */ comment.  A regular expression won't
# work because they are greedy, we need to find the first '*/', not
# the last.

    def eat_comment(self):
        self.current_line = self.current_line[2:]

        while True:
            n = self.current_line.find('*/')
            if n >= 0:
                break

            self.current_line = ''
            if self.next_line():
                raise lex_error, 'File ended inside comment'

            pass

        self.current_line = self.current_line[n+2:]
        return


    def parse_number(self):
        m = float_re.match(self.current_line)
        if m is not None:
            self.current_line = self.current_line[len(m.group()):]
            return constant(float(m.group()))

        value = int_re.match(self.current_line).group()
        self.current_line = self.current_line[len(value):]
        return constant(int(value))


    def parse_unigram(self):
        t = self.uni_map[self.current_line[0]]
        self.current_line = self.current_line[1:]
        return t


# parse_digrams()-- All digrams have unigram interpretations, so if
# things don't work out here, try parse_unigram().

    def parse_digram(self):
        if len(self.current_line) == 1:
            return self.parse_unigram()

        a = self.current_line[0]
        b = self.current_line[1]

        dg = self.di_map[a]
        if b not in dg:
            return self.parse_unigram()

        self.current_line = self.current_line[2:]
        return dg[b]


# parse_word()-- Parse a word.  Returns an instance of some sort.  If
# the word isn't a reserved name, create a word() instance.

    def parse_word(self):
        m = word_re.match(self.current_line)
        name = m.group()

        self.current_line = self.current_line[len(name):]
        return self.kw_dict.get(name, word(name))


# next_token()-- Return the next token on the input.

    def next_token(self):
        if len(self.token_queue) > 0:
            return self.token_queue.pop(0)

        while True:
            self.current_line = self.current_line.lstrip()

            if self.next_line():
                return tok_eof

            if self.current_line.startswith('//'):  # End of line comment
                self.current_line = ''
                continue

            if self.current_line.startswith('/*'):  # Regular comment start 
                self.eat_comment()
                continue

            break

# We've hit something at this point

        c = self.current_line[0]
        if c not in self.lex_map:
            raise lex_error, "Bad character '%s' found" % c

        return self.lex_map[c]()


# push()-- Push a token back on the input.  Maximun of one push.

    def push(self, token):
        self.token_queue.insert(0, token)
        return


# peek_token()-- Peek at the next token, return True and consume the
# token if it is 't', leave the input alone if not.

    def peek_token(self, t):
        n = self.next_token()
        if t == n:
            return True

        self.push(n)
        return False


    def required_token(self, t):
        if self.next_token() == t:
            return

        raise lex_error, "Syntax error, '%s' not found" % t.name

    pass



def test_lexer():
    import sys

    if len(sys.argv) < 2:
        raise SystemExit, 'No filename'

    filename = sys.argv[1]

    lex = lexer(filename)
    line_width = 0

    while True:
        t = lex.next_token()

        s = str(t)
        w = len(s)

        if line_width + w > 70:
            print
            line_width = 0
            pass

        print s,
        line_width += w

        if t == tok_eof:
            break

        pass

    print
    return

