from analyzer import Analyzer
from translator import Translator
from pathlib import Path

import os

def transpile_file(name):
    # file = read_tree(name)
# 
    # if check_grammatical_errors(file):
        # return
# 
    # tree = parse_file(file)
    # tree.print()

    # os.chdir("./mu")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    analyzer = Analyzer()

    analyzer.run(f"{os.path.dirname(os.path.realpath(__file__))}\\mu_core.mu")
    analyzer.run(name)

    analyzer.finalize()

    # os.chdir("../c")
    translator = Translator("./c/" + Path(name).stem + ".c", analyzer)
    translator.run()