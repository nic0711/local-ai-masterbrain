#!/usr/bin/env bash
# Erstellt die Qdrant-Collection 'osticket_solutions' für den osTicket-KB-Workflow.
# Dimension 768 = nomic-embed-text Ausgabe.
# Aufruf: bash scripts/init_qdrant_osticket.sh [qdrant-host]

QDRANT_HOST="${1:-https://qdrant.brain.local}"
COLLECTION="osticket_solutions"

echo "Erstelle Qdrant-Collection '${COLLECTION}' auf ${QDRANT_HOST} ..."

curl -sf -X PUT "${QDRANT_HOST}/collections/${COLLECTION}" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "default_segment_number": 2
    }
  }' | python3 -m json.tool

echo ""
echo "Fertig. Collection-Status:"
curl -sf "${QDRANT_HOST}/collections/${COLLECTION}" | python3 -m json.tool
