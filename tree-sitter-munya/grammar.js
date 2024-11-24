const PREC = {
    OR:         1,  // or
    AND:        2,  // and
    RANGE:      3,  
    COMPARE:    4,  // < > <= >= != ==
    BIT:        5,  // && || ^^
    BIT_SHIFT:  6,  // << >>
    PLUS:       7,  // + -
    MULTI:      8,  // * / %
    EXPO:       9,  // ^
    UNARY:      10, // not - ~
    TYPE:       11  // :
};

const BINARY_OPS_1 = [
    ["+",  PREC.PLUS     ], //addition          //add interfaces
    ["-",  PREC.PLUS     ], //subtraction       //sub interface
    ["*",  PREC.MULTI    ], //multiplication
    ["/",  PREC.MULTI    ], //division
    ["%",  PREC.MULTI    ], //remainder
    ["^",  PREC.EXPO     ], //exponent
    ["&&", PREC.BIT      ], //bit and | type and
    ["||", PREC.BIT      ], //bit or | type or  //create Enum
    ["^^", PREC.BIT      ], //bit xor
    ["<<", PREC.BIT_SHIFT], //bit shift left
    [">>", PREC.BIT_SHIFT], //bit shift right
]

const BINARY_OPS_2 = [
    ["==",  PREC.COMPARE], //equality
    ["!=",  PREC.COMPARE], //inequality
    ["<=",  PREC.COMPARE], //lesser or equal
    [">=",  PREC.COMPARE], //greater or equal
    ["<",   PREC.COMPARE], //less than
    [">",   PREC.COMPARE], //greater than
    ["and", PREC.AND    ], //and
    ["or",  PREC.OR     ], //or
    ["..",  PREC.TYPE   ], //range
    ["..=", PREC.TYPE   ], //inclusive range
    [";",   PREC.TYPE   ], //type assertion 
    [";~",  PREC.TYPE   ], //type interface 
    [";>",  PREC.TYPE   ], //type conversion 
]

const UNARY_OPS = [
    ["not", PREC.UNARY], //not
    ["-",   PREC.UNARY], //negation
    ["~",   PREC.UNARY], //bit not
    ["&=",  PREC.UNARY], //var ref
    ["&:",  PREC.UNARY], //const ref
]

//keywords
//fn if else elif do while for in and or not return break continue
//Type Fn Enum Error Quantum


const list = (rule) => optional(seq(rule, repeat(seq(',', rule)), optional(',')))
const list1 = (rule) => seq(rule, repeat(seq(',', rule)), optional(','))

const string = ($, start, content, escapes) => seq(
    alias(start, $.quot),
    repeat(choice(
        alias((token.immediate(content)), $.content),
        alias('\\' + start, $.quot_escape),
        ...escapes
    )),
    alias(start, $.quot)
)

const table_internals = ($) => list(choice(
    prec(2, $.param),
    prec(2, $.reassignment),
    prec(1, $.expression),
))

