from copy import copy
from misc import dent_print as dent, matches_any

debug_val = 0
def debug(level, msg):
    if debug_val >= level:
        print("debug: " + str(msg))

# print(tree.root_node)

class Cursor:
    def __init__(self, cursor) -> None:
        self.cursor = cursor
        self.comments = None
        self.end = False

    def type(self) -> str:
        if self.end:
            return "!!!!!!!!!"
        return self.cursor.node.type
    
    def text(self) -> str:
        if self.end:
            return "!!!!!!!!!"
        return str(self.cursor.node.text, encoding='utf-8')
    
    def node(self):
        return self.cursor.node
    
    def next(self) -> bool:
        while self.cursor.goto_next_sibling():
            if self.type() == "comment":
                self.comments.append(self.cursor.node)
            else:
                return True
        self.end = True
        return False
    
    def next_no_skip(self) -> bool:
        out = self.cursor.goto_next_sibling()
        self.end = not out
        return out
    
    def child(self) -> bool:
        return self.cursor.goto_first_child()
    
    def parent(self) -> bool:
        self.end = False
        return self.cursor.goto_parent()
    
    def prev(self) -> bool:
        return self.cursor.goto_previous_sibling()
        

class Print:
    def print(self, d=0):
        dent(d, self.type + " (")
        self.data_print(d+1)
        dent(d, ")")

    def data_print(self, d):
        pass

class Context:
    def __init__(self) -> None:
        self.file = True
        self.deconstruction = False
        self.loop = False
        self.type = False
        self.param = False

class File(Print):
    def __init__(self) -> None:
        self.type = "File"
        self.shebang = None
        self.statements = None

    def new(cursor: Cursor):
        debug(1, "File")
        self = File()

        if not cursor.child():
            return self

        if cursor.type() == "shebang":
            self.shebang = cursor.text()
            cursor.next_no_skip()

        s = Statements(cursor)
        self.statements = s

        return self
    
    def data_print(self, d):
        if self.shebang:
            dent(d, "shebang: " + str(self.shebang))
        dent(d, "statements:")
        for x in self.statements:
            x.print(d+1)

    
class Comment(Print):
    def __init__(self) -> None:
        self.type = "Comment"
        self.content = []
        self.line = None

    def get_content(self, cursor: Cursor):
        cursor.child()
        cursor.next()
        # print(cursor.type())
        out = None
        if cursor.type() == "content":
            out = (True, cursor.text())
        else:
            cursor.child()
            cursor.next_no_skip()
            out = (False, cursor.text())
            cursor.parent()

        cursor.parent()
        return out

    def new(cursor: Cursor):
        debug(1, "Comment")
        self = Comment()
        

        (l, c) = self.get_content(cursor)
        self.line = l
        self.content = [c]
        last = cursor.node().start_point.row

        if not self.line:
            return self

        while cursor.next_no_skip():
            # print(cursor.node().start_point.row, last)
            if cursor.node().start_point.row != last + 1:
                cursor.prev()
                break
            
            if cursor.type() == "comment":
                (l, c) = self.get_content(cursor)
                if not l:
                    break
                self.content.append(c)
            elif matches_any(["assignment", "param"], cursor.type()):
                return Assignment.new(cursor, self)
            else:
                cursor.prev()
                break

            last = cursor.node().start_point.row

        # print("exit")
        return self
    
    def data_print(self, d):
        dent(d, "full-line: " + str(self.line))
        for x in self.content:
            dent(d+1, x)

#---------------------------Assignment------------------------------------

class Reassignment(Print):
    def __init__(self) -> None:
        self.type = "Reassignment"
        self.comments = []
        self.iter = None
        self.name = None
        self.op = None
        self.value = None

    def new(cursor: Cursor):
        self = Reassignment()
        cursor.comments = self.comments
        
        cursor.child()
        self.name = expression(cursor)
        cursor.next()

        self.op = cursor.text()
        cursor.next()

        if cursor.type() == "in":
            self.iter = True
            cursor.next()

        #value
        self.value = assignment_types(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "name:")
        self.name.print(d+1)
        if self.iter:
            dent(d, "iter: True")
        dent(d, "op: " + str(self.op))
        dent(d, "value:")
        self.value.print(d+1)


