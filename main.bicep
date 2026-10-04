// =============================================================================
// Moon Café Interlaken - Bereitstellung in Azure App Service (Bicep)
// Praxisarbeit VICC - Shahilla Fazal
// Deklarative Variante von deploy_azure.sh: beschreibt den Zielzustand
// =============================================================================

// Parameter (Standardwerte entsprechen deploy_azure.sh)
param location string = resourceGroup().location
param planName string = 'plan-moon-cafe'
param appName string = 'moon-cafe'
param image string = 'ghcr.io/shahilla/moon-cafe:latest'

// App Service Plan (Linux, Stufe B1)
resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true // erforderlich für Linux
  }
}

// Web-App, die das Container-Image aus der GitHub Container Registry betreibt
resource app 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${image}'
      appSettings: [
        // Port der Anwendung im Container und Herkunft des Images
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: 'https://ghcr.io' }
      ]
    }
  }
}

// Ausgabe der öffentlichen Adresse
output url string = 'https://${app.properties.defaultHostName}/'
