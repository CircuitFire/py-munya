main ;: fn(){
    range ;: Range_U64(10)
    while o_num ;Option_U64: in range {
        if |o_num| num ;: Option_U64.val {
            out ;: "\{num}"
            out.print()
        }
    }
    x ;: "input:"
    x.print()
    input ;: String()
    input.read()
    x.append(&=input)
    x.print()
}