#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_DIR="$REPO_ROOT/host"
MANIFEST_TEMPLATE="$REPO_ROOT/native-messaging-manifest/com.piifilter.host.json"

echo "== 1. Virtuelle Umgebung fuer den Host anlegen =="
python3 -m venv "$HOST_DIR/.venv"
source "$HOST_DIR/.venv/bin/activate"

echo "== 2. Python-Abhaengigkeiten installieren (kann etwas dauern) =="
pip install -e "$HOST_DIR"

echo "== 3. Deutsches spaCy-Sprachmodell herunterladen (~50-100MB) =="
python -m spacy download de_core_news_sm

HOST_EXECUTABLE="$HOST_DIR/.venv/bin/piifilter-host"

echo "== 4. Extension-ID abfragen (aus chrome://extensions) =="
read -rp "Extension-ID: " EXTENSION_ID

echo "== 5. Manifest generieren =="
TMP_MANIFEST=$(mktemp)
sed -e "s|REPLACE_WITH_ABSOLUTE_PATH|$HOST_EXECUTABLE|" \
    -e "s|REPLACE_WITH_EXTENSION_ID|$EXTENSION_ID|" \
    "$MANIFEST_TEMPLATE" > "$TMP_MANIFEST"

echo "== 6. Browser waehlen =="
select BROWSER in "google-chrome" "chromium"; do
  case $BROWSER in
    google-chrome) TARGET_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"; break ;;
    chromium)      TARGET_DIR="$HOME/.config/chromium/NativeMessagingHosts"; break ;;
  esac
done

mkdir -p "$TARGET_DIR"
cp "$TMP_MANIFEST" "$TARGET_DIR/com.piifilter.host.json"

echo ""
echo "Fertig."
echo "Manifest installiert: $TARGET_DIR/com.piifilter.host.json"
echo "Host-Executable: $HOST_EXECUTABLE"
echo ""
echo "Hinweis: der erste Aufruf des Hosts nach dem Browserstart dauert"
echo "spuerbar laenger, da Presidio/spaCy das Sprachmodell laden muessen."
echo ""
echo "Jetzt: $BROWSER komplett beenden (auch Hintergrundprozesse, ggf. 'pkill $BROWSER')"
echo "und neu starten."pip install -e .