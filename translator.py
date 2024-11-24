import analyzer
from misc import matches_any, dent, dump
from pathlib import Path
import build

OPS = {
    "+"  : "__add__",
    "-"  : "__sub__",
    "*"  : "__mul__",
    "/"  : "__div__",
    "%"  : "__mod__",
    "&&" : "__b_and__",
    "||" : "__b_or__",
    "^"  : "__b_xor__",
    "<<" : "__b_shl__",
    ">>" : "__b_shr__",
    "==" : "__eq__",
    "!=" : "__n_eq__",
    "<=" : "__lt_eq__",
    ">=" : "__gt_eq__",
    "<"  : "__lt__",
    ">"  : "__gt__",
    "and": "__and__",
    "or" : "__or__",
    ".." : "__range__",
    "..=": "__i_range__",
    ";>" : "__c_type__",
    "not": "__not__",
    "-"  : "__neg__",
    "~"  : "__b_not__",

    "="  : "__copy__",
    "+="  : "__add_a__",
    "-="  : "__sub_a__",
    "*="  : "__mul_a__",
    "/="  : "__div_a__",
    "%="  : "__mod_a__",
    "&&=" : "__b_and_a__",
    "||=" : "__b_or_a__",
    "^="  : "__b_xor_a__",
    "<<=" : "__b_shl_a__",
    ">>=" : "__b_shr_a__",
}

