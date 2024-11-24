

def dent(n: int, s):
    x = ("    " * n)
    # print(n)
    return x + str(s) + "\n"

def dent_print(n: int, s):
    print(dent(n, s))

# def f_dent(n: int, s):
#     return ("    " * n) + str(s, encoding='utf-8')

# def f_dent_print(n: int, s):
#     print(f_dent(n, s))

def matches_any(types, value):
    for type in types:
        if value == type:
            return True
    return False

def dump(x):
    print("======================================================")
    print("dumping:")
    print(',\n'.join("%s: %s" % item for item in vars(x).items()))
    print("======================================================")