class Assignment(Print):
    def __init__(self) -> None:
        self.type = "Assignment"
        self.comments = []
        self.pub = False
        self.type_info = None
        self.const = True
        self.iter = False
        self.value = None
        self.doc = None
        self.name = None

    def new(cursor: Cursor, comment=None):
        debug(1, "Assignment")
        self = Assignment()
        cursor.comments = self.comments
        
        self.doc = comment
        
        #check if pub
        cursor.child()
        if cursor.type() == "pub":
            self.pub = True
            cursor.next()

        #var name
        self.name = expression(cursor)
        
        cursor.next()

        #var type info
        if cursor.type() == "type_data":
            self.type_info = TypeData.new(cursor)
            cursor.next()

        #is(n't) const
        if matches_any(["const", "var"], cursor.type()):
            self.const = cursor.type() == "const"
            cursor.next()
            
        #in
        if cursor.type() == "in":
            self.iter = True
            cursor.next()

        #value
        if matches_any(["function", "expression", "while", "if", "do", "multi_string"], cursor.type()):
            self.value = assignment_types(cursor)
            
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "name:")
        self.name.print(d+1)
        if self.doc:
            dent(d, "doc:")
            for x in self.doc.content:
                dent(d+1, x)
        if self.pub:
            dent(d, "pub: True")
        if self.const:
            dent(d, "const: True")
        if self.iter:
            dent(d, "iter: True")
        if self.type_info:
            dent(d, "type_info:")
            self.type_info.data_print(d+1)
        if self.value:
            dent(d, "value:")
            self.value.print(d+1)
        else:
            dent(d, "value: None")

class TypeData(Print):
    def __init__(self) -> None:
        self.type = "TypeData"
        self.comments = []
        self.data = None
        self.kind = None

    def new(cursor: Cursor):
        debug(1, "TypeData")
        self = TypeData()
        cursor.comments = self.comments
        
        cursor.child()
        self.kind = cursor.type()
        debug(1, "  " + cursor.type())

        if cursor.next():
            debug(1, "  " + cursor.type())
            if cursor.type() == "(":
                cursor.next()

            self.data = expression(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "type: " + self.kind)
        if self.data:
            dent(d, "value:")
            self.data.print(d+1)
        else:
            dent(d, "value: None")

#---------------------------ControlFlow------------------------------------

def assignment_types(cursor: Cursor):
    if cursor.type() == "function":
        return Function.new(cursor)
    elif cursor.type() == "expression":
        return expression(cursor)
    elif cursor.type() == "while":
        return While.new(cursor)
    elif cursor.type() == "if":
        return If.new(cursor)
    elif cursor.type() == "do":
        return Do.new(cursor)
    elif cursor.type() == "multi_string":
        return MultiString.new(cursor)

