#!/bin/bash
# =============================================================================
#   iJeery V5.0 - Génération bundle macOS (.app)
# =============================================================================
cd "$(dirname "$0")"

echo ""
echo "============================================================================"
echo "  iJeery V5.0 - Génération APP macOS (build_ijerry_mac.py)"
echo "============================================================================"
echo ""

# Vérifie Python3
if ! python3 --version > /dev/null 2>&1; then
    echo "[ERREUR] Python3 introuvable."
    echo "Installez Python 3.12 depuis https://www.python.org/downloads/macos/"
    exit 1
fi

python3 build_ijerry_mac.py "$@"
ERR=$?

if [ $ERR -ne 0 ]; then
    echo ""
    echo "[ERREUR] Build échoué (code $ERR)."
    exit $ERR
fi

echo ""
echo "Appuyez sur Entrée pour fermer..."
read
exit 0
