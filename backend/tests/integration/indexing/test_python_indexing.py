import shutil
from pathlib import Path

from sqlalchemy.orm import aliased

from codegraph.db.engine import get_session
from codegraph.db.models import Alias, File, Node, Node__Reference, Project
from codegraph.graph.indexing.pipeline import create_project, run_indexing
from codegraph.graph.models import Language, NodeType


def test_basic(reset: None) -> None:
    """
    - proj: links to root file
    - file: links to parent directory & project
    - file: skips non-indexed extensions
    - file: skips skip pattern directories
    - file: skips files with syntax errors (for codegraph)
    - node: Module node
    - node: Function and Class nodes
    - node: nested Function and Class nodes
    - refs: between Module node and Function/Class nodes
    - refs: between nested Function/Class nodes
    """
    project_name = "cool project"
    project_root = Path(__file__).parent / "test_files" / "basic"
    project_id = create_project(project_name, project_root)
    run_indexing(project_id)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()

        source_node = aliased(Node)
        target_node = aliased(Node)
        refs = (
            session.query(Node__Reference, source_node, target_node)
            .join(source_node, Node__Reference.source_node_id == source_node.id)
            .join(target_node, Node__Reference.target_node_id == target_node.id)
            .all()
        )

    assert len(projs) == 1
    proj = projs[0]
    assert proj.id == project_id
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
        "file.outer_fn",
        "file.outer_fn.inner_fn",
        "file.outer_fn.InnerClass",
        "file.OuterClass",
        "file.OuterClass.InnerClass",
    }
    for node in nodes:
        assert node.file_id == file2.id
        assert node.project_id == proj.id
        if node.global_qualifier == "file":
            assert node.type == NodeType.MODULE
        elif node.global_qualifier in (
            "file.SimpleClass",
            "file.outer_fn.InnerClass",
            "file.OuterClass",
            "file.OuterClass.InnerClass",
        ):
            assert node.type == NodeType.CLASS
        else:
            assert node.type == NodeType.FUNCTION

    aliases_map = {(alias.local_qualifier, alias.global_qualifier): alias for alias in aliases}
    assert aliases_map.keys() == set()

    refs_map: dict[tuple[str, str, int], Node__Reference] = {
        (sn.global_qualifier, tn.global_qualifier, ref.line_number): ref for (ref, sn, tn) in refs
    }
    assert refs_map.keys() == {
        ("file", "file.simple_fn", 1),
        ("file", "file.SimpleClass", 5),
        ("file", "file.SimpleClass.__init__", 7),
        ("file.SimpleClass", "file.SimpleClass.__init__", 7),
        ("file", "file.SimpleClass.simple_method", 10),
        ("file.SimpleClass", "file.SimpleClass.simple_method", 10),
        ("file", "file.outer_fn", 14),
        ("file", "file.outer_fn.inner_fn", 16),
        ("file.outer_fn", "file.outer_fn.inner_fn", 16),
        ("file", "file.outer_fn.InnerClass", 19),
        ("file.outer_fn", "file.outer_fn.InnerClass", 19),
        ("file", "file.OuterClass", 25),
        ("file", "file.OuterClass.InnerClass", 27),
        ("file.OuterClass", "file.OuterClass.InnerClass", 27),
    }