class Function(Print):
    def __init__(self) -> None:
        self.type = "Function"
        self.comments = []
        self.macro = False
        self.params = []
        self.ret = None
        self.block = None
        self.priority = None
        self.ref = None

    def new(cursor: Cursor):
        debug(1, "Function")
        self = Function()
        cursor.comments = self.comments

        cursor.child() #'fn'
        cursor.next()  #'parameter_list' | '!'
        if cursor.type() == "macro":
            self.macro = True
            cursor.next() #'parameter_list' | '<'
        
        if cursor.type() == "<":
            cursor.next()
            self.priority = expression(cursor)
            cursor.next()
            cursor.next()

        cursor.child() #'('
        cursor.next()  #'param'

        debug(1, "  " + cursor.type())
        if cursor.type() == "ref":
            self.ref = cursor.text()
            cursor.next()

        # print(cursor.type())
        while cursor.type() == "param":
            c = Assignment.new(cursor)
            self.params.append(c)
            
            cursor.next() # ',' | ')'
            if cursor.type() == ",":
                cursor.next()

        cursor.parent()
        cursor.next()

        if cursor.type() == "req_type_data":
            self.ret = TypeData.new(cursor)
            
            cursor.next()

        self.block = CodeBlock.new(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "macro: " + str(self.macro))
        if self.priority:
            dent(d, "priority: ")
            self.priority.print(d+1)
        if self.ret:
            dent(d, "return_type:")
            self.ret.data_print(d+1)
        else:
            dent(d, "return_type: None")
        dent(d, "params:")
        if self.ref:
            dent(d, f"self ref: {self.ref}")
        for p in self.params:
            p.print(d+1)
        self.block.print(d)

def Statements(cursor: Cursor):
    statements = []

    while cursor.type() != "}" and cursor.type() != "!!!!!!!!!":
        # print(cursor.type())
        if cursor.type() == "comment":
            c = Comment.new(cursor)
            statements.append(c)
            
        elif matches_any(["assignment", "param"], cursor.type()):
            c = Assignment.new(cursor)
            statements.append(c)
            
        elif cursor.type() == "control":
            c = Control.new(cursor)
            statements.append(c)
            
        elif cursor.type() == "reassignment":
            c = Reassignment.new(cursor)
            statements.append(c)
            
        elif cursor.type() == "expression":
            c = expression(cursor)
            statements.append(c)
            
        elif cursor.type() == "while":
            c = While.new(cursor)
            statements.append(c)

        elif cursor.type() == "if":
            c = If.new(cursor)
            statements.append(c)

        elif cursor.type() == "do":
            c = Do.new(cursor)
            statements.append(c)
            
        elif cursor.type() == ",":
            pass
            
        else:
            e = Print()
            e.type = "Unimplemented: " + cursor.type()
            statements.append(e)
                
        if not cursor.next_no_skip():
            break

    return statements

class CodeBlock(Print):
    def __init__(self) -> None:
        self.type = "CodeBlock"
        self.statements = []

    def new(cursor: Cursor):
        self = CodeBlock()

        cursor.child()#'{'
        cursor.next_no_skip()

        self.statements = Statements(cursor)

        cursor.parent()
        return self
    
    def data_print(self, d):
        for x in self.statements:
            x.print(d+1)

class Control(Print):
    def __init__(self) -> None:
        self.type = "Control"
        self.comments = []
        self.tag = None
        self.value = None
        self.kind = None

    def new(cursor: Cursor):
        self = Control()
        cursor.comments = self.comments
        
        cursor.child()
        self.kind = cursor.text()

        cursor.next()
        if cursor.type() == "tag":
            cursor.child()
            cursor.next()
            self.tag = cursor.text()
            cursor.parent()
            cursor.next()

        if cursor.type() != "tag" and cursor.type() != "!!!!!!!!!":
            self.value = expression(cursor)
            
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "type: " + self.kind)
        if self.tag:
            dent(d, "tag: " + str(self.tag))
        if self.value:
            dent(d, "return:")
            self.value.print(d+1)

def else_block(cursor):
    cursor.child() #'else'
    cursor.next()
    out = CodeBlock.new(cursor)
    cursor.parent()
    return out

