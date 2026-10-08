#!/usr/bin/env bash
# Usage: fetch.sh <group> <repo> <outname>
set -u
KEY="${DATA_GOV_API_KEY:-DEMO_KEY}"
BASE=https://api.nal.usda.gov/FederalLCACommonsapi
g=$1; r=$2; out=$3
t0=$(date +%s)
tok=$(curl -sS --max-time 600 "$BASE/download/json/prepare/$g/$r?api_key=$KEY")
echo "prepare($g/$r) -> ${tok:0:200} ($(( $(date +%s)-t0 ))s)"
tok=$(echo "$tok" | tr -d '"[:space:]')
curl -sS --max-time 1800 -o "$out" -w "download http=%{http_code} size=%{size_download} time=%{time_total}s\n" "$BASE/download/json/$tok?api_key=$KEY"
ls -la "$out"; file "$out"
