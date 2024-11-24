import sys
import subprocess
from transpile import transpile_file
from build import compile_exe
from pathlib import Path

if len(sys.argv) < 3:
    print("usage: mu 'command' 'file'")
    exit()

command = sys.argv[1]
file = sys.argv[2]
fil = Path(file).stem
if command == "tran":
    transpile_file(file)
elif command == "build":
    transpile_file(file)
    compile_exe("./c/" + fil, p_cmd=True)
elif command == "run":
    transpile_file(file)
    out = compile_exe("./c/" + fil, p_cmd=True)
    if out:
        subprocess.run(out)