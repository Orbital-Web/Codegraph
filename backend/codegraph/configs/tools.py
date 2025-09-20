import os

NATIVE_MCP_TOOL_PREFIX = "cg"  # used to determine if a tool is native or not
INTERNAL_TOOL_CALL_ERROR_FLAG = "[ITCError]"  # used to differentiate from other tool call errors

GREP_MAX_MATCHES = int(os.getenv("GREP_MAX_MATCHES", "20"))
GREP_MAX_CONTEXT = int(os.getenv("GREP_MAX_CONTEXT", "5"))

FILE_MAX_READ_LINES = int(os.getenv("FILE_MAX_READ_LINES", "200"))
LIST_DIR_MAX_NUM_CONTENTS = int(os.getenv("LIST_DIR_MAX_NUM_CONTENTS", "50"))
