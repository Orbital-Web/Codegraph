from pathlib import Path

import pytest

from codegraph.db.engine import get_session
from codegraph.db.models import File, Node, Node__Reference, Project
from codegraph.graph.indexing.pipeline import run_indexing
from codegraph.graph.models import Language, NodeType


@pytest.mark.xfail(reason="TODO: implement ref extraction")
def test_basic(reset: None) -> None:
    """
    - proj: links to root file
    - file: links to parent directory & project
    - file: skips non-indexed extensions
    - file: skips files with syntax errors (for codegraph)
    - node: module node
    - node: Function and Class nodes
    - node: nested Function and Class nodes
    - refs: between Function/Class nodes and module node
    - refs: between nodes of same file
    - refs: between nested nodes
    - refs: self-referencing (e.g., recursive function, factory class, self type hinting)
    - refs: between inherited classes
    - refs: from type hints
    - refs: from object attribute method calls (e.g., `obj = Class()`, `obj.method()`)
    """
    project_name = "cool project"
    project_root = Path(__file__).parent / "test_files" / "basic"
    run_indexing(project_name, project_root)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        refs = session.query(Node__Reference).all()

    assert len(projs) == 1
    proj = projs[0]
    assert proj.name == project_name

    files_map = {Path(file.path).relative_to(project_root).as_posix(): file for file in files}
    assert files_map.keys() == {".", "file.py", "error_file.py"}
    file1 = files_map["."]
    file2 = files_map["file.py"]
    file3 = files_map["error_file.py"]
    assert proj.root_file_id == file1.id
    assert file1.name == "basic"
    assert file1.parent_id is None
    assert file1.project_id == proj.id
    assert file1.language is None
    assert file2.name == "file.py"
    assert file2.parent_id == file1.id
    assert file2.project_id == proj.id
    assert file2.language == Language.PYTHON
    assert file3.name == "error_file.py"
    assert file3.parent_id == file1.id
    assert file3.project_id == proj.id
    assert file3.language == Language.PYTHON

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

    refs_map = {(ref.source_node_id, ref.target_node_id, ref.line_number): ref for ref in refs}
    assert refs_map.keys() == {
        ("file", "file.simple_fn", 4),
        ("file", "file.SimpleClass", 9),
        ("file", "file.SimpleClass.__init__", 12),
        ("file", "file.SimpleClass.simple_method", 17),
        ("file", "file.parent_fn", 23),
        ("file", "file.parent_fn.ChildClass", 26),
        ("file", "file.parent_fn.child_fn", 32),
        ("file", "file.recursive_fn", 44),
        ("file", "file.ParentClass", 51),
        ("file", "file.ParentClass.ChildClass", 54),
        ("file.SimpleClass", "file.SimpleClass.__init__", 12),
        ("file.SimpleClass", "file.SimpleClass.simple_method", 17),
        ("file.parent_fn", "file.parent_fn.ChildClass", 26),
        ("file.parent_fn", "file.parent_fn.child_fn", 32),
        ("file.parent_fn", "file.parent_fn.ChildClass", 41),
        ("file.parent_fn.ChildClass", "file.SimpleClass", 26),
        ("file.parent_fn.child_fn", "file.SimpleClass", 32),
        ("file.parent_fn.child_fn", "file.SimpleClass.simple_method", 38),
        ("file.recursive_fn", "file.recursive_fn", 48),
        ("file.ParentClass", "file.ParentClass.ChildClass", 54),
    }


def test_basic_import(reset: None) -> None:
    """
    TODO:
    - refs: through global imports
    - refs: through `import module`, usage `module.node`
    - refs: from class initialization
    - refs: from superclass method calls
    - refs: between module node and bare usage nodes (not in a function/class)
    """
    project_name = "cool multifile project"
    project_root = Path(__file__).parent / "test_files" / "basic_import"
    run_indexing(project_name, project_root)

    # TODO: run checks


# TODO:
# - incremental indexing (new file)
# - incremental indexing (modified file)
# - incremental indexing (deleted file)
# - incremental indexing (moved file = deleted + new)

# - file: skips skip pattern directories
# - file: skips files that are too big

# - refs: through global imports (with alias)
# - refs: through imports within function (with/without alias)
# - refs: through relative imports (with/without alias)
# - refs: through mix of relative and global imports (with/without alias)
# - refs: through `import module.node`, usage `module.node`
# - refs: from class & static method calls (e.g., `Class.method()`)
