import io
from pathlib import Path
from colorama import Fore, Style

import pytest
from cli.stream import stream_with_code_format
from colorama import Fore, Style

G = Fore.GREEN
R = Fore.RED
N = Style.RESET_ALL


def test_streaming_without_code_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    project_root = Path(__file__).parent
    input_stream = [
        "test_files/sample1.py\n",
        "this isn't\n",
        "a code block.\n",
    ]
    expected_stream = input_stream

    output_stream = list(stream_with_code_format(project_root, input_stream))
    assert output_stream == expected_stream


def test_streaming_with_multiline_chunks(capsys: pytest.CaptureFixture[str]) -> None:
    project_root = Path(__file__).parent
    input_stream = [
        "hello there\nnice to meet you",
        "\n",
    ]
    expected_stream = [
        "hello there\n",
        "nice to meet you\n",
    ]

    output_stream = list(stream_with_code_format(project_root, input_stream))
    assert output_stream == expected_stream


def test_streaming_with_split_and_leftover_chunks(
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = Path(__file__).parent
    input_stream = [
        "hel",
        "lo\n",
        "test_fi",
        "les/s",
        "ample2.",
        "cpp\n`",  # ``` split across multiple chunks
        "``cp",
        "p\n",
        "int factorial(int n) {\n",
        "    int result = 1;\n",
        "    for (int i = 2; i <= n; i++)\n",
        "        result *= i;\n",
        "    return result;\n",
        "}\n",
        "`",
        "``",  # leftover, no newline
    ]
    expected_stream = [
        "hello\n",
        "test_files/sample2.cpp\n",
        "```cpp\n",
        (
            "int factorial(int n) {\n"
            + "    int result = 1;\n"
            + f"{R}    for (int i = 1; i <= n; i++){N}\n"
            + f"{G}    for (int i = 2; i <= n; i++){N}\n"
            + "        result *= i;\n"
            + "    return result;\n"
            + "}\n"
        ),
        "```",
    ]

    output_stream = list(stream_with_code_format(project_root, input_stream))
    assert output_stream == expected_stream


def test_streaming_with_multiple_code_blocks(
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = Path(__file__).parent
    input_stream = [
        "test_files/",
        "sample1.py\n",
        "`",
        "``python\n",
        "def add(a: int, b: int) -> int:\n",
        "    return a + b\n\n",
        "def subtract(a: int, b: int) -> int:\n",
        "    return a - b\n\n",
        "def multiply(a, b):\n",
        "    # multiplies a and b\n",
        "    return a * b\n",
        "```\n",
        "some ",
        "text\n",
        "test_files/sample2.cpp\n```\n",
        "int factorial(int n) {\n",
        "    int result = 1;\n",
        "    for (int i = 2; i <= n; i++)\n",
        "        result *= i;\n",
        "    return result;\n",
        "}\n",
        "```\n",
    ]
    expected_stream = [
        "test_files/sample1.py\n",
        "```python\n",
        (
            f"{G}def add(a: int, b: int) -> int:{N}\n"
            + f"{R}def add(a, b):{N}\n"
            + f"{R}    # adds a and b{N}\n"
            + "    return a + b\n\n"
            + f"{G}def subtract(a: int, b: int) -> int:{N}\n"
            + f"{G}    return a - b{N}\n\n"
            + "def multiply(a, b):\n"
            + "    # multiplies a and b\n"
            + "    return a * b\n"
        ),
        "```\n",
        "some text\n",
        "test_files/sample2.cpp\n",
        "```\n",
        (
            "int factorial(int n) {\n"
            + "    int result = 1;\n"
            + f"{R}    for (int i = 1; i <= n; i++){N}\n"
            + f"{G}    for (int i = 2; i <= n; i++){N}\n"
            + "        result *= i;\n"
            + "    return result;\n"
            + "}\n"
        ),
        "```\n",
    ]

    output_stream = list(stream_with_code_format(project_root, input_stream))
    assert output_stream == expected_stream


def test_streaming_with_new_file(capsys: pytest.CaptureFixture[str]) -> None:
    project_root = Path(__file__).parent
    input_stream = [
        "test_files/sample3.txt\n",  # sample3 doesn't exist yet
        "```\n",
        "hello there\nnice to meet you\n",
        "```\n",
    ]
    expected_stream = [
        "test_files/sample3.txt\n",
        "```\n",
        f"{G}hello there{N}\n{G}nice to meet you{N}\n",
        "```\n",
    ]

    output_stream = list(stream_with_code_format(project_root, input_stream))
    assert output_stream == expected_stream


def test_streaming_with_unclosed_code_block(capsys: pytest.CaptureFixture[str]) -> None:
    project_root = Path(__file__).parent
    input_stream = [
        "test_files/sample2.cpp\n```\n",
        "int factorial(int n) {\n",
        "    int result = 1;\n",
        "    for (int i = 2; i <= n; i++)\n",
        "        result *= i;\n",
        "    return result;",  # leftover, no newline
        # unclosed code block
    ]
    expected_stream = [
        "test_files/sample2.cpp\n",
        "```\n",
        (
            "int factorial(int n) {\n"
            + "    int result = 1;\n"
            + f"{R}    for (int i = 1; i <= n; i++){N}\n"
            + f"{G}    for (int i = 2; i <= n; i++){N}\n"
            + "        result *= i;\n"
            + "    return result;\n"
            + (R + "}" + N + "\n")
        ),
        "```\n",
    ]

    output_stream = list(stream_with_code_format(project_root, input_stream))
    assert output_stream == expected_stream
