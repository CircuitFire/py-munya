import subprocess
import shutil
import sys
from pathlib import Path

def command_exists(command):
    out = shutil.which(command) != None
    if not out:
        print(command + "missing")
    return out

def c_file(path):
    return path.with_suffix(".c")

def o_file(path):
    return path.with_suffix(".o")

def plat_exe(path):
    if sys.platform == "win32":
        return path.with_suffix(".exe")
    return path

def plat_lib(path):
    if sys.platform == "win32":
        return path.with_suffix(".lib")
    return path.with_suffix(".a")

def plat_dynlib(path):
    if sys.platform == "win32":
        return path.with_suffix(".dll")
    return path.with_suffix(".so")

def into_path(x):
    if type(x) is str:
        return Path(x)
    return x

def print_cmd(cmd):
    out = "cmd:"
    for x in cmd:
        out += " " + str(x)
    print(out)

def make_dir(dir, file=False):
    if file:
        dir.parent.mkdir(parents=True, exist_ok=True)
    else:
        dir.mkdir(parents=True, exist_ok=True)

def into_dir(dir):
    if type(dir) != Path:
        return Path(dir)
    return dir

def compile_exe(files, out=None, include=[], libs=[], build_dir="./build", out_dir="./out", p_cmd=False):
    if not command_exists("clang"):
        return

    if type(files) == str:
        files = [files]
    build_dir = into_dir(build_dir)
    out_dir = into_dir(out_dir)

    make_dir(out_dir)
    
    if out == None:
        out = into_path(files[0])
    
    args = ""
    out = out_dir / plat_exe(out)
    make_dir(out, file=True)
    cmd = ["clang", args, "-o", out]

    for i, lib in enumerate(libs):
        libs[i] = "-l" + str(plat_lib(into_path(lib)))

    cmd.extend(libs)

    for i, file in enumerate(files):
        file = into_path(file)
        o = build_dir / o_file(file)
        c = c_file(file)
        if not o.is_file() or o.stat().st_mtime < c.stat().st_mtime:
            compile_obj(file, out_dir=build_dir, p_cmd=p_cmd)
        files[i] = o

    cmd.extend(files)

    if p_cmd:
        print_cmd(cmd)
    if subprocess.run(cmd).returncode == 0:
        return out

def compile_obj(file, out_dir="./build", p_cmd=False):
    if not command_exists("clang"):
        return
    out_dir = into_dir(out_dir)

    args = "-c"
    file = into_path(file)
    out = out_dir / o_file(file)
    make_dir(out, file=True)
    cmd = ["clang", args, c_file(file), "-o", out_dir / o_file(file)]

    if p_cmd:
        print_cmd(cmd)
    if subprocess.run(cmd).returncode == 0:
        return out

def compile_lib(out, files, build_dir="./build", out_dir="./libs", p_cmd=False):
    if not command_exists("llvm-ar"):
        return
    
    build_dir = into_dir(build_dir)
    out_dir = into_dir(out_dir)
    make_dir(out_dir)

    out = into_path(out)
    for i, file in enumerate(files):
        file = into_path(file)
        o = build_dir / o_file(file)
        c = c_file(file)
        if not o.is_file() or o.stat().st_mtime < c.stat().st_mtime:
            compile_obj(file, out_dir=build_dir, p_cmd=p_cmd)
        files[i] = o
    
    cmd = ["llvm-ar", "-rc", out_dir / plat_lib(out)]
    cmd.extend(files)

    if p_cmd:
        print_cmd(cmd)

    if subprocess.run(cmd).returncode == 0:
        return out_dir/out

# out = compile_lib("test_lib", ["c/lib1", "c/lib2"], p_cmd=True)
# if out:
# out = compile_exe("test", p_cmd=True)
# if out:
#     subprocess.run(out)
