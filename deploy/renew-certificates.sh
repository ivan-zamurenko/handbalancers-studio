#!/bin/sh
# Host-side timer entrypoint. Certbot never receives access to the Docker socket.
set -eu

if [ "$#" -ne 1 ]; then
    echo 'Usage: sh deploy/renew-certificates.sh /absolute/path/to/private.env' >&2
    exit 2
fi
case "$1" in
    /*) environment_file=$1 ;;
    *) echo 'The private environment file path must be absolute.' >&2; exit 2 ;;
esac
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

docker compose --env-file "$environment_file" -f compose.production.yaml run --rm --no-deps certbot renew --webroot -w /var/www/certbot --quiet
# A reload is harmless when no certificate is due; only run it after success.
docker compose --env-file "$environment_file" -f compose.production.yaml exec -T nginx nginx -t
docker compose --env-file "$environment_file" -f compose.production.yaml exec -T nginx nginx -s reload
