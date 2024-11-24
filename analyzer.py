from tree_sitter import Language, Parser
import tree_sitter_munya as tsmunya

MUNYA_LANGUAGE = Language(tsmunya.language())
tree_parser = Parser(MUNYA_LANGUAGE)

import parser
from misc import matches_any, dent, dump
from pathlib import Path

from typing import Any, Self

def get_type(tree: parser.Assignment, parent):
    if tree.type_info == None:
        return "_"

    if tree.type_info.data != None:
        if matches_any(["PostfixExpression", "UnaryExpression"], tree.type_info.data.type):
            return Expression(parent, tree.type_info.data)
        return tree.type_info.data.name
    elif tree.value != None:
        # dump(tree.value)
        if tree.value.type == "Integer":
            return "I64"
        elif tree.value.type == "PostfixExpression":
            if tree.value.value.type == "Compiler":
                return "_"
            # dump(tree.value.value)
            return tree.value.value.name
        elif tree.value.type == "Function":
            return "Function"
        elif tree.value.type == "BasicString":
            return "String"
    
    return "_"

def Expression(parent, tree):
    if tree.type == "BinaryExpression":
        var = Var(parent)
        var.statement = "Binary"
        var.op = tree.op
        var.append(Expression(var, tree.left), "left")
        var.append(Expression(var, tree.right), "right")
        return var
    elif tree.type == "UnaryExpression":
        var = Var(parent)
        var.statement = "Unary"
        var.op = tree.op
        var.append(Expression(var, tree.value))
        return var
    elif tree.type == "ParenthesizedExpression":
        var = Var(parent)
        var.statement = "Parentheses"
        var.append(Expression(var, tree.value))
        return var
    elif matches_any(["PostfixExpression", "Table"], tree.type):
        var = Var(parent)
        var.PostfixExpression(tree)
        return var
    elif tree.type == "Field":
        return tree.value.name
    elif tree.type == "Integer":
        return tree.value
    elif tree.type == "Assignment":
        var = Var(parent)
        var.Assignment(tree)
        return var
    elif tree.type == "Reassignment":
        var = Var(parent)
        var.Reassignment(tree)
        return var
    elif tree.type == "Bool":
        # print(f"t:{tree.print()}")
        if tree.value:
            return "true"
        return "false"
    elif tree.type == "BasicString":
        var = Var(parent)
        var.BasicString(tree)
        return var
    else:
        # dump(tree)
        return tree.name

