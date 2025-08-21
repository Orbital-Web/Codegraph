from pathlib import Path

from codegraph.db.engine import get_session
from codegraph.db.models import File, Node, Project
from codegraph.graph.indexing.pipeline import run_indexing
from codegraph.graph.models import Language, NodeType


def test_basic(reset: None) -> None:
    """
    - proj: links to root file
    - file: links to parent directory & project, skips non-indexed extensions
    - node: module node
    - node: Function and Class nodes
    - node: nested Function and Class nodes
    - TODO: refs: between Function/class nodes and module node
    - TODO: refs: between nodes of same file
    - TODO: refs: between nested nodes
    - TODO: refs: self-referencing (e.g., recursive function, factory class, self type hinting)
    - TODO: refs: between inherited classes
    - TODO: refs: from type hints
    """
    project_name = "cool project"
    project_root = Path(__file__).parent / "test_files" / "basic"
    run_indexing(project_name, project_root)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        # TODO: refs = session.query(Node__Reference).all()

    assert len(projs) == 1
    proj = projs[0]
    assert proj.name == project_name

    assert len(files) == 2
    files_map = {Path(file.path).relative_to(project_root).as_posix(): file for file in files}
    assert files_map.keys() == {".", "file.py"}
    file1 = files_map["."]
    file2 = files_map["file.py"]
    assert proj.root_file_id == file1.id
    assert file1.name == "basic"
    assert file1.parent_id is None
    assert file1.project_id == proj.id
    assert file1.language is None
    assert file2.name == "file.py"
    assert file2.parent_id == file1.id
    assert file2.project_id == proj.id
    assert file2.language == Language.PYTHON

    assert len(nodes) == 11
    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file",
        "file.simple_fn",
        "file.SimpleClass",
        "file.SimpleClass.__init__",
        "file.SimpleClass.simple_method",
        "file.parent_fn",
        "file.parent_fn.ChildClass",
        "file.parent_fn.child_fn",
        "file.recursive_fn",
        "file.ParentClass",
        "file.ParentClass.ChildClass",
    }
    for node in nodes:
        assert node.file_id == file2.id
        assert node.project_id == proj.id
        if node.global_qualifier == "file":
            assert node.type == NodeType.MODULE
        elif node.global_qualifier in (
            "file.SimpleClass",
            "file.parent_fn.ChildClass",
            "file.ParentClass",
            "file.ParentClass.ChildClass",
        ):
            assert node.type == NodeType.CLASS
        else:
            assert node.type == NodeType.FUNCTION

    # TODO: check refs


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
