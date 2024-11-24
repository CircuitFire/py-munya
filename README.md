- v0.1 of Munya
- This has gone as far as it can with no knowledge or planning.
- v0.2 will be written in Rust.
- currently it is mostly a wraper around c
- mu_core.mu is the standered lib that is added to all translated programs.
- test.mu is an example program.
- munya-color/ is to be used with tree-sitter-vscode extention to provide basic colors in vs-code.

# requires
- clang
- python

# install
- py -m pip install ./tree-sitter-munya

# uninstall
- py -m pip uninstall tree-sitter-munya

# translate to c
- py .\mu.py tran test.mu

# translate to c and compile
- py .\mu.py build test.mu

# translate to c, compile, and run
- py .\mu.py run test.mu
