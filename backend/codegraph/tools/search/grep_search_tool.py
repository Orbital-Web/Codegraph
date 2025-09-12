from fastmcp import FastMCP

app = FastMCP(__name__)


# TODO: actually implement
@app.tool()
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y