class While(Print):
    def __init__(self) -> None:
        self.type = "While"
        self.comments = []
        self.tag = None
        self.else_block = None
        self.condition = None
        self.block = None

    def new(cursor: Cursor):
        self = While()               
        cursor.comments = self.comments
        
        cursor.child() #'while'
        cursor.next()
        if cursor.type() == "tag":
            cursor.child()
            cursor.next()
            self.tag = cursor.text()
            cursor.parent()
            cursor.next()

        if cursor.type() == "expression":
            c = expression(cursor)
        elif cursor.type() == "assignment":
            c = Assignment.new(cursor)
        elif cursor.type() == "reassignment":
            c = Reassignment.new(cursor)

        self.condition = c
        
        cursor.next()

        c = CodeBlock.new(cursor)
        self.block = c
        
        cursor.next()

        if cursor.type() == "else":
            self.else_block = else_block(cursor)
            
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        if self.tag:
            dent(d, "tag: " + str(self.tag))
        dent(d, "condition:")
        self.condition.print(d+1)
        self.block.print(d)
        if self.else_block:
            dent(d, "else:")
            self.else_block.print(d+1)

class Do(Print):
    def __init__(self) -> None:
        self.type = "Do"
        self.comments = []
        self.tag = None
        self.condition = None
        self.else_block = None
        self.block = None

    def new(cursor: Cursor):
        self = Do()               
        cursor.comments = self.comments
        
        cursor.child()# 'do'
        cursor.next()
        if cursor.type() == "tag":
            cursor.child()
            cursor.next()
            self.tag = cursor.text()
            cursor.parent()
            cursor.next()

        self.block = CodeBlock.new(cursor)
        
        cursor.next()

        if cursor.type() == "keyword":
            cursor.next()
            self.condition = expression(cursor)
            
            cursor.next()

        if cursor.type() == "else":
            self.else_block = else_block(cursor)
            
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        if self.tag:
            dent(d, "tag: " + str(self.tag))
        if self.condition:
            dent(d, "condition:")
            self.condition.print(d+1)
        self.block.print(d)
        if self.else_block:
            dent(d, "else:")
            self.else_block.print(d+1)

def if_conditions(cursor: Cursor):
    cons = []

    while cursor.type() == "expression":
        c = expression(cursor)
        cons.append(c)
        
        cursor.next()

        if cursor.type() == ",":
            cursor.next()

    return cons

class If(Print):
    def __init__(self) -> None:
        self.type = "If"
        self.comments = []
        self.tag = None
        self.key = None
        self.elifs = []
        self.else_block = None
        self.conditions = None
        self.block = None
        self.assignment = None

    def new(cursor: Cursor):
        self = If()               
        cursor.comments = self.comments
        
        cursor.child()# 'if'
        cursor.next()
        if cursor.type() == "tag":
            cursor.child()
            cursor.next()
            self.tag = cursor.text()
            cursor.parent()
            cursor.next()

        if cursor.type() == "|":
            cursor.next()
            cursor.child()
            self.key = expression(cursor)
            cursor.parent()
            cursor.next()
            cursor.next()

        if cursor.type() == "assignment":
            self.assignment = Assignment.new(cursor)
            cursor.next()

        self.conditions = if_conditions(cursor)
        
        self.block = CodeBlock.new(cursor)
        cursor.next()

        while cursor.type() == "elif":
            c = Elif.new(cursor)
            self.elifs.append(c)

            if not cursor.next():
                break

        if cursor.type() == "else":
            self.else_block = else_block(cursor)
            
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        if self.tag:
            dent(d, "tag: " + str(self.tag))
        if self.key:
            dent(d, "key:")
            self.key.print(d+1)
        if self.assignment:
            dent(d, "assignment:")
            self.assignment.print(d+1)
        dent(d, "conditions:")
        for con in self.conditions:
            con.print(d+1)
        self.block.print(d)
        if len(self.elifs) > 0:
            dent(d, "elifs:")
            for con in self.elifs:
                con.print(d+1)
        if self.else_block:
            dent(d, "else:")
            self.else_block.print(d+1)

