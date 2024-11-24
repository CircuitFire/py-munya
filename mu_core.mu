!.lang.c.require('<inttypes.h>')
!.lang.c.require('<stdint.h>')
!.lang.c.require('<stdbool.h>')
!.lang.c.require('<stdio.h>')
!.lang.c.require('<stdlib.h>')
!.lang.c.require('<string.h>')

I64 ;: !.lang.c.local("int64_t")
I32 ;: !.lang.c.local("int32_t")
I16 ;: !.lang.c.local("int16_t")
I8 ;: !.lang.c.local("int8_t")
U64 ;: !.lang.c.local("uint64_t")
U32 ;: !.lang.c.local("uint32_t")
U16 ;: !.lang.c.local("uint16_t")
U8 ;: !.lang.c.local("uint8_t")
F64 ;: !.lang.c.local("double")
F32 ;: !.lang.c.local("float")
Bool ;: !.lang.c.local("bool")
CString ;: !.lang.c.local("char*")

c_malloc ;: !.lang.c.local("malloc")
c_free ;: !.lang.c.local("free")
c_sizeof ;: !.lang.c.local("sizeof")

c_abort ;: !.lang.c.local("abort")
c_puts ;: !.lang.c.local("puts")
c_strlen ;: !.lang.c.local("strlen")
c_getchar ;: !.lang.c.local("getchar")
c_putchar ;: !.lang.c.local("putchar")
c_snprintf ;: !.lang.c.local("snprintf")


U64 ;: Type.{
    to_cstring ;: fn(&=self);CString{
        len ;U64: c_snprintf(0, 0, "%lld", self.*) + 1
        new; CString: !.lang.c.cast(CString, c_malloc(len * c_sizeof(U8)))
        c_snprintf(new, len, "%lld", self.*)
        return new
    }
}

print ;: fn(str; &:String){
    c_puts(str.content)
}

c_str_panic ;: fn(message; CString){
    c_puts(message)
    c_abort()
}

panic ;: fn(message; &:String){
    print(message)
    c_abort()
}

Option_U64 ;: Enum.{
    val; U64,
    _
}

Range_U64 ;: Type.{
    current; U64,
    max; U64,

    __new__ ;: fn(max; U64);Range_U64{
        x ;= Range_U64.{
            current = 0,
            max = max,
        }
        return x
    },

    next ;: fn(&=self);Option_U64{
        if self.current == self.max {
            out ;: Option_U64.{_}
            return out
        }

        out ;: Option_U64.{val=self.current}
        self.current += 1
        return out
    },
}

//macros don't work
//List ;: fn!(type_){
//    return Type.{
//        content; &=type_,
//        capacity; U64,
//        len; U64,
//
//        __new__ ;: fn(size; U64);type_{
//            x ;: type_.{
//                content = !.lang.c.cast(type_, c_malloc(size * c_sizeof(type_))),
//                capacity = size,
//                len = size,
//            }
//            return x
//        },
//
//        __drop__ ;: fn(&=self){
//            c_free(self.content)
//            self.content = 0
//        },
//
//        __set_index__ ;: fn(&=self, index;U64, value;type_) {
//            if index > self.capacity {
//                c_str_panic("Error: tried to index outside of List size")
//            }
//            self.content[index] = value
//        },
//
//        __get_index__ ;: fn(&:self, index;U64);type_ {
//            if index > self.capacity {
//                c_str_panic("Error: tried to index outside of List size")
//            }
//            return self.content[index]
//        },
//    }
//}

String ;: Type.{
    content; CString,
    capacity; U64,
    len; U64,
    type; U8, //0 = empty, 1 = const, 2 = var

    __new__ ;: fn();String{
        x ;= String.{
            content = 0,
            capacity = 0,
            len = 0,
            type = 0,
        }
        return x
    },

    __drop__ ;: fn(&=self){
        if self.type == 2 {
            c_free(self.content)
        }
    },

    realloc ;: fn(&=self, new_len;U64){
        //c_puts("realloc")
        if new_len < self.len * 2 {
            new_len = self.len * 2
        }
        new; CString: !.lang.c.cast(CString, c_malloc((new_len+1) * c_sizeof(U8)))
        range ;= Range_U64(self.len)
        while x ;Option_U64= in range {
            if |x| i ;: Option_U64.val{
                new[i] = self.content[i]
            }
        }
        self.content = new
        self.capacity = new_len
    },

    append_internal ;: fn(&=self, str;CString, len;U64){
        //c_puts("append_internal")
        new_len;U64: len + self.len
        if new_len > self.capacity {
            self.realloc(new_len)
        }
        range ;= Range_U64(len)
        while x ;Option_U64= in range {
            if |x| i ;: Option_U64.val{
                //c_putchar(str[i])
                self.content[self.len + i] = str[i]
            }
        }
        self.len = new_len
        self.content[self.len] = 0
    },

    append_c ;: fn(&=self, str;CString){
        //c_puts("append_c")
        if self.type == 0 {
            self.content = str
            self.len = c_strlen(str)
            self.capacity = 0
            self.type = 1
        } else {
            self.type = 2
            self.append_internal(str, c_strlen(str))
        }
    },

    append_c_temp ;: fn(&=self, str;CString){
        self.type = 2
        self.append_internal(str, c_strlen(str))
    },

    append_char ;: fn(&=self, char_;U8){
        //c_puts("append_char")
        if |self.type| 0, 1 {
            self.type = 2
            self.content = !.lang.c.cast(CString, c_malloc((11) * c_sizeof(U8)))
            self.content[1] = 0
            self.content[0] = char_
            self.capacity = 10
            self.len = 1
        } elif 2 {
            if self.capacity == self.len {
                self.realloc(self.capacity * 2)
            }
            self.content[self.len] = char_
            self.len += 1
            self.content[self.len] = 0
        }
    },

    append ;: fn(&=self, str;&=String){
        self.type = 2
        self.append_internal(str.content, str.len)
    },

    print ;: fn(&=self){
        c_puts(self.content)
    },

    clear ;: fn(&=self){
        if |self.type| 1 {
            self.content = 0
        } elif 2 {
            self.content[0] = 0
            self.len = 0
        }
    },

    read ;: fn(&=self){
        char_ ;U8: c_getchar()
        while char_ != 10 {
            //c_putchar(char_)
            self.append_char(char_)
            char_ = c_getchar()
        }
    },
}