class Var:
    statement: str = None
    name: str = None
    tag: str = None
    type: str = None
    op: str = None
    value: str = None
    out: str = None
    drop: bool = False
    ex_drop: Self = None
    macro: bool = False
    # ref: str = None
    key: str = None
    elifs = None
    els = None

    def __init__(self, parent=None) -> None:
        self.params = {}
        self.param_order = []
        self.elifs = []
        self.parent = parent
        self.children = {}

    def append(self, value, name=None):
        if name == None:
            name = f"{len(self.params)}"
        self.params[name] = value
        self.param_order.append(name)

    def insert(self, value, index, name):
        self.params[name] = value
        self.param_order.insert(index, name)

    def print(self, d=0):
        string = ""
        string += dent(d, "=======================================================================")
        # dent(d, f"self: {self}")
        if self.statement != None:
            string += dent(d, f"statement: {self.statement}")
        if self.name != None:
            if type(self.name) is Var:
                string += dent(d, f"name:")
                string += self.name.print(d+1)
            else:
                string += dent(d, f"name: {self.name}")
        if self.tag != None:
            string += dent(d, f"tag: {self.tag}")
        if self.key != None:
            if type(self.key) is Var:
                string += dent(d, f"op:")
                string += self.key.print(d+1)
            else:
                string += dent(d, f"key: {self.key}")
        if self.op != None:
            if type(self.op) is Var:
                string += dent(d, f"op:")
                string += self.op.print(d+1)
            else:
                string += dent(d, f"op: {self.op}")
        if self.type != None:
            string += dent(d, f"type: {self.type}")
        if self.value != None:
            if type(self.value) is Var:
                string += dent(d, "value:")
                string += self.value.print(d+1)
            else:
                string += dent(d, f"value: {self.value}")
        if len(self.params) > 0:
            string += dent(d, "params:")
            for x in self.param_order:
                if type(self.params[x]) is Var:
                    string += self.params[x].print(d+1)
                else:
                    string += dent(d+1, f"{x}: {self.params[x]}")
                    if type(self.params[x]) is dict:
                        if self.params[x].get("value") != None:
                            if type(self.params[x]["value"]) is Var:
                                string += self.params[x]["value"].print(d+1)
                        # print(type(self.params[x].get("type")))
                        if type(self.params[x].get("type")) is Var:
                            string += self.params[x]["type"].print(d+1)
        if len(self.elifs) > 0:
            string += dent(d, "elifs:")
            for x in self.elifs:
                string += x.print(d+1)
        if self.els != None:
            string += dent(d, f"else:")
            string += self.els.print(d+1)
        if self.out != None:
            string += dent(d, f"out: {self.out}")
        # if self.ref != None:
        #     dent(d, f"ref: {self.ref}")
        if self.drop:
            string += dent(d, f"drop: {self.drop}")
        if self.ex_drop != None:
            string += dent(d, f"ex_drop:")
            string += self.ex_drop.print(d+1)
        # string += dent(d, f"macro: {self.macro}")
        if len(self.children) > 0:
            string += dent(d, "children:")
            for name, x in self.children.items():
                string += dent(d+1, name)
        # if self.parent != None:
        #     dent(d, f"parent: {self.parent}")
        string += dent(d, "-----------------------------------------------------------------------")
        return string
    
    def __str__(self) -> str:
        return self.print()

    def params_in_order(self) -> list[tuple[str, Self]]:
        out = []
        for i, x in enumerate(self.param_order):
            out.append((i, self.params[x]))
        return out
    
    def get_assignment_type(self, tree: parser.Assignment):
        if tree.type_info.data != None:
            self.type = tree.type_info.data.name
        
        if tree.value.type == "Integer":
            self.type = "I64"
        
        if tree.value.type == "PostfixExpression":
            # dump(tree.value.value)
            name = tree.value.value.name
            if name == "Enum":
                self.type = "Enum"
            elif name == "Type":
                self.type = "Type"

    def collect_params(self, params):
        index = 0
        for x in params:
            # print("param")
            # dump(x)
            t = {}
            if x.type == "Comment":
                continue
            elif not(matches_any(["Assignment", "Reassignment"], x.type)):
                t["index"] = str(index)
                t["value"] = Expression(self, x)
                index += 1
            else:
                if x.type == "Reassignment":
                    # dump(x.name)
                    if x.name.type == "Index":
                        t["index"] = Expression(self, x.name.value)
                    else:
                        t["name"] = x.name.name
                    t["value"] = Expression(self, x.value)
                else:
                    t["name"] = x.name.name
                    type = get_type(x, self)
                    t["type"] = type
                    if type == "Function":
                        var = Var(self)
                        var.Assignment(x)
                        t["value"] = Expression(self, x)
        
            self.append(t, t.get("name"))

    def Assignment(self, tree: parser.Assignment):
        self.statement = "Assignment"
        self.type = get_type(tree, self)

        # print(self.type)
        self.name = Expression(self, tree.name)
        
        if matches_any(["Enum", "Type"], self.type):
            # dump(tree.value.ops[0])
            self.collect_params(tree.value.ops[0].value.statements)
        elif self.type == "Function":
            self.collect_params(tree.value.params)
            # dump(tree.value)
            if tree.value.ref != None:
                var = Var(self)
                var.statement = "Unary"
                var.op = "&="
                var.append("Self")

                self.params["self"]["type"] = var
            self.macro = tree.value.macro
            self.out = "_"
            if tree.value.ret != None:
                self.out = tree.value.ret.data.name
            self.value = Var(self)
            self.value.code_block(tree.value.block)
        # elif self.type == "String":
        #     # dump(tree.value)
        #     var = Var(self)
        #     var.BasicString(tree.value)
        #     self.value = var
        else:
            self.value = Expression(self, tree.value)
            

    def PostfixExpression(self, tree: parser.PostfixExpression):
        if tree.type == "Table":
            tree = table_postfix(tree)
        # dump(tree)
        if tree.value.type == "Compiler":
            self.statement = "CompilerExpression"
            self.name = "Compiler"
        else:
            self.statement = "PostfixExpression"
            self.name = tree.value.name

        for x in tree.ops:
            if x.type == "Field":
                self.append({"type": x.type, "value": Expression(self, x)})
            elif x.type == "Index":
                self.append({"type": x.type, "value": Expression(self, x.value)})
            elif x.type == "FunctionCall":
                params = []
                for y in x.values:
                    params.append(Expression(self, y))

                self.append({"type": x.type, "params": params})
            elif x.type == "CreateType":
                # dump(x.value)
                var = Var(self)
                var.collect_params(x.value.statements)
                self.append({"type": x.type, "value": var})
            elif x.type == "Deref":
                self.append({"type": x.type})
    
    def Control(self, tree: parser.Control):
        # dump(tree)
        self.statement = "Control"
        self.name = tree.kind
        self.tag = tree.tag
        if tree.value != None:
            self.value = Expression(self, tree.value)

    def Reassignment(self, tree: parser.Reassignment):
        self.statement = "Reassignment"
        self.name = Expression(self, tree.name)
        self.op = tree.op
        self.value = Expression(self, tree.value)
        # dump(tree)

    def While(self, tree: parser.While):
        self.statement = "While"
        self.tag = tree.tag
        self.op = Expression(self, tree.condition)
        self.value = Var(self)
        self.value.code_block(tree.block)

        # dump(tree.condition)
        if matches_any(["Assignment", "Reassignment"], tree.condition.type):
            if tree.condition.iter:
                self.name = "For-in"
            else:
                self.name = "For"
        else:
            self.name = "While"

    def Do(self, tree: parser.While):
        # dump(tree)
        self.statement = "Do"
        self.tag = tree.tag
        self.value = Var(self)
        self.value.code_block(tree.block)
        if tree.condition != None:
            self.op = Expression(self, tree.condition)

    def If(self, tree: parser.If, name="If"):
        # dump(tree)
        self.statement = "If"
        self.name = name

        for con in tree.conditions:
            self.append(Expression(self, con))

        self.value = Var(self)
        self.value.code_block(tree.block)
        if tree.assignment != None:
            self.out = Expression(self, tree.assignment.name)
            self.type = get_type(tree.assignment, self)

        if name == "If":
            self.tag = tree.tag
            if tree.key != None:
                self.key = Expression(self, tree.key)
            if tree.elifs != None:
                for x in tree.elifs:
                    var = Var(self)
                    var.If(x, "Elif")
                    self.elifs.append(var)
            if tree.else_block != None:
                self.els = Var(self)
                self.els.code_block(tree.else_block)

    def code_block(self, tree: parser.File):
        self.statement = "Block"
        requires = []

        for statement in tree.statements:
            var = Var(self)

            # print(statement.type)
            if statement.type == "Assignment":
                var.Assignment(statement)
            elif statement.type == "PostfixExpression":
                if statement.value.type == "Compiler" and statement.ops[0].value.name == "require":
                    requires.append(statement.ops[1].values[0].content[0].value)
                else:
                    var.PostfixExpression(statement)
            elif statement.type == "Control":
                var.Control(statement)
            elif statement.type == "Reassignment":
                var.Reassignment(statement)
            elif statement.type == "While":
                var.While(statement)
            elif statement.type == "Do":
                var.Do(statement)
            elif statement.type == "If":
                var.If(statement)
            else:
                var.statement = f"{statement.type}"
                # print(f"Error: '{statement.type}' not implemented in 'code_block' ")

            # var.print()
            self.append(var)

        return requires

    def BasicString(self, tree: parser.BasicString):
        self.statement = "String"
        self.name = "const"
        # tree.print()
        for x in tree.content:
            if x.type == "Content":
                self.append({"type": "str", "value": x.value})
            elif x.type == "BasicEscape":
                self.append({"type": "bEsc", "value": x.value})
            elif x.type == "ValueEscape":
                self.name = "format"
                self.append({"type": "vEsc", "value": Expression(self, x.value)})

    def blank_drop(self):
        self.statement = "Assignment"
        self.type = "Function"
        self.name = "__drop__"
        self.out = "_"

        var = Var(self)
        var.statement = "Unary"
        var.op = "&="
        var.append("Self")

        self.append({"name": "self", "type": var}, "self")

        self.value = Var(self)
        self.value.statement = "Block"

    def call_drop(self, name, field=None):
        self.statement = "PostfixExpression"
        self.name = "self"
        if field != None:
            self.append({"type": "Field", "value": field})
        self.append({"type": "Field", "value": "__drop__"})
        self.append({"type": "Function", "params": []})

    def match_exp(self, field):
        self.statement = "PostfixExpression"
        self.name = "self"
        self.append({"type": "Field", "value": field})

    def is_local_type(self):
        if not (self.statement == "Assignment" and self.value != None and self.value.statement == "CompilerExpression"):
            return False
        x = self.value.params.get("2")
        return x != None and x["value"] == "local"

    def is_type(self):
        return self.type == "Type"

    def is_enum(self):
        return self.type == "Enum"

    def is_macro(self):
        return self.type == "Function" and self.macro

    def is_run_macro(self):
        return self.type == "RunMacro"

    def is_function(self):
        return self.type == "Function" and not self.macro