class Elif(Print):
    def __init__(self) -> None:
        self.type = "Elif"
        self.conditions = None
        self.block = None
        self.assignment = None

    def new(cursor: Cursor):
        self = Elif()
        
        cursor.child()# 'elif'
        cursor.next()

        if cursor.type() == "assignment":
            self.assignment = Assignment.new(cursor)
            cursor.next()

        self.conditions = if_conditions(cursor)
        self.block = CodeBlock.new(cursor)
        
        cursor.parent()
        return self
    
    def data_print(self, d):
        if self.assignment:
            dent(d, "assignment:")
            self.assignment.print(d+1)
        dent(d, "conditions:")
        for con in self.conditions:
            con.print(d+1)
        self.block.print(d)
        

#---------------------------Expression------------------------------------

def expression(cursor: Cursor):
    debug(1, "expression " + cursor.type())
    
    # print(cursor.type())
    drop = matches_any(["expression", "limited_expression", "priority"], cursor.type())
    if drop:
        cursor.child()
    out = None
    if cursor.type() == "identifier":
        out = Ident.new(cursor)
    elif cursor.type() == "binary_expression":
        out = BinaryExpression.new(cursor)
    elif cursor.type() == "unary_expression":
        out = UnaryExpression.new(cursor)
    elif cursor.type() == "parenthesized_expression":
        out = ParenthesizedExpression.new(cursor)
    elif cursor.type() == "postfix_expression":
        out = PostfixExpression.new(cursor)
    elif cursor.type() == "bool":
        out = Bool.new(cursor)
    elif cursor.type() == "integer":
        out = Integer.new(cursor)
    elif cursor.type() == "float":
        out = Float.new(cursor)
    elif cursor.type() == "string":
        out = BasicString.new(cursor)
    elif cursor.type() == "table":
        out = Table.new(cursor)
    elif matches_any(Basic_Literal.types, cursor.type()): #literals
        out = Basic_Literal.new(cursor)
    elif cursor.type() == "index": #table_values
        out = Postfix.new(cursor)
    else:
        e = Print()
        e.type = "Unimplemented: " + cursor.type()
        out = e

    if drop:
        cursor.parent()
    return out

class BinaryExpression(Print):
    def __init__(self) -> None:
        self.type = "BinaryExpression"
        self.comments = []
        self.left = None
        self.op = None
        self.right = None

    def new(cursor: Cursor):
        self = BinaryExpression()
        cursor.comments = self.comments
        
        cursor.child()
        self.left = expression(cursor)
        
        cursor.next()
        self.op = cursor.text()

        cursor.next()
        self.right = expression(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "op: " + str(self.op))
        dent(d, "left:")
        self.left.print(d+1)
        dent(d, "right:")
        self.right.print(d+1)

class UnaryExpression(Print):
    def __init__(self) -> None:
        self.type = "UnaryExpression"
        self.comments = []
        self.op = None
        self.value = None

    def new(cursor: Cursor):
        self = UnaryExpression()
        cursor.comments = self.comments
        
        cursor.child()
        self.op = cursor.text()

        cursor.next()
        self.value = expression(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "op: " + str(self.op))
        dent(d, "value:")
        self.value.print(d+1)

