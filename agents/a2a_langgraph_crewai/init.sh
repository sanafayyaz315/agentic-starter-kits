#!/bin/bash
#
# init.sh — Environment bootstrap for A2A LangGraph ↔ CrewAI
#
# Loads variables from .env next to this script and validates that every
# defined variable is non-empty (same pattern as other agents under agents/).
#

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
ENV_FILE="$AGENT_DIR/.env"

ENV_VARS=()

if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line//$'\r'/}"
        line="${line#"${line%%[![:space:]]*}"}"
        [[ -z "$line" || "$line" == \#* ]] && continue
        export "$line"
        ENV_VARS+=("${line%%=*}")
    done < "$ENV_FILE"
    echo "Environment variables loaded from $ENV_FILE"
else
    echo "ERROR: .env file not found at $ENV_FILE"
    return 1 2>/dev/null || exit 1
fi

for var_name in "${ENV_VARS[@]}"; do
    var_value=$(eval echo "\$$var_name")
    if [ -z "$var_value" ]; then
        echo "  ERROR: $var_name is empty. Check your .env file."
        return 1 2>/dev/null || exit 1
    fi
    local_lower=$(echo "$var_name" | tr '[:upper:]' '[:lower:]')
    if [[ "$local_lower" == *password* || "$local_lower" == *apikey* || "$local_lower" == *api_key* || "$local_lower" == *secret* || "$local_lower" == *token* ]]; then
        echo "  $var_name=****"
    else
        echo "  $var_name=$var_value"
    fi
done