def test_basic_import(reset: None) -> None:
    """
    - node: __init__ file node
    - alias: for top-level imports
    - alias: for imports within function
    - alias: for aliased imports (`import module as`)
    - alias: for relative imports
    - alias: for `import module.submodule`
    - alias: for multiple imports (`import module1, module2`)
    """
    project_name = "cool multifile project"
    project_root = Path(__file__).parent / "test_files" / "basic_import"
    project_id = create_project(project_name, project_root)
    run_indexing(project_id)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()

        source_node = aliased(Node)
        target_node = aliased(Node)
        refs = (
            session.query(Node__Reference, source_node, target_node)
            .join(source_node, Node__Reference.source_node_id == source_node.id)
            .join(target_node, Node__Reference.target_node_id == target_node.id)
            .all()
        )

    assert len(projs) == 1
    proj = projs[0]
    assert proj.id == project_id
    assert proj.name == project_name

    files_map = {Path(file.path).relative_to(project_root).as_posix(): file for file in files}
    assert files_map.keys() == {
        ".",
        "file1.py",
        "file2.py",
        "module1",
        "module2",
        "module1/__init__.py",
        "module1/file3.py",
        "module2/__init__.py",
        "module2/file4.py",
    }
    root_file = files_map["."]
    assert proj.root_file_id == root_file.id
    assert root_file.parent_id is None
    module1_file = files_map["module1"]
    module2_file = files_map["module2"]
    assert module1_file.parent_id == root_file.id
    assert module2_file.parent_id == root_file.id
    assert files_map["file1.py"].parent_id == root_file.id
    assert files_map["file2.py"].parent_id == root_file.id
    assert files_map["module1/__init__.py"].parent_id == module1_file.id
    assert files_map["module1/file3.py"].parent_id == module1_file.id
    assert files_map["module2/__init__.py"].parent_id == module2_file.id
    assert files_map["module2/file4.py"].parent_id == module2_file.id
    for filepath, file in files_map.items():
        assert file.project_id == proj.id
        if filepath.endswith(".py"):
            assert file.language == Language.PYTHON
        else:
            assert file.language is None

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file1",
        "file1.func1a",
        "file2",
        "file2.func2a",
        "file2.func2b",
        "module1",
        "module1.file3",
        "module1.file3.func3a",
        "module1.file3.Class3a",
        "module1.file3.Class3a.method",
        "module2",
        "module2.file4",
        "module2.file4.func4a",
        "module2.file4.func4b",
    }
    for node in nodes:
        assert node.project_id == proj.id
        if "func" in node.global_qualifier or "method" in node.global_qualifier:
            assert node.type == NodeType.FUNCTION
        elif "Class" in node.global_qualifier:
            assert node.type == NodeType.CLASS
        else:
            assert node.type == NodeType.MODULE

    aliases_map = {(alias.local_qualifier, alias.global_qualifier): alias for alias in aliases}
    assert aliases_map.keys() == {
        ("file1.file2", "file2"),
        ("file1.f4", "module2.file4"),
        ("file1.f3a", "module1.func3a"),
        ("file1.Class3a", "module1.file3.Class3a"),
        ("file1.func4a", "module1.file3.func4a"),
        ("file1.func2b", "file2.func2b"),
        ("module1.func3a", "module1.file3.func3a"),
        ("module1.file3.func4a", "module2.file4.func4a"),
    }

    refs_map: dict[tuple[str, str, int], Node__Reference] = {
        (sn.global_qualifier, tn.global_qualifier, ref.line_number): ref for (ref, sn, tn) in refs
    }
    assert refs_map.keys() == {
        ("file1", "file1.func1a", 17),
        ("file2", "file2.func2a", 1),
        ("file2", "file2.func2b", 5),
        ("module1.file3", "module1.file3.func3a", 4),
        ("module1.file3", "module1.file3.Class3a", 8),
        ("module1.file3", "module1.file3.Class3a.method", 9),
        ("module1.file3.Class3a", "module1.file3.Class3a.method", 9),
        ("module2.file4", "module2.file4.func4a", 1),
        ("module2.file4", "module2.file4.func4b", 5),
    }


def test_deleting_root_should_delete_project(reset: None, tmp_path: Path) -> None:
    """
    - proj: should be deleted if root no longer exists
    """
    project_name = "cool project"
    project_root = tmp_path / "project_root"
    shutil.copytree(Path(__file__).parent / "test_files" / "basic", project_root)

    # initial indexing
    project_id = create_project(project_name, project_root)
    run_indexing(project_id)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()
        refs = session.query(Node__Reference).all()

    assert len(projs) == 1
    proj = projs[0]
    assert proj.id == project_id
    assert proj.name == project_name
    assert len(files) == 3
    assert len(nodes) == 10
    assert len(aliases) == 0
    assert len(refs) == 14

    # delete root and re-index
    shutil.rmtree(project_root)
    run_indexing(project_id)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()
        refs = session.query(Node__Reference).all()

    assert len(projs) == 0
    assert len(files) == 0
    assert len(nodes) == 0
    assert len(aliases) == 0
    assert len(refs) == 0


