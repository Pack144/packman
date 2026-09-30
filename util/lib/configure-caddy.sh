#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"

port="${1:?Usage: configure-caddy.sh PORT}"
caddy_server_id="${CADDY_SERVER_ID:-srv0}"
caddy_route_id="packman-localhost"
caddy_route_endpoint="http://127.0.0.1:2019/id/$caddy_route_id"
caddy_routes_endpoint="http://127.0.0.1:2019/config/apps/http/servers/$caddy_server_id/routes"

caddy_route="$(cat <<EOF
{
    "@id": "$caddy_route_id",
    "match": [{"host": ["packman.localhost"]}],
    "handle": [{
        "handler": "reverse_proxy",
        "upstreams": [{"dial": "127.0.0.1:$port"}]
    }]
}
EOF
)"

if ! command -v caddy >/dev/null 2>&1; then
    warn "Caddy is not installed. Django will be available only at http://localhost:$port"
elif ! curl --fail --silent http://127.0.0.1:2019/config/ >/dev/null; then
    warn "Caddy's Admin API is unavailable. Start it with: brew services start caddy"
else
    info "Updating Caddy route"
    delete_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
        -X DELETE "$caddy_route_endpoint")"
    if [[ "$delete_status" != 2* && "$delete_status" != "404" ]]; then
        warn "Caddy route could not be deleted. Django will be available only at http://localhost:$port"
    elif curl --fail --silent --show-error -X POST "$caddy_routes_endpoint" \
        -H "Content-Type: application/json" \
        --data-binary "$caddy_route" >/dev/null; then
        success "Caddy configured for http://packman.localhost"
    else
        warn "Caddy route could not be updated. Django will be available only at http://localhost:$port"
    fi
fi