class ParenthesizedExpression(Print):
    def __init__(self) -> None:
        self.type = "ParenthesizedExpression"
        self.comments = []
        self.value = None

    def new(cursor: Cursor):
        self = ParenthesizedExpression()
        cursor.comments = self.comments
        
        cursor.child() #'('
        cursor.next()

        self.value = expression(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        self.value.print(d+1)

def postfix(cursor: Cursor):
    if cursor.type() == "function_call":
        return FunctionCall.new(cursor)
    elif matches_any(["get_type", "deref"], cursor.type()):
        return SimplePostfix.new(cursor)
    else:
        return Postfix.new(cursor)

class SimplePostfix(Print):
    def __init__(self) -> None:
        self.type = "SimplePostfix"
        self.comments = []

    def new(cursor: Cursor):
        self = SimplePostfix()
        cursor.comments = self.comments
        
        if cursor.type() == "get_type":
            self.type = "GetType"
        else:
            self.type = "Deref"

        cursor.comments = None
        return self
    
    def print(self, d):
        dent(d, self.type)

class FunctionCall(Print):
    def __init__(self) -> None:
        self.type = "FunctionCall"
        self.comments = []
        self.values = []

    def new(cursor: Cursor):
        self = FunctionCall()
        cursor.comments = self.comments
        
        cursor.child()
        cursor.next()

        while cursor.type() != ")" and cursor.type() != "!!!!!!!!!":
            if cursor.type() == "reassignment":
                c = Reassignment.new(cursor)
            else:
                c = expression(cursor)
            self.values.append(c)
            
            cursor.next()

            if cursor.type() == ",":
                cursor.next()

        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        for value in self.values:
            value.print(d+1)

class Postfix(Print):
    def __init__(self) -> None:
        self.type = "Postfix"
        self.comments = []
        self.value = None

    def new(cursor: Cursor):
        self = Postfix()
        cursor.comments = self.comments
        
        # print("postfix: " + cursor.type())
        if cursor.type() == "index":
            self.type = "Index"
        elif cursor.type() == "field_index":
            self.type = "FieldIndex"
        elif cursor.type() == "field":
            self.type = "Field"
        else:
            self.type = "CreateType"

        cursor.child()
        if self.type != "CreateType":
            cursor.next()

        self.value = expression(cursor)
        
        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        self.value.print(d+1)
            

class PostfixExpression(Print):
    def __init__(self) -> None:
        self.type = "PostfixExpression"
        self.comments = []
        self.ops = []
        self.value = None

    def new(cursor: Cursor):
        self = PostfixExpression()
        cursor.comments = self.comments
        
        depth = 0
        while cursor.type() == "postfix_expression":
            cursor.child()
            depth += 1

        self.value = expression(cursor)
        

        for _ in range(depth):
            cursor.next()
            c = postfix(cursor)
            self.ops.append(c)
            
            cursor.parent()

        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "value:")
        self.value.print(d+1)
        dent(d, "ops:")
        for op in self.ops:
            op.print(d+1)

#---------------------------Literals------------------------------------

class Ident(Print):
    def __init__(self) -> None:
        self.type = "Ident"
        self.name = None

    def new(cursor: Cursor):
        self = Ident()
        
        self.name = cursor.text()
        
        return self
    
    def print(self, d):
        dent(d, self.type + ": " + str(self.name))

class Basic_Literal(Print):
    types = ["nil", "root", "compiler", "args"]

    def __init__(self) -> None:
        self.type = "Literal err"
        self.comments = []

    def new(cursor: Cursor):
        self = Basic_Literal()
        
        self.type = str(cursor.type()).title()
        
        return self
    
    def print(self, d):
        dent(d, self.type)

class Bool(Print):
    def __init__(self) -> None:
        self.type = "Bool"
        self.comments = []
        self.value = None

    def new(cursor: Cursor):
        self = Bool()
        cursor.comments = self.comments
        
        cursor.child()
        # print(cursor.text())
        self.value = len(str(cursor.text())) == 4

        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "value: " + str(self.value))

class Integer(Print):
    def __init__(self) -> None:
        self.type = "Integer"
        self.comments = []
        self.value = None
        self.base = None

    def new(cursor: Cursor):
        self = Integer()
        cursor.comments = self.comments
        
        cursor.child()
        self.base = int(cursor.type()[1:])
        self.value = cursor.text()

        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "base: " + str(self.base))
        dent(d, "value: " + str(self.value))

class Float(Print):
    def __init__(self) -> None:
        self.type = "Float"
        self.comments = []
        self.exponent = None
        self.value = None

    def new(cursor: Cursor):
        self = Float()
        cursor.comments = self.comments
        
        cursor.child()
        self.value = cursor.text()
        cursor.next()

        if cursor.type() == "exponent":
            self.exponent = cursor.text()

        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        dent(d, "value: " + str(self.value))
        if self.exponent:
            dent(d, "exponent: " + str(self.exponent))