def title(name, symbol):
    buffer = 50 - (len(name)//2)
    return f"//{symbol * buffer} {name} {symbol * (buffer - len(name)%2)}\n"

class Writer:
    def __init__(self, file) -> None:
        self.buffers = []
        build.make_dir(Path(file), file=True)
        self.file = open(file, "wb")

    def finalize(self):
        self.file.close()

    def write(self, out):
        self.file.write(str.encode(out))

    def new_buffer(self):
        self.buffers.append("")

    def buffer(self, out, index=0):
        self.buffers[-1-index] += out

    def dump(self, index=0):
        self.write(self.buffers[-1-index])
        self.buffers.pop(-1-index)

    def seek(self, len):
        self.file.seek(len, 1)

    def over_write(self, len, val):
        self.seek(-len)
        self.write(val)

class Translator:
    def __init__(self, out, analyzer_) -> None:
        self.natives = {}

        self.out = Writer(out)
        self.info: analyzer.Analyzer = analyzer_

    def run(self):
        self.out.write(title("Transpiled Using Munya Bootstrap compiler", "+"))
        self.out.write("//Expect jank and bugs.\n")
        self.out.write("//This compiler is very dumb and does very few sanity checks.\n")
        self.out.write("//Its recommended to check this generated c with a LSP/IDE.\n")

        self.pre_collect()

        self.out.write("\n" + title("Includes Start", "="))
        self.includes()
        self.out.write(title("Includes End", "="))

        self.out.write("\n" + title("Type Macros Start", "="))
        self.macros()
        self.out.write(title("Type Macros End", "="))

        self.out.write("\n" + title("Type Declarations Start", "="))
        self.types()
        self.out.write(title("Type Declarations End", "="))

        self.out.write("\n" + title("Function Declarations Start", "="))
        self.fn_dec()
        self.out.write(title("Function Declarations End", "="))

        self.out.write("\n" + title("Functions Start", "="))
        self.fn()
        self.out.write(title("Functions End", "="))

        self.out.finalize()

    def pre_collect(self):
        for file in self.info.files:
            for name, state in file.params_in_order():
                if state.is_local_type():
                    self.natives[state.name] = state.value.params["3"]["params"][0].params["0"]["value"]

    def includes(self):
        requires = {
            "<inttypes.h>": "Auto",
            "<stdlib.h>": "Auto",
            "<stdbool.h>": "Auto",
        }

        self.out.write(title(f"Auto", "-"))
        self.out.write("#include <inttypes.h>\n")
        self.out.write("#include <stdlib.h>\n")
        self.out.write("#include <stdbool.h>\n")

        for file in self.info.files:
            self.out.write(title(f"{Path(file.name).name}", "-"))
            for name, state in file.params_in_order():
                # dump(state)
                if state.statement == "CompilerExpression":
                    # dump(state.params["3"]["params"][0])
                    r = state.params["3"]["params"][0].params["0"]["value"]
                    # print(r)
                    if requires.get(r) == None:
                        requires[r] = file.name
                        self.out.write(f"#include {r}\n")

    def format_type(self, var, parent="SELF"):
        ref = ""
        val = ""
        if type(var) is analyzer.Var:
            val = var.params["0"]
            ref = "*"
        else:
            val = var

        check = val
        if val == "Self":
            val = self.format_type(parent)

        x = self.info.types.get(val)
        native = self.natives.get(val)
        if native != None:
            x = native
        else:
            if (x != None or val.endswith("##")):
                x = f"{val}_MU_struct"
            else:
                x = val
        
        return f"{x}{ref}"
    
    def macros(self):
        for file in self.info.files:
            self.out.write(title(f"{Path(file.name).name}", "-"))
            for name, state in file.params_in_order():
                if state.is_macro():
                    self.write_macro(state)

    def write_macro(self, state):
        params = {}
        params_str = f"MU_NAME"
        for _, p in state.params_in_order():
            params[p["name"]] = True
            params_str += f", {p["name"]}"

        typ = state.value.params["0"].value.params["0"]["value"]
        typ.name = state.name
        # print(typ)
        self.out.write(f"#define {state.name}_MU_type({params_str})\\\n")
        if state.value.params["0"].value.name == "Type":
            self.write_type(typ, d=1, macro="\\")
            self.out.write(f"#define {state.name}_MU_dec({params_str})\\\n")
            self.write_type_fn(typ, d=1, macro="\\", dec=";")
            self.out.over_write(2, "\n") #remove trailing \
            self.out.write(f"#define {state.name}_MU_fn({params_str})\\\n")
            self.write_type_fn(typ, d=1, macro="\\")
            self.out.over_write(2, "\n")
        elif state.value.params["0"].value.name == "Enum":
            self.write_enum(typ, d=1, macro="\\")
            self.out.write(f"#define {state.name}_MU_dec({params_str})\\\n")
            self.write_enum_fn(typ, d=1, macro="\\", dec=";")
            self.out.over_write(2, "\n")
            self.out.write(f"#define {state.name}_MU_fn({params_str})\\\n")
            self.write_enum_fn(typ, d=1, macro="\\")
            self.out.over_write(2, "\n")

    def types(self):
        # self.out.write(title(f"Auto Generated", "-"))
        # self.out.write("typedef struct Any_MU_struct{\n")
        # self.out.write(dent(1, "uint64_t tag;"))
        # self.out.write(dent(1, "void* value;"))
        # self.out.write("}Any_MU_struct;\n")

        # self.out.write("enum Any_MU_enum{\n")
        # self.out.write(dent(1, f"Any_MU_tag__,"))
        # for name, type in self.info.types.items():
        #     if type.type != "Function":
        #         self.out.write(dent(1, f"Any_MU_tag_{name},"))
        # for name, _ in self.natives.items():
        #     self.out.write(dent(1, f"Any_MU_tag_{name},"))
        # self.out.write("};\n")

        for file in self.info.files:
            self.out.write(title(f"{Path(file.name).name}", "-"))
            for name, state in file.params_in_order():
                # print(state)
                if state.is_type():
                    self.write_type(state)
                elif state.is_enum():
                    self.write_enum(state)
                elif state.is_run_macro():
                    self.write_macro_use(state, "type")

    def write_type(self, state, d=0, macro=""):
        # print(state)
        self.out.write(dent(d, f"typedef struct {state.name}_MU_struct{{{macro}"))
        for _, field in state.params_in_order():
            if field["type"] != "Function":
                self.out.write(dent(d+1, f"{self.format_type(field["type"])} {field["name"]};{macro}"))
        self.out.write(dent(d, f"}}{state.name}_MU_struct;"))

    def write_enum(self, state, d=0, macro=""):
        # print(state)
        self.out.new_buffer()
        self.out.write(dent(d, f"typedef struct {state.name}_MU_struct{{{macro}"))
        self.out.buffer(dent(d, f"enum {state.name}_MU_enum{{{macro}"))

        self.out.write(dent(d+1, f"uint64_t tag;{macro}"))
        self.out.write(dent(d+1, f"union {{{macro}"))

        for _, field in state.params_in_order():
            if field["name"] != "_":
                self.out.write(dent(d+2, f"{self.format_type(field["type"])} {field["name"]};{macro}"))
            self.out.buffer(dent(d+1, f"{state.name}_MU_tag_{field["name"]},{macro}"))
        pass

        self.out.write(dent(d+1, f"}} value;{macro}"))
        self.out.write(dent(d, f"}}{state.name}_MU_struct;{macro}"))
        self.out.buffer(dent(d, "};"))

        self.out.dump()

    def write_macro_use(self, state, mode):
        # print(state)
        params = ""
        for x in state.value.params["0"]["params"]:
            params += f", {self.format_type(x)}"
        self.out.write(f"{state.value.name}_MU_{mode}({state.name}{params})\n")

    def fn_dec(self):
        for file in self.info.files:
            self.out.write(title(f"{Path(file.name).name}", "-"))
            for name, state in file.params_in_order():
                # dump(state)
                if state.is_function():
                    self.write_fn(state, dec=";")
                elif state.is_type():
                    self.write_type_fn(state, dec=";")
                elif state.is_enum():
                    self.write_enum_fn(state, dec=";")
                elif state.is_run_macro():
                    self.write_macro_use(state, "dec")

        # self.out.write(title(f"Auto Generated", "-"))

    def fn(self):
        for file in self.info.files:
            self.out.write(title(f"{Path(file.name).name}", "-"))
            for name, state in file.params_in_order():
                # dump(state)
                if state.is_function():
                    self.write_fn(state)
                elif state.is_type():
                    self.write_type_fn(state)
                elif state.is_enum():
                    self.write_enum_fn(state)
                elif state.is_run_macro():
                    self.write_macro_use(state, "fn")

        # self.out.write(title(f"Auto Generated", "-"))

    def write_type_fn(self, state, d=0, macro="", dec="{"):
        # print(state)
        for _, field in state.params_in_order():
            if field["type"] == "Function":
                # print(field["value"])
                self.write_fn(field["value"], state.name, d=d, macro=macro, dec=dec)

    def write_enum_fn(self, state, d=0, macro="", dec="{"):
        # print(state.ex_drop)
        if state.ex_drop != None:
            self.write_fn(state.ex_drop, state.name, d=d, macro=macro, dec=dec)


    def format_fn(self, fn, parent=""):
        name = fn
        native = self.natives.get(name)
        if native != None:
            return native
        if name == "main":
            ret = "int"
        else:
            if parent != "":
                name = f"{parent}_MU_fn_{name}"
            else:
                name = f"{name}_MU"
        return name

    def write_fn(self, state, parent="", d=0, macro="", dec="{"):
        # print(state)
        name = self.format_fn(state.name, parent)
        
        scope = Scope()
        params = ""
        for _, x in state.params_in_order():
            if x["name"] == "self":
                # print(state.parent.name)
                if type(x["type"]) is analyzer.Var:
                    x["type"].params["0"] = state.parent.name
                else:
                    x["type"] = state.parent.name
                # print(x["type"])
            scope.new_var(x["name"], x["type"])
            typ = self.format_type(x["type"], parent)
            if macro != "":
                typ = "MU_NAME##"
            params += f", {typ} {x["name"]}"

        if params == "":
            params = "void"
        else:
            params = params[2:]

        ret = self.format_type(state.out)
        if name == "main":
            ret = "int"
        elif ret == "_":
            ret = "void"

        self.out.write(dent(d, f"{ret} {name}({params}){dec}{macro}"))
        if dec != "{":
            return
        
        self.write_block(state.value, scope, d=d+1, macro=macro)
        self.out.write(dent(d, f"}}{macro}"))

    def write_block(self, state, scope, d=0, macro=""):
        # print(state)
        for _, val in state.params_in_order():
            self.write_statement(val, scope, d=d, macro=macro)

    def write_statement(self, state, scope, d=0, macro=""):
        # print(state)
        if state.statement == "Assignment":
            exp = ""
            extra = []
            if type(state.value) is analyzer.Var or state.value != "_":
                scope.new_var(state.name, state.type)
                (main, extra) = self.write_exp(state.value, scope, state.name)
                if main != "":
                    exp = f"= {main}"
            
            self.out.write(dent(d, f"{self.format_type(state.type)} {state.name} {exp};{macro}"))
            for val in extra:
                self.out.write(dent(d, f"{val}{macro}"))
        elif state.statement == "Comment":
            pass
        elif state.statement == "Reassignment":
            if type(state.name) is analyzer.Var and self.post_type(state.name, scope, -1) == "<Index>":
                self.out.write(dent(d, f"{self.write_index(state.name, scope, set=state.value)[0]};{macro}"))
            elif self.has_OP(state.name, state.op, scope):
                lt, name = self.end_type(state.name, scope)
                fn = lt.params[OPS[state.op]]["value"].params_in_order()
                refs = ["", ""]
                for i in range(2):
                    if type(fn[i][1]["type"]) is analyzer.Var:
                        refs[i] = "&"
                self.out.write(dent(d, 
                    f"{name}_MU_fn_{OPS[state.op]}({refs[0]}{self.write_exp(state.name, scope)[0]}, {refs[1]}{self.write_exp(state.value, scope)[0]});{macro}"
                ))
            else:
                self.out.write(dent(d, f"{self.write_exp(state.name, scope)[0]} {state.op} {self.write_exp(state.value, scope)[0]};{macro}"))
        elif state.statement == "If":
            self.write_if(state, scope, d, macro)
        elif state.statement == "While":
            self.write_while(state, scope, d, macro)
        elif state.statement == "Do":
            self.write_do(state, scope, d, macro)
        elif state.statement == "Control":
            self.write_control(state, scope, d, macro)
        else:
            self.out.write(dent(d, f"{self.write_exp(state, scope)[0]};{macro}"))

    def write_control(self, state, scope, d=0, macro=""):
        # print(state)
        val = ""
        if state.value != None:
            val = f" {self.write_exp(state.value, scope)[0]}"
        self.out.write(dent(d, f"{state.name}{val};{macro}"))


    def if_express(self, key, state, scope, enum):
        if key == None:
            return self.write_exp(state.params["0"], scope)[0]
        else:
            out = ""
            key = self.write_exp(key, scope)[0]
            if enum:
                key += ".tag"
            for _, val in state.params_in_order():
                out += f"{key} == {self.write_exp(val, scope)[0]} || "
            return out[:-4]

    def write_if(self, state, scope, d=0, macro=""):
        # print(state.params["0"])
        enum = state.out != None

        self.out.write(dent(d, f"if({self.if_express(state.key, state, scope, enum)}){{{macro}"))
        scope.new_scope()
        if enum:
            t = self.end_type(state.params["0"], scope)[1]
            scope.new_var(state.out, t)
            self.out.write(dent(d+1, f"{self.format_type(t)} {state.out} = {state.key}.value.{state.params["0"].params["0"]["value"]};{macro}"))
        self.write_block(state.value, scope, d+1, macro)
        scope.remove_scope()
        self.out.write(dent(d, f"}}{macro}"))

        for el in state.elifs:
            self.out.write(dent(d, f"else if({self.if_express(state.key, el, scope, enum)}){{{macro}"))
            scope.new_scope()
            if enum:
                t = self.end_type(el.params["0"], scope)[1]
                scope.new_var(el.out, t)
                self.out.write(dent(d+1, f"{self.format_type(t)} {el.out} = {state.key}.value.{el.params["0"].params["0"]["value"]};{macro}"))
            self.write_block(el.value, scope, d+1, macro)
            scope.remove_scope()
            self.out.write(dent(d, f"}}{macro}"))

        if state.els != None:
            self.out.write(dent(d, f"else {{{macro}"))
            scope.new_scope()
            self.write_block(state.els, scope, d+1, macro)
            scope.remove_scope()
            self.out.write(dent(d, f"}}{macro}"))

    def write_while(self, state, scope, d=0, macro=""):
        # print(state)

        scope.new_scope()
        if state.name == "While":
            self.out.write(dent(d, f"while({self.write_exp(state.op, scope)[0]}){{{macro}"))
        else:
            exp = f"{self.write_exp(state.op.value, scope)[0]}"
            if state.name == "For-in":
                typ, name = self.end_type(state.op.value, scope)
                if typ.params.get("next") != None:
                    exp = f"{name}_MU_fn_next(&{state.op.value})"
                else:
                    num = scope.auto()
                    self.out.write(dent(d, f"{self.format_type(typ.params["iter"]["value"].out)} MU_auto_{num} = {name}_MU_fn_iter(&{state.op.value});{macro}"))
                    exp = f"{typ.params["iter"]["value"].out}_MU_fn_next(&MU_auto_{num})"

            start = f"{self.format_type(state.op.type)} {state.op.name} = {exp}"
            check = f"{state.op.name}.tag != {state.op.type}_MU_tag__"
            inc = f"{state.op.name} = {exp}"
            self.out.write(dent(d, f"for({start}; {check}; {inc}){{{macro}"))
        
        self.write_block(state.value, scope, d+1, macro)
        self.out.write(dent(d, f"}}{macro}"))
        scope.remove_scope()

    def write_do(self, state, scope, d=0, macro=""):
        # print(state)
        scope.new_scope()
        if state.op == None:
            self.out.write(dent(d, f"{{{macro}"))
            self.write_block(state.value, scope, d+1, macro)
            self.out.write(dent(d, f"}}{macro}"))
        else:
            self.out.write(dent(d, f"do {{{macro}"))
            self.write_block(state.value, scope, d+1, macro)
            self.out.write(dent(d, f"}} while({self.write_exp(state.op, scope)[0]});{macro}"))

        scope.remove_scope()

    def has_OP(self, state, op, scope):
        dunder = OPS.get(op)
        if dunder == None:
            return False
        typ = self.end_type(state, scope)
        if typ == None:
            return False
        typ = typ[0]
        if typ == None:
            return False
        return typ.params.get(dunder) != None
    
    def end_type(self, state, scope):
        name = None
        if type(state) is analyzer.Var:
            name = self.post_type(state, scope, -1)
        else:
            name = scope.get(state)
        if name == None:
            return None
        typ = self.info.get(name)
        # print(typ)
        if typ == None:
            return (None, self.natives.get(name))
        return (typ, name)

    def write_exp(self, state, scope, var="ERR"):
        # print(state)
        main = None

        if type(state) is str:
            main = self.format_type(state)
        elif state.statement == "Binary":
            left = self.write_exp(state.params["left"], scope)[0]
            right = self.write_exp(state.params["right"], scope)[0]
            if self.has_OP(state.params["left"], state.op, scope):
                lt, name = self.end_type(state.params["left"], scope)
                fn = lt.params[OPS[state.op]]["value"].params_in_order()
                refs = ["", ""]
                for i in range(2):
                    if type(fn[i][1]["type"]) is analyzer.Var:
                        refs[i] = "&"

                main = f"{name}_MU_fn_{OPS[state.op]}({refs[0]}{left}, {refs[1]}{right})"
            else:
                main = f"{left} {state.op} {right}"
        elif state.statement == "Unary":
            val = self.write_exp(state.params["0"], scope)[0]
            if self.has_OP(state.params["0"], state.op, scope):
                lt, name = self.end_type(state.params["0"], scope)
                fn = lt.params[OPS[state.op]]["value"].params_in_order()
                ref = ""
                if type(fn[0][1]["type"]) is analyzer.Var:
                    ref = "&"
                main = f"{name}_MU_fn_{OPS[state.op]}({ref}{val})"
            elif state.op == "&=" or state.op == "&:":
                main = f"&{val}"
            else:
                main = f"{state.op}{val}"
        elif state.statement == "Parentheses":
            main = f"({self.write_exp(state.params["0"], scope)[0]})"
        elif state.statement == "PostfixExpression":
            return self.write_post(state, scope, var)
        elif state.statement == "String":
            return self.write_string(state, scope, var)
        elif state.statement == "CompilerExpression" and state.params["2"]["value"] == "cast":
            t = state.params["3"]["params"]
            # print(t)
            return (f"(({self.format_type(t[0])}){self.write_exp(t[1], scope, var)[0]})", [])

        return (main, [])
    
    def write_string(self, state, scope, var):
        main = ""
        extra = []

        # print(state)
        if scope.get(var) == "String":
            main = "String_MU_fn___new__()"
            mode = ""
            buffer = ""
            for _, val in state.params_in_order():
                if matches_any(["str", "bEsc"], val["type"]):
                    if matches_any(["str", "bEsc"], mode):
                        mode = val["type"]
                        buffer += val["value"]
                    else:
                        mode = val["type"]
                        buffer = val["value"]
                else:
                    if matches_any(["str", "bEsc"], mode):
                        num = scope.auto()
                        # extra.append(f'char* MU_auto_{num} = "{buffer}";')
                        extra.append(f'String_MU_fn_append_c(&{var}, "{buffer}");')
                    
                    mode = val["type"]
                    ref = "&"
                    if type(scope.get(val["value"])) is analyzer.Var:
                        ref = ""
                    if scope.get(val["value"]) == "String":
                        extra.append(f'String_MU_fn_append(&{var}, {ref}{val["value"]});')
                    elif scope.get(val["value"]) == "CString":
                        extra.append(f'String_MU_fn_append_c(&{var}, {val["value"]});')
                    else:
                        num = scope.auto()
                        extra.append(f'char* MU_auto_{num} = {scope.get(val["value"])}_MU_fn_to_cstring({ref}{val["value"]});')
                        extra.append(f'String_MU_fn_append_c_temp(&{var}, MU_auto_{num});')
                        extra.append(f'free(MU_auto_{num});')
            if matches_any(["str", "bEsc"], mode):
                num = scope.auto()
                # extra.append(f'char* MU_auto_{num} = ;')
                extra.append(f'String_MU_fn_append_c(&{var}, "{buffer}");')
        else:
            main = '"'
            for _, val in state.params_in_order():
                # print(val["value"])
                main += val["value"]
            main += '"'
        
        return (main, extra)

    def post_type(self, state, scope, index=0):
        # print(f"post_type: {state}")
        p_type = scope.get(state.name)
        if p_type == None and self.info.get(state.name):
            p_type = state.name
        # print(f"type: {p_type}")
        if index == 0:
            return p_type
        params = state.params_in_order()
        if index < 0:
            # print(f"{len(params)}{index}")
            index = len(params) + (index+1)
            if index == 0:
                return p_type
            # print(index)
            # if matches_any(["Index", "FunctionCall"], params[index-1][1]["type"]):
            #     index -= 1
        for i in range(index):
            # print(i)
            if type(p_type) is analyzer.Var:
                p_type = p_type.params["0"]
            p = self.info.get(p_type)
            # print(p_type)
            if p == None:
                return f"<{p_type}>"
            elif params[i][1]["type"] == "Index":
                return "<Index>"
            # print(params[i][1])
            # print(p)
            p_type = p.params[params[i][1]["value"]]["type"]
        return p_type
    
    def inject_self_func(self, state, scope):
        out = ""
        params = state.params_in_order()
        offset = -2
        ref = False

        func = None
        if len(params) == 1:
            offset = -1
            typ = self.post_type(state, scope, 0)
            func = self.info.get(typ).params["__new__"]["value"].params.get("self")
            ref = True
        else:
            name = params[-2][1]["value"]
            # print(name)
            typ = self.post_type(state, scope, -3)
            # print(f"t:{typ}")
            if type(typ) is analyzer.Var:
                ref = True
                typ = typ.params["0"]

            func = self.info.get(typ).params[name]["value"].params.get("self")
        
        # print(func)
        if func != None:
            if type(func["type"]) is analyzer.Var and not ref:
                out += "&"
            out += state.name
            for i in range(len(params)+offset):
                s = "."
                if type(self.post_type(state, scope, i)) is analyzer.Var:
                    s = "->"
                out += f"{s}{params[i][1]["value"]}"
            out += ", "
        return out

    def write_post(self, state, scope, var):
        # print(state)

        main = state.name
        i = 0
        for _, field in state.params_in_order():
            i += 1
            if field["type"] == "Field":
                s = "."
                par_name = self.post_type(state, scope, i-1)
                if type(par_name) is analyzer.Var:
                    par_name = par_name.params["0"]
                par_type = self.info.get(par_name)
                if par_type != None and par_type.type == "Enum":
                    return (f"{par_name}_MU_tag_{field["value"]}", [])
                elif self.post_type(state, scope, i) != "Function" and type(self.post_type(state, scope, i-1)) is analyzer.Var:
                    s = "->"
                main += f"{s}{field["value"]}"
            elif field["type"] == "Index":
                if self.info.get(self.post_type(state, scope, i-1)) != None:
                    return self.write_index(state, scope, var)
                main += f"[{self.write_exp(field["value"], scope, var)[0]}]"
            elif field["type"] == "FunctionCall":
                return self.write_func_call(state, scope, var)
            elif field["type"] == "CreateType":
                return self.init_type(state, scope, var)
            elif field["type"] == "Deref":
                main = f"(*{main})"

        return (main, [])
    
    def inject_self_index(self, state, scope):
        out = f"&{state.name}"
        params = state.params_in_order()
        for i in range(len(params)-2):
            s = "."
            if type(self.post_type(state, scope, i)) is analyzer.Var:
                s = "->"
            out += f"{s}{params[i][1]["value"]}"
        out += ", "
        return out
    
    def write_index(self, state, scope, var="ERR", set=None):
        params = state.params_in_order()
        val = None
        if len(params) < 2:
            val = self.post_type(state, scope, 0)
        else:
            val = self.post_type(state, scope, -2)
            
        func = "__get_index__"
        if set != None:
            func = "__set_index__"

        main = f"{val}_MU_fn_{func}"

        buffer = self.inject_self_index(state, scope)
        buffer += f"{self.write_exp(params[-1][1]["value"], scope, var)[0]}, "
        if set != None:
            buffer += f"{self.write_exp(set, scope, var)[0]}, "
        if buffer != "":
            buffer = buffer[:-2]
        main += f"({buffer})"

        return (main, [])

    def write_func_call(self, state, scope, var="ERR"):
        # print(state)
        params = state.params_in_order()

        main = self.format_fn(state.name)
        buffer = ""
        # print(state.name, scope.get(state.name))
        get = scope.get(state.name)
        if type(get) is analyzer.Var:
            get = get.params["0"]
        # print(get)
        if self.info.get(state.name) != None or self.info.get(get) != None:
            val = None
            func = None
            if len(params) == 1:
                val = self.post_type(state, scope, 0)
                func = "__new__"
            else:
                val = self.post_type(state, scope, -3)
                if type(val) is analyzer.Var:
                    val = val.params["0"]
                func = params[-2][1]["value"]

            # print(val)
            if val == "<Self>":
                val = "MU_NAME##"
            main = f"{val}_MU_fn_{func}"
            buffer += self.inject_self_func(state, scope)

        for x in params[-1][1]["params"]:
            buffer += f"{self.write_exp(x, scope, var)[0]}, "
        if buffer != "":
            buffer = buffer[:-2]
        main += f"({buffer})"

        return (main, [])

    def init_type(self, state, scope, var):
        main = ""
        extra = []

        last = state.params_in_order()[-1][1]["value"]
        t = None
        for _, val in last.params_in_order():
            if val.get("index") != None:
                if t == "name":
                    print("Error: type created with fields and indexes.")
                    exit()
                t = "index"
            elif val.get("name") != None:
                if t == "index":
                    print("Error: type created with fields and indexes.")
                    exit()
                t = "name"
        if t == None:
            return ("{}", extra)
        # print(last)
        
        if t == "name":
            main = "{"
            v = None
            nil = None
            for _, val in last.params_in_order():
                v = val[t]
                nil = val.get("value")
                main += f".{val[t]} = {self.write_exp(val.get("value", ""), scope)[0]}, "
            main += "}"
            if self.info.get(state.name) != None and self.info.get(state.name).type == "Enum":
                if nil == None:
                    main = f"{{.tag = {state.name}_MU_tag_{v}}}"
                else:
                    main = f"{{.tag = {state.name}_MU_tag_{v}, .value = {main}}}"
        else:
            main = f"{state.name}_MU_fn___new__({len(last.params)})"
            for _, val in last.params_in_order():
                extra.append(f"{state.name}_MU_fn___set_index__(&{var}, {val[t]}, {self.write_exp(val["value"], scope)[0]});")

        return (main, extra)

class Scope:
    def __init__(self) -> None:
        self.auto_ = 0
        self.scopes = [{}]

    def new_scope(self):
        self.scopes.append({})

    def remove_scope(self):
        self.scopes.pop()

    def new_var(self, var, type):
        self.scopes[-1][var] = type

    def get(self, var):
        for scope in reversed(self.scopes):
            # print(scope)
            f = scope.get(var)
            if f != None:
                return f
    
    def auto(self):
        t = self.auto_
        self.auto_ += 1
        return t