#!/usr/bin/env bash
# ===========================================================================
# deploy_azure.sh  -  Betreibt die Moon-Cafe-App in Azure App Service aus dem
#                     oeffentlichen Container-Image der GitHub Container
#                     Registry (ghcr.io).  IaC-Nachweis fuer die VICC-Arbeit.
# Voraussetzung: Das Image wurde von GitHub Actions gebaut und ist OEFFENTLICH.
# Ausfuehren in der Azure Cloud Shell (Bash):  bash deploy_azure.sh
# ===========================================================================
set -euo pipefail

RG="rg-moon-cafe"
PLAN="plan-moon-cafe"
APP="moon-cafe"                 # ergibt https://moon-cafe.azurewebsites.net
STANDORT="italynorth"

# >>> HIER deinen GitHub-Benutzernamen eintragen (kleingeschrieben) <<<
GHUSER="shahilla"
IMAGE="ghcr.io/${GHUSER}/moon-cafe:latest"

echo ">> 1/5  Ressourcengruppe anlegen ($STANDORT)"
az group create -n "$RG" -l "$STANDORT" -o none

echo ">> 2/5  App Service Plan anlegen (Linux, Stufe B1)"
az appservice plan create -g "$RG" -n "$PLAN" --is-linux --sku B1 -l "$STANDORT" -o none

echo ">> 3/5  Web-App aus dem Container-Image erstellen"
echo "        Image: $IMAGE"
az webapp create -g "$RG" -p "$PLAN" -n "$APP" \
  --deployment-container-image-name "$IMAGE" -o none

echo ">> 4/5  Konfiguration (Port und Image)"
az webapp config appsettings set -g "$RG" -n "$APP" --settings WEBSITES_PORT=8000 -o none
az webapp config container set -g "$RG" -n "$APP" \
  --docker-custom-image-name "$IMAGE" \
  --docker-registry-server-url "https://ghcr.io" -o none

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
echo " Aufraeumen nach der Bewertung:"
echo "   az group delete -n ${RG} --yes --no-wait"
echo "============================================================"
