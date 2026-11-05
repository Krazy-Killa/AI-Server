#!/usr/bin/env bash
# Create a small local CA and one server certificate for the AI Server LAN proxy.
#
# Run as root on the server. Private keys are written 0600 and never printed.
# The CA is restricted (name constraints) to the names and addresses given, so a
# device that trusts it cannot be used to impersonate other sites. Install only
# ca.crt on client devices; never copy the .key files off the server.
#
# Usage: make-lan-cert.sh [--out DIR] (--dns NAME | --ip ADDRESS)...
set -euo pipefail

OUT=/etc/ai-server/tls
DNS_NAMES=()
IP_ADDRS=()

die() { echo "make-lan-cert: $*" >&2; exit 64; }

while [ $# -gt 0 ]; do
  case "$1" in
    --out) [ $# -ge 2 ] || die "--out needs a directory"; OUT="$2"; shift 2 ;;
    --dns) [ $# -ge 2 ] || die "--dns needs a name"; DNS_NAMES+=("$2"); shift 2 ;;
    --ip)  [ $# -ge 2 ] || die "--ip needs an IPv4 address"; IP_ADDRS+=("$2"); shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ $(( ${#DNS_NAMES[@]} + ${#IP_ADDRS[@]} )) -gt 0 ] || die "give at least one --dns or --ip"
for name in "${DNS_NAMES[@]}"; do
  [[ "$name" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$ ]] || die "invalid DNS name: $name"
done
for addr in "${IP_ADDRS[@]}"; do
  [[ "$addr" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || die "invalid IPv4 address: $addr"
  IFS=. read -r a b c d <<<"$addr"
  [ "$a" -le 255 ] && [ "$b" -le 255 ] && [ "$c" -le 255 ] && [ "$d" -le 255 ] || die "invalid IPv4 address: $addr"
done
command -v openssl >/dev/null || die "openssl is required"

for existing in ca.crt ca/ca.key server.crt server.key; do
  [ ! -e "$OUT/$existing" ] || die "$OUT/$existing already exists; refusing to overwrite"
done

umask 077
install -d -m 755 "$OUT"
install -d -m 700 "$OUT/ca"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

san=""
constraints=""
for name in "${DNS_NAMES[@]}"; do
  san+="${san:+,}DNS:$name"
  constraints+="${constraints:+,}permitted;DNS:$name"
done
for addr in "${IP_ADDRS[@]}"; do
  san+="${san:+,}IP:$addr"
  constraints+="${constraints:+,}permitted;IP:$addr/255.255.255.255"
done
primary="${DNS_NAMES[0]:-${IP_ADDRS[0]}}"

openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$OUT/ca/ca.key" 2>/dev/null
openssl req -x509 -new -key "$OUT/ca/ca.key" -sha256 -days 1825 \
  -subj "/CN=AI Server Local CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "nameConstraints=critical,$constraints" \
  -out "$OUT/ca.crt"

openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$OUT/server.key" 2>/dev/null
openssl req -new -key "$OUT/server.key" -subj "/CN=$primary" -out "$work/server.csr"
cat >"$work/server.ext" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=serverAuth
subjectAltName=$san
EOF
openssl x509 -req -in "$work/server.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca/ca.key" \
  -CAcreateserial -CAserial "$work/ca.srl" -sha256 -days 397 \
  -extfile "$work/server.ext" -out "$OUT/server.crt" 2>/dev/null

chmod 644 "$OUT/ca.crt" "$OUT/server.crt"
chmod 600 "$OUT/server.key" "$OUT/ca/ca.key"
openssl verify -CAfile "$OUT/ca.crt" "$OUT/server.crt" >/dev/null

echo "created in $OUT:"
echo "  ca.crt      install on client devices (public)"
echo "  server.crt  certificate for NGINX, valid 397 days"
echo "  server.key  NGINX private key (root only)"
echo "  ca/ca.key   CA private key (root only; move it off the server when practical)"
echo "names: $san"
openssl x509 -in "$OUT/server.crt" -noout -enddate -fingerprint -sha256