def test_basic_incremental_indexing(reset: None, tmp_path: Path) -> None:
    """
    - file/node/alias/refs: should be left intact if not modified
    - file/node/alias/refs: should be deleted if deleted
    - file/node/alias/refs: should be deleted and recreated if modified
    """
    project_name = "updated project"
    project_root = tmp_path / "project_root"
    incremental_root = Path(__file__).parent / "test_files" / "basic_incremental"
    shutil.copytree(incremental_root / "original", project_root)

    # initial indexing
    project_id = create_project(project_name, project_root)
    run_indexing(project_id)

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()

        source_node = aliased(Node)
        target_node = aliased(Node)
        refs = (
            session.query(Node__Reference, source_node, target_node)
            .join(source_node, Node__Reference.source_node_id == source_node.id)
            .join(target_node, Node__Reference.target_node_id == target_node.id)
            .all()
        )

    assert len(projs) == 1
    proj = projs[0]
    assert proj.id == project_id
    assert proj.name == project_name

    files_map = {Path(file.path).relative_to(project_root).as_posix(): file for file in files}
    assert files_map.keys() == {".", "file1.py", "file2.py", "file3.py"}
    dir1 = files_map["."]
    file1 = files_map["file1.py"]
    file2 = files_map["file2.py"]
    file3 = files_map["file3.py"]
    assert dir1.name == "project_root"
    assert file1.name == "file1.py"
    assert file2.name == "file2.py"
    assert file3.name == "file3.py"

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file1",
        "file1.func1a",
        "file1.func1b",
        "file2",
        "file2.func2a",
        "file3",
        "file3.func3a",
    }
    for node_name, node in nodes_map.items():
        assert node.project_id == proj.id
        assert node.file_id == files_map[node_name.split(".")[0] + ".py"].id

    aliases_map = {(alias.local_qualifier, alias.global_qualifier): alias for alias in aliases}
    assert aliases_map.keys() == set()

    refs_map: dict[tuple[str, str, int], Node__Reference] = {
        (sn.global_qualifier, tn.global_qualifier, ref.line_number): ref for (ref, sn, tn) in refs
    }
    assert refs_map.keys() == {
        ("file1", "file1.func1a", 2),
        ("file1", "file1.func1b", 6),
        ("file2", "file2.func2a", 2),
        ("file3", "file3.func3a", 2),
    }

    # modify project and re-index
    shutil.copyfile(incremental_root / "new" / "file1.py", project_root / "file1.py")
    shutil.copyfile(incremental_root / "new" / "file4.py", project_root / "file4.py")
    (project_root / "file3.py").unlink()
    status = run_indexing(project_id)

    # make sure re-indexing only ran for the modified/new files
    assert status.codegraph_indexed_paths == [project_root / "file1.py", project_root / "file4.py"]
    assert status.vector_indexed_paths == [project_root / "file1.py", project_root / "file4.py"]

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()

        source_node = aliased(Node)
        target_node = aliased(Node)
        refs = (
            session.query(Node__Reference, source_node, target_node)
            .join(source_node, Node__Reference.source_node_id == source_node.id)
            .join(target_node, Node__Reference.target_node_id == target_node.id)
            .all()
        )

    assert len(projs) == 1
    proj = projs[0]
    assert proj.id == project_id
    assert proj.name == project_name

    files_map = {Path(file.path).relative_to(project_root).as_posix(): file for file in files}
    assert files_map.keys() == {".", "file1.py", "file2.py", "file4.py"}
    dir1 = files_map["."]
    file1 = files_map["file1.py"]
    file2 = files_map["file2.py"]
    file4 = files_map["file4.py"]
    assert dir1.name == "project_root"
    assert file1.name == "file1.py"
    assert file2.name == "file2.py"
    assert file4.name == "file4.py"

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file1",
        "file1.func1a",
        "file1.func1c",
        "file2",
        "file2.func2a",
        "file4",
        "file4.func4a",
    }
    for node_name, node in nodes_map.items():
        assert node.project_id == proj.id
        assert node.file_id == files_map[node_name.split(".")[0] + ".py"].id

    aliases_map = {(alias.local_qualifier, alias.global_qualifier): alias for alias in aliases}
    assert aliases_map.keys() == set()

    refs_map = {
        (sn.global_qualifier, tn.global_qualifier, ref.line_number): ref for (ref, sn, tn) in refs
    }
    assert refs_map.keys() == {
        ("file1", "file1.func1a", 2),
        ("file1", "file1.func1c", 6),
        ("file2", "file2.func2a", 2),
        ("file4", "file4.func4a", 2),
    }


def test_should_ignore_massive_files(reset: None, tmp_path: Path) -> None:
    """
    - file: skips files that are too big
    """
    project_name = "massive project"
    project_root = tmp_path / "project_root"
    project_root.mkdir()

    with open(project_root / "file1.py", "w", encoding="utf-8") as f:
        f.write("def func1():\n    pass\n")

    with open(project_root / "file2.py", "w", encoding="utf-8") as f:
        for i in range(30):
            f.write(f"def func{i}():\n    pass\n\n")

    project_id = create_project(project_name, project_root)
    run_indexing(project_id, max_filesize=100 / (1024 * 1024))

    with get_session() as session:
        projs = session.query(Project).all()
        files = session.query(File).all()
        nodes = session.query(Node).all()
        aliases = session.query(Alias).all()

        source_node = aliased(Node)
        target_node = aliased(Node)
        refs = (
            session.query(Node__Reference, source_node, target_node)
            .join(source_node, Node__Reference.source_node_id == source_node.id)
            .join(target_node, Node__Reference.target_node_id == target_node.id)
            .all()
        )

    assert len(projs) == 1
    proj = projs[0]
    assert proj.id == project_id
    assert proj.name == project_name

    files_map = {Path(file.path).relative_to(project_root).as_posix(): file for file in files}
    assert files_map.keys() == {".", "file1.py"}

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {"file1", "file1.func1"}

    aliases_map = {(alias.local_qualifier, alias.global_qualifier): alias for alias in aliases}
    assert aliases_map.keys() == set()

    refs_map: dict[tuple[str, str, int], Node__Reference] = {
        (sn.global_qualifier, tn.global_qualifier, ref.line_number): ref for (ref, sn, tn) in refs
    }
    assert refs_map.keys() == {("file1", "file1.func1", 1)}


# TODO:
# - file: skips files that are too big
