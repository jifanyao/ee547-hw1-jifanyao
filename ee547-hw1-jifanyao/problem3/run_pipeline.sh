#!/bin/bash
if [ $# -lt 1 ]; then
  echo "Usage: $0 <url1> [url2] ..."
  echo "Example: $0 https://example.com"
  exit 1
fi

echo "Starting Multi-Container Pipeline"
echo "================================="

docker-compose down -v 2>/dev/null

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

for url in "$@"; do
  echo "$url" >> "$TEMP_DIR/urls.txt"
done

echo "URLs to process:"
cat "$TEMP_DIR/urls.txt"
echo ""

echo "Building containers..."
docker-compose build

echo "Starting pipeline..."
docker-compose up -d
sleep 3

echo "Injecting URLs..."
docker exec pipeline-fetcher mkdir -p /shared/input
docker cp "$TEMP_DIR/urls.txt" pipeline-fetcher:/shared/input/urls.txt

echo "Processing..."
MAX_WAIT=300
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  if docker exec pipeline-analyzer test -f /shared/analysis/final_report.json 2>/dev/null; then
    echo "Pipeline complete"
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

mkdir -p output
docker cp pipeline-analyzer:/shared/analysis/final_report.json output/
docker cp pipeline-analyzer:/shared/status output/

docker-compose down

if [ -f "output/final_report.json" ]; then
  echo ""
  echo "Results saved to output/final_report.json"
  python3 -m json.tool output/final_report.json | head -20
else
  echo "Pipeline failed - no output generated"
  exit 1
fi