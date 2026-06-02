#!/usr/bin/env bash
#
# Pre-flight check for the MCP server example. Run from this directory.

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }

FAILED=0

echo "=== MCP filesystem server pre-flight ==="
echo

# Python 3.12+
if command -v python3 >/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 12 ]; then
        pass "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION is too old (need 3.12+)"
    fi
else
    fail "python3 not found"
fi

# mcp installed
if python3 -c 'import mcp.server.fastmcp' 2>/dev/null; then
    pass "mcp package installed"
else
    fail "mcp not installed. Run: pip install -e ."
fi

# Server module imports cleanly
if python3 -c 'from mcp_filesystem_server.server import mcp; assert mcp is not None' 2>/dev/null; then
    pass "server module imports"
else
    fail "server module import failed"
fi

# Tool module imports and three tools exist
if python3 -c '
from mcp_filesystem_server.tools import read_file, list_files, edit_file
assert callable(read_file)
assert callable(list_files)
assert callable(edit_file)
' 2>/dev/null; then
    pass "three tools available"
else
    fail "tools import failed"
fi

# Optional: MCP Inspector
if command -v npx >/dev/null; then
    pass "npx available (needed for MCP Inspector)"
else
    echo "  ℹ️  npx not found — you won't be able to run the MCP Inspector. Install Node.js if you want to use it."
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the server with:${NC}"
    echo "    cd sample_repo && python -m mcp_filesystem_server.server"
    echo "Or inspect it with:"
    echo "    cd sample_repo && npx @modelcontextprotocol/inspector python -m mcp_filesystem_server.server"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
