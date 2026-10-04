#!/bin/bash
# =============================================================================
# Moon Café Interlaken - Bereitstellung in Azure App Service (Infrastructure as Code)
# Praxisarbeit VICC - Shahilla Fazal
# Ausführen in der Azure Cloud Shell: bash deploy_azure.sh
# =============================================================================
set -euo pipefail

# Namen der Azure-Ressourcen und Container-Image
RG="rg-moon-cafe"
PLAN="plan-moon-cafe"
APP="moon-cafe"
STANDORT="italynorth"
IMAGE="ghcr.io/shahilla/moon-cafe:latest"

echo ">> 1/5  Ressourcengruppe anlegen ($STANDORT)"
az group create -n "$RG" -l "$STANDORT" -o none

echo ">> 2/5  App Service Plan anlegen (Linux, Stufe B1)"
az appservice plan create -g "$RG" -n "$PLAN" --is-linux --sku B1 -l "$STANDORT" -o none

echo ">> 3/5  Web-App aus dem Container-Image erstellen"
echo "        Image: $IMAGE"
az webapp create -g "$RG" -p "$PLAN" -n "$APP" --container-image-name "$IMAGE" -o none

# Port der Anwendung im Container und Herkunft des Images festlegen
echo ">> 4/5  Konfiguration (Port und Image)"
az webapp config appsettings set -g "$RG" -n "$APP" --settings WEBSITES_PORT=8000 -o none
az webapp update -g "$RG" -n "$APP" --https-only true -o none   # nur HTTPS zulassen
az webapp config container set -g "$RG" -n "$APP" \
  --container-image-name "$IMAGE" \
  --container-registry-url "https://ghcr.io" -o none

echo ">> 5/5  Web-App neu starten"
az webapp restart -g "$RG" -n "$APP" -o none

echo ""
echo "============================================================"
echo " Fertig!  Betrieb aus Container-Image ($IMAGE)"
echo "   Browser : https://${APP}.azurewebsites.net/"
echo "   Web-API : https://${APP}.azurewebsites.net/api/menu"
echo ""
echo " Der erste Start kann 1-3 Minuten dauern (Image wird geladen)."
echo "------------------------------------------------------------"
echo " Aufräumen nach der Bewertung:"
echo "   az group delete -n ${RG} --yes --no-wait"
echo "============================================================"
