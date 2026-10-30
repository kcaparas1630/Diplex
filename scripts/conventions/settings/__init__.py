"""Checker settings: which files count as source code, and the limits each convention rule enforces."""

PYTHON_SUFFIXES = frozenset({".py"})
TYPESCRIPT_SUFFIXES = frozenset({".ts", ".tsx"})

# Generated or declaration-only files are never edited by hand, so they are not checked.
GENERATED_FILE_SUFFIXES = (".gen.ts", ".d.ts")

# Folders never walked. Hidden folders (.git, .venv, .claude, ...) are skipped as well.
EXCLUDED_DIRECTORIES = frozenset({"node_modules", "__pycache__", "dist", "build", "venv", "samples"})

# Tests may import anything they test and need no folder entry.
TEST_FOLDER_NAMES = frozenset({"tests", "test", "__tests__"})

# Where absolute Python imports are looked up, relative to the repository root.
PYTHON_SOURCE_ROOTS = ("diplex-core/src", ".")

# A folder's public entry: other folders import the folder through this file only.
ENTRY_FILE_NAMES = frozenset({"__init__.py", "__main__.py", "index.ts", "index.tsx", "index.js", "index.mjs"})
PYTHON_ENTRY_NAME = "__init__.py"
TYPESCRIPT_ENTRY_NAMES = frozenset({"index.ts", "index.tsx"})

# Tool configuration files may sit in a folder without making it a folder of code.
CONFIG_FILE_PATTERNS = ("*.config.ts", "*.config.js", "*.config.mjs", "*.config.cjs", "conftest.py", "setup.py")

# Above this many lines a file almost always holds more than one responsibility.
MAX_FILE_LINES = 300

MIN_NAME_LENGTH = 3
ALLOWED_SHORT_NAMES = frozenset({"i", "j", "k", "x", "y", "w", "h", "id", "ok", "db", "io"})
IGNORED_NAMES = frozenset({"self", "cls", "_", "__"})

# Names that say nothing about what they hold or do. Matched whole, ignoring case and trailing digits.
VAGUE_NAMES = frozenset({
    "arr", "bar", "baz", "cb", "data", "dct", "fn", "foo", "func", "handle", "helper", "helpers",
    "info", "lst", "manager", "misc", "obj", "res", "ret", "stuff", "temp", "thing", "things", "tmp",
    "util", "utils", "val",
})

# File names that invite unrelated code to pile up in one place.
VAGUE_FILE_STEMS = frozenset({"common", "helper", "helpers", "lib", "misc", "shared", "stuff", "util", "utils"})
