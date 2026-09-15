#!/usr/bin/env bash
#
# Pre-flight check for the OrderBase (Java) sample repo.
#
# Checks the JDK, builds the jar, runs the smoke tests, then boots the
# service and hits one endpoint. Non-zero exit if anything fails.
#
# Usage:
#   ./verify.sh
#
# On Windows you can run verify.ps1 instead -- the Java path does not need WSL.

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}PASS %s${NC}\n" "$1"; }
fail() { printf "${RED}FAIL %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}WARN %s${NC}\n" "$1"; }

FAILED=0
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "=== OrderBase (Java) pre-flight ==="
echo

# JDK 21+
if command -v java >/dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1 | sed -E 's/.*"([0-9]+)(\.[0-9]+)?.*/\1/')
    if [ "${JAVA_VERSION:-0}" -ge 21 ] 2>/dev/null; then
        pass "JDK $JAVA_VERSION (>= 21 required)"
    else
        fail "JDK $JAVA_VERSION is too old. Install JDK 21 or later (e.g. https://adoptium.net/)"
    fi
else
    fail "java not found. Install JDK 21+ (e.g. https://adoptium.net/)"
fi

# Build
echo
echo "=== Building (./mvnw package) ==="
if [ "$FAILED" -eq 0 ]; then
    if ./mvnw -q package -DskipTests >/dev/null 2>&1; then
        pass "jar builds"
    else
        fail "build failed. Run './mvnw package -DskipTests' to see why."
    fi
fi

# Smoke tests
echo
echo "=== Running smoke tests ==="
if [ "$FAILED" -eq 0 ]; then
    if ./mvnw -q test >/dev/null 2>&1; then
        pass "smoke tests"
    else
        fail "smoke tests failed. Run './mvnw test' to see why."
    fi
fi

# Boot the service and hit one endpoint. Run from a scratch dir with a scratch
# DB so we don't leave orderbase.db or a log file behind in the repo.
echo
echo "=== Booting service and probing GET /orders?limit=1 ==="
APP_JAR="$(find target -maxdepth 1 -name '*.jar' ! -name '*.original' 2>/dev/null | head -1)"
if [ -z "$APP_JAR" ]; then
    fail "could not find the built jar (target/*.jar). Run './mvnw package -DskipTests' first."
else
    BOOT_DIR="$(mktemp -d -t orderbase-verify)"
    export ORDERBASE_DB="$BOOT_DIR/verify.db"
    ( cd "$BOOT_DIR" && java -jar "$REPO_ROOT/$APP_JAR" ) >"$BOOT_DIR/app.log" 2>&1 &
    APP_PID=$!
    trap 'kill "$APP_PID" 2>/dev/null; rm -rf "$BOOT_DIR"' EXIT

    CODE=""
    for _ in $(seq 1 30); do
        CODE=$(curl -s -o /dev/null -w '%{http_code}' 'http://localhost:5057/orders?limit=1' 2>/dev/null || true)
        if [ "$CODE" = "200" ]; then
            break
        fi
        if ! kill -0 "$APP_PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done

    if [ "$CODE" = "200" ]; then
        pass "GET /orders?limit=1 -> 200"
    else
        fail "GET /orders?limit=1 -> ${CODE:-no response}"
        echo "--- app output ---"
        tail -20 "$BOOT_DIR/app.log" 2>/dev/null
    fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the service with: ./mvnw spring-boot:run${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
