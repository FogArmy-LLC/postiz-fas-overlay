#!/usr/bin/env bash
# audit_agpl_quarantine.sh — AGPL-3.0 overlay quarantine audit.
#
# Exits 0 (pass) if the working tree contains no secret-like files and an
# AGPL-3.0 LICENSE is present.  Exits 1 with a list of violations on failure.
#
# Usage:
#   bash scripts/audit_agpl_quarantine.sh [repo-root]
#
# If repo-root is omitted, defaults to the parent directory of this script.

set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
VIOLATIONS=()

check_no_secrets() {
    local patterns=(
        '\.env$'
        '\.env\.'
        '/secrets/'
        '/vault/'
        '/\.aws/'
        '/\.ssh/'
        '\.pem$'
        '\.key$'
        '_secret'
        'credentials'
    )
    for pat in "${patterns[@]}"; do
        while IFS= read -r -d $'\0' f; do
            VIOLATIONS+=("SECRET-PATTERN '$pat' matched: $f")
        done < <(find "$REPO_ROOT" \
                    -not -path '*/.git/*' \
                    -not -path '*/node_modules/*' \
                    -not -path '*/__pycache__/*' \
                    -regextype posix-extended -regex ".*${pat}.*" \
                    -print0 2>/dev/null || true)
    done
}

check_agpl_license() {
    local license="$REPO_ROOT/LICENSE"
    if [[ ! -f "$license" ]]; then
        VIOLATIONS+=("MISSING: LICENSE file not found at $license")
        return
    fi
    if ! grep -qiF 'GNU AFFERO GENERAL PUBLIC LICENSE' "$license"; then
        VIOLATIONS+=("WRONG-LICENSE: $license does not contain AGPL header")
    fi
}

check_no_raw_ips() {
    # Reject raw 10.20.x.x IPs — internal CNAMEs only per FAS CNAME law
    while IFS= read -r -d $'\0' f; do
        if grep -qP '10\.20\.\d+\.\d+' "$f" 2>/dev/null; then
            VIOLATIONS+=("RAW-INTERNAL-IP in $f — use *.fogarmy.internal CNAME instead")
        fi
    done < <(find "$REPO_ROOT" \
                -not -path '*/.git/*' \
                -not -path '*/node_modules/*' \
                -type f -print0 2>/dev/null || true)
}

check_no_secrets
check_agpl_license
check_no_raw_ips

if [[ ${#VIOLATIONS[@]} -eq 0 ]]; then
    echo "AGPL quarantine audit: PASS (0 violations)"
    exit 0
else
    echo "AGPL quarantine audit: FAIL (${#VIOLATIONS[@]} violation(s))" >&2
    for v in "${VIOLATIONS[@]}"; do
        echo "  - $v" >&2
    done
    exit 1
fi
