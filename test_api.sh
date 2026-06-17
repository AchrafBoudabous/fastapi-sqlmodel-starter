#!/usr/bin/env bash
# Manual end-to-end smoke test for the FastAPI SQLModel Starter.
# Requires: curl, python (any version, for JSON pretty-print).
# Usage: bash test_api.sh

BASE="http://localhost:8000"
PASS=0
FAIL=0

# ── Helpers ───────────────────────────────────────────────────────────────────

green()  { echo -e "\033[0;32m$*\033[0m"; }
red()    { echo -e "\033[0;31m$*\033[0m"; }
yellow() { echo -e "\033[0;33m$*\033[0m"; }
bold()   { echo -e "\033[1m$*\033[0m"; }

step() {
    echo ""
    bold "─── Step $1: $2 ───────────────────────────────────────"
}

expect_status() {
    local label=$1 expected=$2 actual=$3
    if [ "$actual" = "$expected" ]; then
        green "  ✓ $label → HTTP $actual"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label → expected HTTP $expected, got HTTP $actual"
        FAIL=$((FAIL + 1))
    fi
}

pause() { echo ""; yellow "  ⏳ waiting 3 seconds..."; sleep 3; }

# ── Steps ─────────────────────────────────────────────────────────────────────

step 1 "Health check"
RESP=$(curl -s "$BASE/health")
echo "$RESP" | python -m json.tool 2>/dev/null || echo "$RESP"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health")
expect_status "GET /health" "200" "$STATUS"

pause

step 2 "Register a new user"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoketest@example.com","password":"password123"}')
BODY=$(echo "$RESP" | head -n -1)
STATUS=$(echo "$RESP" | tail -n 1)
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
expect_status "POST /auth/register" "201" "$STATUS"

pause

step 3 "Reject duplicate email (409)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoketest@example.com","password":"password123"}')
expect_status "POST /auth/register (duplicate)" "409" "$STATUS"

pause

step 4 "Reject short password (422)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@example.com","password":"short"}')
expect_status "POST /auth/register (short password)" "422" "$STATUS"

pause

step 5 "Login — capture access + refresh tokens"
LOGIN=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoketest@example.com","password":"password123"}')
echo "$LOGIN" | python -m json.tool 2>/dev/null || echo "$LOGIN"
ACCESS=$(echo "$LOGIN" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
REFRESH=$(echo "$LOGIN" | python -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])" 2>/dev/null)
if [ -n "$ACCESS" ]; then
    green "  ✓ POST /auth/login → tokens received"
    PASS=$((PASS + 1))
else
    red "  ✗ POST /auth/login → no token in response"
    FAIL=$((FAIL + 1))
fi

pause

step 6 "GET /me — authenticated"
RESP=$(curl -s -w "\n%{http_code}" "$BASE/api/v1/auth/me" \
  -H "Authorization: Bearer $ACCESS")
BODY=$(echo "$RESP" | head -n -1)
STATUS=$(echo "$RESP" | tail -n 1)
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
expect_status "GET /auth/me" "200" "$STATUS"

pause

step 7 "GET /me — no token (expect 401)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/auth/me")
expect_status "GET /auth/me (no token)" "401" "$STATUS"

pause

step 8 "GET /me — garbage token (expect 401)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/auth/me" \
  -H "Authorization: Bearer thisisnotavalidtoken")
expect_status "GET /auth/me (garbage token)" "401" "$STATUS"

pause

step 9 "Create an item"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/v1/items/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"title":"Smoke test item","description":"Created by test_api.sh"}')
BODY=$(echo "$RESP" | head -n -1)
STATUS=$(echo "$RESP" | tail -n 1)
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
ITEM_ID=$(echo "$BODY" | python -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
expect_status "POST /items/" "201" "$STATUS"

pause

step 10 "Get item by id"
RESP=$(curl -s -w "\n%{http_code}" "$BASE/api/v1/items/$ITEM_ID" \
  -H "Authorization: Bearer $ACCESS")
BODY=$(echo "$RESP" | head -n -1)
STATUS=$(echo "$RESP" | tail -n 1)
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
expect_status "GET /items/:id" "200" "$STATUS"

pause

step 11 "Update item (partial — title only, description preserved)"
RESP=$(curl -s -w "\n%{http_code}" -X PUT "$BASE/api/v1/items/$ITEM_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"title":"Updated title"}')
BODY=$(echo "$RESP" | head -n -1)
STATUS=$(echo "$RESP" | tail -n 1)
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
expect_status "PUT /items/:id" "200" "$STATUS"

pause

step 12 "Refresh token — get new access token"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}")
BODY=$(echo "$RESP" | head -n -1)
STATUS=$(echo "$RESP" | tail -n 1)
echo "$BODY" | python -m json.tool 2>/dev/null || echo "$BODY"
expect_status "POST /auth/refresh" "200" "$STATUS"

pause

step 13 "Use access token as refresh (expect 401)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$ACCESS\"}")
expect_status "POST /auth/refresh (access-as-refresh)" "401" "$STATUS"

pause

step 14 "Admin endpoint without admin role (expect 403)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/users/" \
  -H "Authorization: Bearer $ACCESS")
expect_status "GET /users/ (non-admin)" "403" "$STATUS"

pause

step 15 "Delete item"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/api/v1/items/$ITEM_ID" \
  -H "Authorization: Bearer $ACCESS")
expect_status "DELETE /items/:id" "204" "$STATUS"

pause

step 16 "Deleted item is gone (expect 404)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/items/$ITEM_ID" \
  -H "Authorization: Bearer $ACCESS")
expect_status "GET /items/:id (deleted)" "404" "$STATUS"

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
bold "══════════════════════════════════════════"
bold " Results: $PASS passed, $FAIL failed"
bold "══════════════════════════════════════════"
echo ""

[ $FAIL -eq 0 ] && green "All checks passed ✓" || red "Some checks failed ✗"
echo ""
