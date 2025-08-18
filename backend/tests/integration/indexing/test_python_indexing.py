def test_basic(reset: None) -> None:
    # - proj: links to root file
    # - file: links to parent directory & project, skips non-indexed extensions
    # - node: Function and Class nodes
    # - node: nested Function and Class nodes
    # - TODO: refs: between nodes of same file
    # - TODO: refs: between nested nodes
    # - TODO: refs: self-referencing (e.g., recursive function, factory class, self type hinting)
    # - TODO: refs: from type hints
    pass


# TODO:
# - incremental indexing (new file)
# - incremental indexing (modified file)
# - incremental indexing (deleted file)
# - incremental indexing (moved file = deleted + new)

# - file: skips skip pattern directories
# - file: skips files that are too big
# - file: skips files with syntax errors

# - refs: through global imports (with/without alias)
# - refs: through imports within function (with/without alias)
# - refs: through relative imports (with/without alias)
# - refs: through mix of relative and global imports (with/without alias)
# - refs: through `import module.node`, usage `module.node`
# - refs: through `import module`, usage `module.node`

# - refs: from class initialization (e.g., `Class()` creates ref to `Class.__init__()`)
# - refs: from object attribute method calls (e.g., `obj = Class()`, `obj.method()`)
# - refs: from class & static method calls (e.g., `Class.method()`)

# TODO: for these, will need to consider whether to create `Module` type nodes
# Module nodes are the node equivalent of files and directories
# e.g., file.py (Module) has a relation with the function it defines
# likewise, could help pick up bare usage inside a file without being in a function/class
# - node: Module node
# - refs: between module and nodes defined in that module
# - refs: (add to basic test) for bare usage inside a file
