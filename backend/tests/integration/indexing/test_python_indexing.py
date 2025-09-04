import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import aliased

from codegraph.db.engine import get_session
from codegraph.db.models import Alias, File, Node, Node__Reference, Project
from codegraph.graph.indexing.pipeline import create_project, run_indexing
from codegraph.graph.models import Language, NodeType
from codegraph.index.chroma import ChromaIndexManager


class DeliberateError(Exception):
    """Deliberate error for testing purposes."""


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
    - chunk: should be indexed if file is not empty
    - chunk: should reference Function and Class nodes defined in that chunk
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
    assert files_map.keys() == {".", "file.py", "error_file.py", "text.txt"}
    for file_path, file in files_map.items():
        assert file.project_id == project_id
        if file_path.endswith(".py"):
            assert file.language == Language.PYTHON
        else:
            assert file.language is None

        if file_path == ".":
            assert file.parent_id is None
            assert file.name == "basic"
        else:
            assert file.parent_id == files_map["."].id
            assert file.name == file_path.split("/")[-1]

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
        assert node.file_id == files_map["file.py"].id
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

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    chunks_map = {(chunk.file_id, chunk.chunk_id): chunk for chunk in chunks}
    assert chunks_map.keys() == {
        (files_map["file.py"].id, 0),
        (files_map["error_file.py"].id, 0),
        (files_map["text.txt"].id, 0),
    }
    for chunk in chunks:
        if chunk.file_id != files_map["text.txt"].id:
            assert chunk.language == Language.PYTHON
        else:
            assert chunk.language is None

        assert set(chunk.node_ids) == {
            node.id
            for node in nodes
            if node.file_id == chunk.file_id and node.type != NodeType.MODULE
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
    for file_path, file in files_map.items():
        assert file.project_id == project_id
        if file_path.endswith(".py"):
            assert file.language == Language.PYTHON
        else:
            assert file.language is None

        if file_path == ".":
            assert file.parent_id is None
            assert file.name == "basic_import"
        else:
            path_split = file_path.split("/")
            parent_path = "/".join(path_split[:-1]) or "."
            assert file.parent_id == files_map[parent_path].id
            assert file.name == path_split[-1]

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

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    chunks_map = {(chunk.file_id, chunk.chunk_id): chunk for chunk in chunks}
    assert chunks_map.keys() == {
        (files_map["file1.py"].id, 0),
        (files_map["file2.py"].id, 0),
        (files_map["module1/__init__.py"].id, 0),
        (files_map["module1/file3.py"].id, 0),
        (files_map["module2/file4.py"].id, 0),
    }
    for chunk in chunks:
        assert chunk.language == Language.PYTHON
        assert set(chunk.node_ids) == {
            node.id
            for node in nodes
            if node.file_id == chunk.file_id and node.type != NodeType.MODULE
        }


def test_deleting_root_should_delete_project(reset: None, tmp_path: Path) -> None:
    """
    - proj: should be deleted if root no longer exists
    - chunk: should also be deleted alongside project
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
    assert len(files) == 4
    assert len(nodes) == 10
    assert len(aliases) == 0
    assert len(refs) == 14

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    assert len(chunks) == 3

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

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    assert len(chunks) == 0


def test_basic_incremental_indexing(reset: None, tmp_path: Path) -> None:
    """
    - should leave file/node/alias/refs/chunks intact if file is not modified (__init__.py too)
    - should create file/node/alias/refs/chunks if file is new (__init__.py too)
    - should delete and recreate file/node/alias/refs/chunks if file is modified (__init__.py too)
    - should delete file/node/alias/refs/chunks if file is deleted (__init__.py too)
    - should leave file intact if directory is not modified
    - should create file if directory is new
    - should delete file/node/alias/refs/chunks for both directory and child if directory is deleted
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
    assert files_map.keys() == {
        ".",
        "file1.py",
        "file2.py",
        "file3.py",
        "dir1",
        "dir1/__init__.py",
        "dir1/file5.py",
        "dir1/file6.py",
        "dir2",
        "dir2/__init__.py",
        "dir2/file8.py",
        "dir2/file9.txt",
    }
    for file_path, file in files_map.items():
        assert file.project_id == project_id
        if file_path.endswith(".py"):
            assert file.language == Language.PYTHON
        else:
            assert file.language is None

        if file_path == ".":
            assert file.parent_id is None
            assert file.name == "project_root"
        else:
            path_split = file_path.split("/")
            parent_path = "/".join(path_split[:-1]) or "."
            assert file.parent_id == files_map[parent_path].id
            assert file.name == path_split[-1]

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file1",
        "file1.func1a",
        "file1.func1b",
        "file2",
        "file2.func2a",
        "file3",
        "file3.func3a",
        "dir1",
        "dir1.foo",
        "dir1.file5",
        "dir1.file5.func5a",
        "dir1.file6",
        "dir1.file6.func6a",
        "dir2",
        "dir2.file8",
    }
    for node_name, node in nodes_map.items():
        assert node.project_id == proj.id
        if "file" not in node_name:
            assert node.file_id == files_map[node_name[:4] + "/__init__.py"].id
        else:
            assert (
                node.file_id
                == files_map[
                    "/".join(part for part in node_name.split(".") if "func" not in part) + ".py"
                ].id
            )

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
        ("dir1", "dir1.foo", 2),
        ("dir1.file5", "dir1.file5.func5a", 2),
        ("dir1.file6", "dir1.file6.func6a", 2),
    }

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    chunks_map = {(chunk.file_id, chunk.chunk_id): chunk for chunk in chunks}
    assert chunks_map.keys() == {
        (files_map["file1.py"].id, 0),
        (files_map["file2.py"].id, 0),
        (files_map["file3.py"].id, 0),
        (files_map["dir1/__init__.py"].id, 0),
        (files_map["dir1/file5.py"].id, 0),
        (files_map["dir1/file6.py"].id, 0),
        (files_map["dir2/file9.txt"].id, 0),
    }
    for chunk in chunks:
        if chunk.file_id != files_map["dir2/file9.txt"].id:
            assert chunk.language == Language.PYTHON
        else:
            assert chunk.language is None

        assert set(chunk.node_ids) == {
            node.id
            for node in nodes
            if node.file_id == chunk.file_id and node.type != NodeType.MODULE
        }

    # modify project and re-index (copyfile will set updated_at to now, unlike copytree)
    # + file4, dir1/file7, dir3, - dir2, file3, dir1/file6, * file1, dir1/__init__, dir1/file5
    shutil.copyfile(incremental_root / "new" / "file1.py", project_root / "file1.py")
    shutil.copyfile(incremental_root / "new" / "file4.py", project_root / "file4.py")
    shutil.copyfile(
        incremental_root / "new" / "dir1" / "__init__.py", project_root / "dir1" / "__init__.py"
    )
    shutil.copyfile(
        incremental_root / "new" / "dir1" / "file5.py", project_root / "dir1" / "file5.py"
    )
    shutil.copyfile(
        incremental_root / "new" / "dir1" / "file7.py", project_root / "dir1" / "file7.py"
    )
    shutil.rmtree(project_root / "dir2")
    (project_root / "file3.py").unlink()
    (project_root / "dir1" / "file6.py").unlink()
    (project_root / "dir3").mkdir()
    status = run_indexing(project_id)

    # make sure re-indexing only ran for the modified/new files
    assert set(status.codegraph_indexed_paths) == {
        project_root / "file1.py",
        project_root / "file4.py",
        project_root / "dir1" / "__init__.py",
        project_root / "dir1" / "file5.py",
        project_root / "dir1" / "file7.py",
    }
    assert set(status.vector_indexed_paths) == {
        project_root / "file1.py",
        project_root / "file4.py",
        project_root / "dir1" / "__init__.py",
        project_root / "dir1" / "file5.py",
        project_root / "dir1" / "file7.py",
    }

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
        "file4.py",
        "dir1",
        "dir1/__init__.py",
        "dir1/file5.py",
        "dir1/file7.py",
        "dir3",
    }
    for file_path, file in files_map.items():
        assert file.project_id == project_id
        if file_path.endswith(".py"):
            assert file.language == Language.PYTHON
        else:
            assert file.language is None

        if file_path == ".":
            assert file.parent_id is None
            assert file.name == "project_root"
        else:
            path_split = file_path.split("/")
            parent_path = "/".join(path_split[:-1]) or "."
            assert file.parent_id == files_map[parent_path].id
            assert file.name == path_split[-1]

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file1",
        "file1.func1a",
        "file1.func1c",
        "file2",
        "file2.func2a",
        "file4",
        "file4.func4a",
        "dir1",
        "dir1.bar",
        "dir1.file7",
        "dir1.file7.func7a",
    }
    for node_name, node in nodes_map.items():
        assert node.project_id == proj.id
        if "file" not in node_name:
            assert node.file_id == files_map[node_name[:4] + "/__init__.py"].id
        else:
            assert (
                node.file_id
                == files_map[
                    "/".join(part for part in node_name.split(".") if "func" not in part) + ".py"
                ].id
            )

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
        ("dir1", "dir1.bar", 2),
        ("dir1.file7", "dir1.file7.func7a", 2),
    }

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    chunks_map = {(chunk.file_id, chunk.chunk_id): chunk for chunk in chunks}
    assert chunks_map.keys() == {
        (files_map["file1.py"].id, 0),
        (files_map["file2.py"].id, 0),
        (files_map["file4.py"].id, 0),
        (files_map["dir1/__init__.py"].id, 0),
        (files_map["dir1/file5.py"].id, 0),
        (files_map["dir1/file7.py"].id, 0),
    }
    for chunk in chunks:
        assert chunk.language == Language.PYTHON
        assert set(chunk.node_ids) == {
            node.id
            for node in nodes
            if node.file_id == chunk.file_id and node.type != NodeType.MODULE
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

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    chunks_map = {(chunk.file_id, chunk.chunk_id): chunk for chunk in chunks}
    assert chunks_map.keys() == {(files_map["file1.py"].id, 0)}
    chunk = chunks_map[(files_map["file1.py"].id, 0)]
    assert chunk.language == Language.PYTHON
    assert set(chunk.node_ids) == {node.id for node in nodes if node.type != NodeType.MODULE}


def test_basic_indexing_crash_consistency(reset: None, tmp_path: Path) -> None:
    """
    - should handle crash before indexing starts
    - should handle crash during file processing
    - should handle crash during node codegraph processing
    - should handle crash during node vector processing
    - should handle new/modified/deleted files after crash
    - should have up-to-date and correct state after crash and re-indexing
    """
    project_name = "unfortunate project"
    project_root = tmp_path / "project_root"
    crashy_root = Path(__file__).parent / "test_files" / "basic_crash_consistency"
    project_root.mkdir()
    shutil.copyfile(crashy_root / "file1.py", project_root / "file1.py")

    project_id = create_project(project_name, project_root)

    # crash after step 3
    with patch("codegraph.graph.indexing.pipeline.re.compile", side_effect=DeliberateError):
        with pytest.raises(DeliberateError):
            run_indexing(project_id, batch_size=1)

    # crash during step 4
    with patch("codegraph.graph.indexing.pipeline._create_file", side_effect=DeliberateError):
        with pytest.raises(DeliberateError):
            run_indexing(project_id, batch_size=1)

    # add file2
    shutil.copyfile(crashy_root / "file2.py", project_root / "file2.py")

    # crash during step 5
    with patch(
        "codegraph.graph.indexing.pipeline.PythonParser.extract_references",
        side_effect=DeliberateError,
    ):
        with pytest.raises(DeliberateError):
            run_indexing(project_id, batch_size=1)

    # delete file2 and add dir1/__init__, dir1/file4
    (project_root / "file2.py").unlink()
    (project_root / "dir1").mkdir()
    shutil.copyfile(crashy_root / "dir1" / "__init__.py", project_root / "dir1" / "__init__.py")
    shutil.copyfile(crashy_root / "dir1" / "file4.py", project_root / "dir1" / "file4.py")

    # crash at very end (right before returning, so file1 indexing is complete)
    with patch("codegraph.graph.indexing.pipeline.IndexingStatus", side_effect=DeliberateError):
        with pytest.raises(DeliberateError):
            run_indexing(project_id, batch_size=1)

    # modify dir1/__init__, dir1/file3 and add dir1/file4
    shutil.copyfile(crashy_root / "dir1" / "__init__new.py", project_root / "dir1" / "__init__.py")
    shutil.copyfile(crashy_root / "dir1" / "file4new.py", project_root / "dir1" / "file4.py")
    shutil.copyfile(crashy_root / "dir1" / "file3.py", project_root / "dir1" / "file3.py")

    # should look the same as if there was never a crash
    # i.e., file1, dir1/__init__new, dir1/file3, dir1/file4new
    # status shouldn't have file1 as it was indexed pre-crash
    status = run_indexing(project_id)
    assert set(status.codegraph_indexed_paths) == {
        project_root / "dir1" / "__init__.py",
        project_root / "dir1" / "file3.py",
        project_root / "dir1" / "file4.py",
    }
    assert set(status.vector_indexed_paths) == {
        project_root / "dir1" / "__init__.py",
        project_root / "dir1" / "file3.py",
        project_root / "dir1" / "file4.py",
    }

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
        "dir1",
        "dir1/__init__.py",
        "dir1/file3.py",
        "dir1/file4.py",
    }
    for file_path, file in files_map.items():
        assert file.project_id == project_id
        if file_path.endswith(".py"):
            assert file.language == Language.PYTHON
        else:
            assert file.language is None

        if file_path == ".":
            assert file.parent_id is None
            assert file.name == "project_root"
        else:
            path_split = file_path.split("/")
            parent_path = "/".join(path_split[:-1]) or "."
            assert file.parent_id == files_map[parent_path].id
            assert file.name == path_split[-1]

    nodes_map = {node.global_qualifier: node for node in nodes}
    assert nodes_map.keys() == {
        "file1",
        "file1.func1a",
        "dir1",
        "dir1.file3",
        "dir1.file3.func3a",
        "dir1.file4",
        "dir1.file4.Class4a",
        "dir1.file4.Class4a.method4a",
    }
    assert nodes_map["file1"].file_id == files_map["file1.py"].id
    assert nodes_map["file1.func1a"].file_id == files_map["file1.py"].id
    assert nodes_map["dir1"].file_id == files_map["dir1/__init__.py"].id
    assert nodes_map["dir1.file3"].file_id == files_map["dir1/file3.py"].id
    assert nodes_map["dir1.file3.func3a"].file_id == files_map["dir1/file3.py"].id
    assert nodes_map["dir1.file4"].file_id == files_map["dir1/file4.py"].id
    assert nodes_map["dir1.file4.Class4a"].file_id == files_map["dir1/file4.py"].id
    assert nodes_map["dir1.file4.Class4a.method4a"].file_id == files_map["dir1/file4.py"].id

    aliases_map = {(alias.local_qualifier, alias.global_qualifier): alias for alias in aliases}
    assert aliases_map.keys() == {
        ("dir1.c4", "dir1.file4.Class4a"),
        ("dir1.dir1.file3", "dir1.file3"),
        ("dir1.file4.func3a", "dir1.file3.func3a"),
    }

    refs_map = {
        (sn.global_qualifier, tn.global_qualifier, ref.line_number): ref for (ref, sn, tn) in refs
    }
    assert refs_map.keys() == {
        ("file1", "file1.func1a", 2),
        ("dir1.file3", "dir1.file3.func3a", 1),
        ("dir1.file4", "dir1.file4.Class4a", 4),
        ("dir1.file4", "dir1.file4.Class4a.method4a", 6),
        ("dir1.file4.Class4a", "dir1.file4.Class4a.method4a", 6),
    }

    index = ChromaIndexManager.get_or_create_index(project_id)
    chunks = index.get()
    chunks_map = {(chunk.file_id, chunk.chunk_id): chunk for chunk in chunks}
    assert chunks_map.keys() == {
        (files_map["file1.py"].id, 0),
        (files_map["dir1/__init__.py"].id, 0),
        (files_map["dir1/file3.py"].id, 0),
        (files_map["dir1/file4.py"].id, 0),
    }
    for chunk in chunks:
        assert chunk.language == Language.PYTHON
        assert set(chunk.node_ids) == {
            node.id
            for node in nodes
            if node.file_id == chunk.file_id and node.type != NodeType.MODULE
        }

    # should not do anything (i.e., double-checking updated_at is correctly set)
    status = run_indexing(project_id)
    assert status.codegraph_indexed_paths == []
    assert status.vector_indexed_paths == []