class BasicEscape(Print):
    def __init__(self) -> None:
        self.type = "BasicEscape"
        self.value = None

    def new(cursor: Cursor):
        self = BasicEscape()
        
        self.value = cursor.text()
        
        return self
    
    def print(self, d):
        dent(d, "escape: " + str(self.value))

class ValueEscape(Print):
    def __init__(self) -> None:
        self.type = "ValueEscape"
        self.formats = []
        self.value = None

    def new(cursor: Cursor):
        self = ValueEscape()
        
        cursor.child()#'\{'
        cursor.next()

        self.value = expression(cursor)
        
        cursor.next()
        if cursor.type() == "escape_format":
            cursor.child()#';'
            
            while cursor.next():
                self.formats.append((cursor.type(), cursor.text()))

            cursor.parent()
        
        cursor.parent()
        return self
    
    def data_print(self, d):
        if len(self.formats) > 0:
            dent(d, "formatting:")
            for format in self.formats:
                dent(d+1, str(format[0]) + ": " + str(format[1]))
        dent(d, "value:")
        self.value.print(d+1)

class IntEscape(Print):
    def __init__(self) -> None:
        self.type = "IntEscape"
        self.values = []

    def new(cursor: Cursor):
        self = IntEscape()
        
        cursor.child()#'\['
        cursor.next()

        while cursor.type() != "escape_quot" and cursor.type() != "!!!!!!!!!":
            # print("int:" + str(cursor.type()))
            c = expression(cursor)
            self.values.append(c)
            
            cursor.next()

            if cursor.type() == ",":
                cursor.next()
        
        cursor.parent()
        return self
    
    def print(self, d):
        for value in self.values:
            dent(d, "value:")
            value.print(d+1)
            

class Content(Print):
    def __init__(self, value) -> None:
        self.type = "Content"
        self.value = value

    def print(self, d):
        dent(d, "content: " + str(self.value))

class BasicString(Print):
    def __init__(self) -> None:
        self.type = "BasicString"
        self.content = []
        
    def new(cursor: Cursor):
        self = BasicString()
        
        cursor.child() #quot
        while cursor.next(): #escapes
            # print(cursor.type())
            if cursor.type() == "content":
                self.content.append(Content(cursor.text()))
            elif cursor.type() == "basic_escape":
                c = BasicEscape.new(cursor)
                self.content.append(c)
                
            elif cursor.type() == "value_escape":
                c = ValueEscape.new(cursor)
                self.content.append(c)
                
            elif cursor.type() == "int_escape":
                c = IntEscape.new(cursor)
                self.content.append(c)
                
        cursor.parent()
        return self
    
    def data_print(self, d):
        for content in self.content:
            content.print(d+1)

class MultiString(Print):
    def __init__(self) -> None:
        self.type = "MultiString"
        self.strings = []

    def new(cursor: Cursor):
        self = MultiString()
        
        cursor.child()
        while True:
            c = BasicString.new(cursor)
            self.strings.append(c)
            
            if not cursor.next():
                break

        cursor.parent()
        return self
    
    def data_print(self, d):
        for content in self.strings:
            content.print(d+1)

class Table(Print):
    def __init__(self) -> None:
        self.type = "Table"
        self.comments = []
        self.statements = None

    def new(cursor: Cursor):
        self = Table()
        cursor.comments = self.comments

        cursor.child()

        cursor.next_no_skip()
        self.statements = Statements(cursor)

        cursor.parent()
        cursor.comments = None
        return self
    
    def data_print(self, d):
        for x in self.statements:
            x.print(d)


def dump_tree(node, depth=0):
    dent(depth, node.type)

    for child in node.children:
        dump_tree(child, depth + 1)


def parse_file(tree):
    # dump_tree(tree.root_node)
    # print("---------------------------------------------------------")

    out = File.new(Cursor(tree.root_node.walk()))
    return out