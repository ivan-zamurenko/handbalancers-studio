#!/bin/sh
set -eu

# Only a hostname may enter the config template, never arbitrary nginx syntax.
if [ "${#STUDIO_HOST}" -gt 253 ] || ! printf '%s\n' "$STUDIO_HOST" | LC_ALL=C grep -Eq '^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]([a-z0-9-]{0,61}[a-z0-9])?$'; then
    echo 'STUDIO_HOST must be a lowercase DNS hostname without a port or path.' >&2
    exit 1
fi

template=/opt/studio/bootstrap.conf.template
certificate_dir="/etc/letsencrypt/live/$STUDIO_HOST"
if [ -s "$certificate_dir/fullchain.pem" ] && [ -s "$certificate_dir/privkey.pem" ]; then
    template=/opt/studio/tls.conf.template
else
    echo 'TLS certificate absent: serving ACME challenges and proxy health only.' >&2
fi

# Substitute only STUDIO_HOST, preserving native nginx variables such as $uri.
envsubst '${STUDIO_HOST}' < "$template" > /etc/nginx/conf.d/studio.conf
mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp
chown -R nginx:nginx /var/cache/nginx
nginx -t
exec nginx -g 'daemon off;'