class Analyzer:
    def __init__(self) -> None:
        self.loaded = {}
        self.files: list[Var] = []
        Any = Var()
        Any.name = "Any"
        Any.type = "Any"
        Any.drop = True
        self.types = {"Any": Any}

    def run(self, path):
        path = Path(path)
        if not path.is_file():
            print(f"'{path}' is missing")
            exit()

        if self.loaded.get(path) == None:
            print(f"loading '{path.name}'")
            self.loaded[path] = True
            var = Var()
            var.name = path

            ruff_tree = read_tree(path)
            if check_grammatical_errors(ruff_tree, path):
                exit()

            tree = parser.parse_file(ruff_tree)
            # tree.print()
            requires = var.code_block(tree)
            # var.print()
            for r in requires:
                print(f"requires '{r}'")
                
            for r in requires:
                self.run(r)

            self.files.append(var)
        else:
            print(f"'{path}' already loaded")

    def finalize(self):
        self.collect_types()

        self.mark_drop()

        # for _, type in self.types.items():
        #     type.print()

        self.inject_drops_in_files()

        self.gen_drop_fns()

        # for file in self.files:
        #     file.print()

    def get(self, typ):
        typ = self.types.get(typ)
        if typ == None:
            return None
        
        if typ.type == "Type" or typ.type == "Enum":
            return typ #return self
        
        if typ.type == "RunMacro":
            typ = self.types[typ.value.name] #get value in used macro

        return typ.value.params["0"].value.params["0"]["value"] #get value contained by macro


    def append_drops(self, parent, drop):
        # print("Type")
        # dump(drop)
        for name, val in parent.params_in_order():
            if type(val["type"]) is str:
                if self.types.get(val["type"]) != None and self.types[val["type"]].drop:
                    var = Var(drop)
                    var.call_drop("self", val["type"])

                    drop.value.append(var)

    def add_drop_to_type(self, drop):
        if drop.params.get("__drop__") == None:
            var = Var(drop)
            var.blank_drop()
            drop.append({'name': '__drop__', 'type': 'Function', 'value': var}, '__drop__')
        self.append_drops(drop, drop.params["__drop__"]["value"])

    def gen_drop_fns(self):
        for _, state in self.types.items():
            state: Var
            if state.type == "Type":
                if state.drop:
                    self.add_drop_to_type(state)
            elif state.type == "Function": #macro type
                # dump(state.value.params["0"].value.params["0"]["value"])
                if state.value.params["0"].value.name == "Type":
                    self.add_drop_to_type(state.value.params["0"].value.params["0"]["value"])
                elif state.value.params["0"].value.name == "Enum":
                    self.gen_enum_drop(state.value.params["0"].value.params["0"]["value"])

            elif state.type == "_": #instance of macro type
                if state.drop:
                    state.ex_drop = Var(state)
                    state.ex_drop.blank_drop()
                    for param in state.value.params["0"]["params"]:
                        if self.types.get(param) != None and self.types[param].drop:
                            var = Var(state.ex_drop)
                            var.call_drop("self", param)

                            state.ex_drop.value.append(var)

            elif state.type == "Enum":
                # print("Enum")
                # dump(state)
                if state.drop:
                    self.gen_enum_drop(state)
                    

    def gen_enum_drop(self, state):
        state.ex_drop = Var(state)
        state.ex_drop.blank_drop()
        match = Var(state.ex_drop)
        state.ex_drop.value.append(match)

        fields = state.params_in_order()

        match.statement = "If"
        match.name = "If"
        match.key = "self"
        match.type = "_"
        match.out = "x"

        ex = Var(match)
        ex.match_exp(fields[0][1]["name"])
        match.append(ex)

        match.value = Var(match)
        match.value.statement = "Block"
        x = Var(match.value)
        x.call_drop("x")
        match.value.append(x)

        for _, branch in fields[1:]:
            eli = Var(match)
            eli.statement = "If"
            eli.name = "Elif"
            eli.type = "_"
            eli.out = "x"

            ex = Var(match)
            ex.match_exp(branch["name"])
            eli.append(ex)

            eli.value = Var(eli)
            eli.value.statement = "Block"
            x = Var(match.value)
            x.call_drop("x")
            eli.value.append(x)
            match.elifs.append(eli)



    def inject_drops_in_files(self):
        for file in self.files:
            for _, val in file.params_in_order():
                if val.statement == "Assignment" and val.type == "Function":
                    self.find_and_inject_drops(val.value)

    def find_and_inject_drops(self, block, parent=[]):
        inject = []

        for index, val in block.params_in_order():
            if val.statement == "Assignment":
                if val.type == "Function":
                    self.find_and_inject_drops(val.value, parent + inject)
                elif self.types.get(val.type) != None:
                    if self.types[val.type].drop:
                        inject.insert(0, val.name)
            elif matches_any(["While", "Do"], val.statement):
                self.find_and_inject_drops(val.value, parent + inject)
                if val.els != None:
                    self.find_and_inject_drops(val.els, parent + inject)
            elif val.statement == "If":
                self.find_and_inject_drops(val.value, parent + inject)
                if val.els != None:
                    self.find_and_inject_drops(val.els, parent + inject)
                for x in val.elifs:
                    self.find_and_inject_drops(x.value, parent + inject)
            elif val.statement == "Control":
                if val.name == "return":
                    drop = parent + inject
                    if val.value != None:
                        if val.value in drop:
                            drop.remove(val.value)

                    self.inject_drops(block, index, drop)
                else:
                    self.inject_drops(block, index, inject)
                return
        
        self.inject_drops(block, len(block.params), inject)

        
    def inject_drops(self, block, index, drops=[]):
        i = 0
        for x in drops:
            var = Var(block)
            var.statement = "PostfixExpression"
            var.name = x
            var.append({"type": "Field", "value": "__drop__"})
            var.append({"type": "FunctionCall", "params": []})
            block.insert(var, index+i, f"{index}:drop{i}")
            i += 1

    def collect_types(self):
        for file in self.files:
            for _, val in file.params_in_order():
                if val.statement == "Assignment":
                    # dump(val)
                    if val.type == "Enum":
                        self.types[val.name] = val
                    elif val.type == "Type":
                        val.drop = val.params.get("__drop__") != None
                        self.types[val.name] = val
                    elif val.type == "Function" and val.macro:
                        # dump(val.value.params["0"].value.params["0"]["value"])
                        val.drop = val.value.params["0"].value.params["0"]["value"].params.get("__drop__") != None
                        self.types[val.name] = val
                    elif val.value.statement == "PostfixExpression" and self.types.get(val.value.name) != None:
                        val.type = "RunMacro"
                        self.types[val.name] = val

        for name, type_ in self.types.items():
            # dump(type_)
            if type_.type == "_":
                # print("here")
                self.types[type_.value.name].children[type_.name] = type_
                # dump(type_.value)
                for param in type_.value.params["0"]["params"]:
                    if self.types.get(param) != None:
                        self.types[param].children[name] = type_
            elif type_.type == "Function": # type macro
                # dump(type_.value.params["0"].value.params["0"]["value"])
                for _, param in type_.value.params["0"].value.params["0"]["value"].params.items():
                    t = param["type"]
                    if not(type(t) is Var):
                        if self.types.get(t) != None:
                            self.types[t].children[name] = type_
            else:
                for _, param in type_.params.items():
                    t = param["type"]
                    if type(t) is Var:
                        continue
                        # print("Error: macro types being used directly is currently unsupported")
                        # exit()
                        # t = t.name
                    if self.types.get(t) != None:
                        self.types[t].children[name] = type_
                        
    def mark_drop(self):
        for name, type in self.types.items():
            rec_mark(type)

def rec_mark(type):
    if type.drop:
        for name, child in type.children.items():
            child.drop = True
            rec_mark(child)

def read_tree(filename):
    with open(filename, "rb") as f:
        return tree_parser.parse(f.read())

def check_grammatical_errors(tree, file):
    query = MUNYA_LANGUAGE.query("(ERROR) @err")
    captures = query.captures(tree.root_node)

    if len(captures) > 0:
        print(f"grammatical errors found in {file}:")
        print("------------------------------------------------------------------")
        for v in captures["err"]:
            point = v.start_point
            print(f"at: row={point.row+1} column={point.column+1}")
            print(f'value: "{str(v.text, encoding='utf-8')}"')
            print("------------------------------------------------------------------")

        return True
    return False

#converts a lone table into a postfix starting with Table
def table_postfix(table):
    p = parser.PostfixExpression()
    p.value = parser.Ident()
    p.value.name = "Table"

    t = parser.Postfix()
    t.type = "CreateType"
    t.value = table
    p.ops = [t]

    return p