module.exports = grammar({
    name: 'munya',
  
    word: $ => $.identifier,

    extras: $ => [$.comment, /\s/],

    rules: {
        source_file: $ => seq(
            optional(alias(/#![^\r\n]*/, $.shebang)),
            repeat($._func_statements),
        ),

        _func_statements: $ => choice(
            $.assignment,
            $.reassignment,
            $._control_flow,
            $.control,
            $.expression,
        ),

        tag: $ => seq(
            "<",
            alias(/[^\p{Control}\s+\-*/%^#&~|<>=(){}\[\];:,.\\'"]+/, $.tag),
            ">",
        ),

        control: $ => prec.right(1, seq(
            alias(choice("return", "break", "continue"), $.keyword),
            optional($.tag),
            optional($.expression)
        )),

        block: $ => seq(
            "{",
            repeat($._func_statements),
            '}'
        ),

        _types_funcs: $ => choice(
            alias(";", $.assert),
            alias(";~", $.interface),
            alias(";>", $.conversion),
        ),

        type_data: $ => seq(
            $._types_funcs,
            optional($.expression),
        ),

        req_type_data: $ => seq(
            $._types_funcs,
            $.expression,
        ),

        multi_set: $ => seq(
            "(",
            list1($._assignment_names),
            ")"
        ),

        _assign_start: $ => seq(
            field("name", choice(
                $._assignment_names,
                $.multi_set,
            )),
            $.type_data,
            choice(
                alias(":", $.const),
                alias("=", $.var),
            ),
        ),

        assignment: $ => seq(
            optional(alias("pub", $.pub)),
            $._assign_start,
            optional(alias("in", $.in)),
            field("value", $._assignment_types),
        ),

        deconstruction: $ => seq(
            "{",
            table_internals($),
            "}",
        ),
        
        reassignment: $ => seq(
            field("name", choice(
                $._assignment_names,
                $.multi_set,
                $.deconstruction
            )),
            alias(
                choice(
                    "=",
                    ...BINARY_OPS_1.map(([operator, precedence]) => operator + "=")
                ),
                $.op
            ),
            optional(alias("in", $.in)),
            $._assignment_types,
        ),

        param: $ => prec.right(seq(
            optional(alias("pub", $.pub)),
            field("name", $._assignment_names),
            optional(seq(
                $.type_data,
                optional(seq(
                    choice(
                        alias(":", $.const),
                        alias("=", $.var),
                    ),
                    optional(alias("in", $.in)),
                    optional(field("value", $._assignment_types)),
                ))
            )),
        )),

        _assignment_types: $ => choice(
            $.function,
            $.expression,
            $.multi_string,
            $._control_flow,
        ),

        //lets keywords to be assigned to inside of types
        _rouge_identifier: $ => prec(-1, alias(choice(
            "and",
            "or",
            "not",
            "true",
            "false",
            "if",
            "elif",
            "else",
            "do",
            "while",
            "in",
            "pub",
            "fn",
            "Fn",
        ), $.identifier)),

        _assignment_names: $ => prec(1, choice(
            $._rouge_identifier,
            $._table_values,
            $.identifier,
            $.postfix_expression
        )),

        expression: $ => choice(
            $._literal,
            $._table_values,
            $.identifier,
            $.postfix_expression,
            $.binary_expression,
            $.unary_expression,
            $.parenthesized_expression,
        ),

        parenthesized_expression: $ => seq('(', $.expression, ')'),

        binary_expression: $ => choice(
            ...BINARY_OPS_1.concat(BINARY_OPS_2).map(([operator, precedence]) =>
                prec.left(
                    precedence,
                    seq(
                        field('left', $.expression),
                        alias(operator, $.op),
                        field('right', $.expression)
                    )
                )
            )
        ),

        unary_expression: $ => choice(
            ...UNARY_OPS.map(([operator, precedence]) => prec.left(
                precedence,
                seq(
                  alias(operator, $.op),
                  field('value', $.expression)
                )
            )),
        ),

        _table_values: $ => choice(
            $.index,
            $.field_index,
            $.insert_field_index,
            $.field,
            $.insert_field,
        ),

        _postfix_functions: $ => choice(
            $.function_call,
            $.get_type,
            $.create_type,
            $.deref,
            $._table_values,
        ),

        get_type: $ => "?",
        deref: $ => ".*",

        function_call: $ => seq(
            '(',
            list(choice(
                $.reassignment,
                $._assignment_types
            )),
            ')'
        ),

        index: $ => seq(
            '[',
            $.expression,
            ']'
        ),

        field_index: $ => seq(
            '.[',
            $.expression,
            ']'
        ),

        insert_field_index: $ => seq(
            '.>[',
            $.expression,
            ']'
        ),

        field: $ => seq(
            '.',
            $.identifier
        ),

        insert_field: $ => seq(
            '.>',
            $.identifier
        ),

        create_type: $ => seq(
            $.table,
        ),

        postfix_expression: $ => prec(1, seq(
            choice(
                $._assignment_names,
                $._literal,
                $.parenthesized_expression
            ),
            $._postfix_functions,
        )),

        function_sig: $ => seq(
            alias('Fn', $.keyword),
            optional(alias("!", $.macro)),
            $.parameter_list,
            $.req_type_data,
        ),

        function: $ => seq(
            alias('fn', $.keyword),
            optional(alias("!", $.macro)),
            optional(seq(
                "<",
                alias($.expression, $.priority),
                ">",
            )),
            $.parameter_list,
            optional($.req_type_data),
            $.block,
        ),

        parameter_list: $ => seq(
            alias(choice('(', '{'), $.type),
            optional(alias(choice( //shortcuts for self:&:Self and self:&=Self
                "&:",
                "&="
            ), $.ref)),
            list($.param),
            choice(')', '}')
        ),

        _control_flow: $ => choice(
            $.if,
            $.while,
            $.do,
        ),

        while: $ => prec.right(seq(
            alias("while", $.keyword),
            optional($.tag),
            choice(
                field("expression", $.expression),
                field("assignment", choice(
                    $.assignment,
                    $.reassignment
                )),
            ),
            field("block", $.block),
            optional($.else),
        )),

        if: $ => prec.right(seq(
            alias("if", $.keyword),
            optional($.tag),
            optional(seq("|", alias($.expression, $.key), "|")),
            alias(optional($._assign_start), $.assignment),
            list1($.expression),
            field("block", $.block),
            repeat($.elif),
            optional($.else),
        )),

        elif: $ => prec.right(seq(
            alias("elif", $.keyword),
            alias(optional($._assign_start), $.assignment),
            list1($.expression),
            field("block", $.block),
        )),

        else: $ => seq(
            alias("else", $.keyword),
            field("block", $.block),
        ),

        do: $ => prec.right(seq(
            alias("do", $.keyword),
            optional($.tag),
            $.block,
            optional(seq(
                field("while", seq(
                    alias("while", $.keyword),
                    $.expression,
                )),
                optional(
                    $.else
                )
            ))
        )),

        comment: $ => choice(
            seq(
                '//',
                alias(/[^\n]*/, $.content),
            ),
            seq(
                '/',
                $.string,
            ),
        ),

        _literal: $ => choice(
            $.bool,
            $.integer,
            $.float,
            $.string,
            $.table,
            $.root,
            $.compiler,
            $.function_sig,
            $.args,
        ),

        root: $ => "@",
        compiler: $ => "!",
        args: $ => "...",

        table: $ => seq(
            ".{",
            table_internals($),
            "}"
        ),

        bool: $ => choice(
            "true",
            "false"
        ),

        integer: $ => choice(
            prec(2, alias(/0b[_0-1]+/, $.i2)),
            prec(2, alias(/0o[_0-7]+/, $.i8)),
            prec(1, alias(/[0-9][_0-9]*/, $.i10)),
            prec(2, alias(/0x[_0-9a-fA-F]+/, $.i16)),
        ),

        float: $ => seq(
            alias(/[0-9][_0-9]*\.[0-9][_0-9]*/, $.value),
            alias(
                token.immediate(optional(seq(
                    "e",
                    /[+-]?[0-9][_0-9]*/
                ))),
                $.exponent
            )
        ),

        string: $ => choice(
            string($, '"', /[^"\\]+/, [$._escape]),
            string($, "'", /[^'\\]+/, [$._escape]),
        ),

        multi_string: $ => repeat1(alias($.multi_chunk, $.string)),

        multi_chunk: $ => seq(
            alias(/\\["']/, $.quot),
            repeat(choice(
                alias(token.immediate(/[^\\\n]+/), $.content),
                alias($.extra, $.content),
                $._escape
            )),
        ),

        //for some reason / *\.\\/ breaks the previous case
        extra: $ => seq(
            repeat(token.immediate(" ")),
            token.immediate("."),
        ),

        _escape: $ => choice(
            $.basic_escape,
            $.value_escape,
            $.int_escape,
        ),

        basic_escape: $ => token.immediate(/\\./),

        value_escape: $ => seq(
            alias("\\{", $.escape_quot),
            $.expression,
            optional($.escape_format),
            alias("}", $.escape_quot),
        ),

        escape_format: $ => seq(
            ":",
            repeat(choice(
                alias("?", $.debug),
                alias(/p./, $.padding_char),
                alias(/[<^>][0-9]+/, $.padding),
                alias(seq(
                    "s",
                    alias(optional(/[0-9]*/), $.distance),
                    alias(optional(/\../), $.dot),
                    alias(optional(/,./), $.comma),
                ), $.separator),
                alias(seq(
                    "#",
                    alias(optional(/[boxe]/), $.format),
                    alias(optional("+"), $.sign),
                    alias(optional(/[0-9]*\.[0-9]*/), $.precision),
                ), $.num_format)
            ))
        ),

        int_escape: $ => seq(
            alias("\\[", $.escape_quot),
            list($.expression),
            alias("]", $.escape_quot),
        ),

        identifier: $ => {
            const identifier_start =
                /[^\p{Control}\s+\-*/%^#&~|<>=(){}\[\];:,.\\'"?!\d]/;
            const identifier_continue =
                /[^\p{Control}\s+\-*/%^#&~|<>=(){}\[\];:,.\\'"?!]*/;
            return token(seq(identifier_start, identifier_continue));
        },
    }
});
  