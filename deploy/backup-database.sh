#!/bin/sh
# Write a complete custom-format dump or remove the incomplete output on failure.
set -eu
umask 077

if [ "$#" -ne 3 ]; then
    echo 'Usage: sh deploy/backup-database.sh /absolute/private.env /absolute/backup-directory database_name' >&2
    exit 2
fi
case "$1" in
    /*) environment_file=$1 ;;
    *) echo 'Use an absolute environment file path.' >&2; exit 2 ;;
esac
case "$2" in
    /*) backup_directory=$2 ;;
    *) echo 'Use an absolute backup directory path.' >&2; exit 2 ;;
esac
database_name=$3
case "$database_name" in
    ''|*[!a-zA-Z0-9_]*) echo 'Use a simple database name containing letters, digits and underscores.' >&2; exit 2 ;;
esac
if [ "${#database_name}" -gt 63 ]; then
    echo 'Database name is too long.' >&2
    exit 2
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

mkdir -p -- "$backup_directory"
chmod 700 "$backup_directory"
backup_file=$(mktemp "$backup_directory/studio-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
trap 'rm -f -- "$backup_file"' 0
trap 'exit 1' HUP INT TERM
docker compose --env-file "$environment_file" -f compose.production.yaml exec -T db pg_dump --username=studio --dbname="$database_name" --format=custom --no-owner --no-acl > "$backup_file"
test -s "$backup_file"
mv -- "$backup_file" "$backup_file.dump"
trap - 0 HUP INT TERM
printf 'Database backup written: %s.dump\n' "$backup_file"
