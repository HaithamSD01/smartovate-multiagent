# Deploie l'API sur Azure Container Apps en lisant les secrets depuis .env
# Aucune valeur secrete n'est affichee a l'ecran a aucun moment.

$ErrorActionPreference = "Stop"

Write-Host "Etape 1/5 : extension containerapp..."
az extension add --name containerapp --upgrade --yes | Out-Null

Write-Host "Etape 2/5 : enregistrement des fournisseurs Azure (peut prendre 1-2 min la premiere fois)..."
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

Write-Host "Etape 3/5 : lecture des variables depuis .env..."
$envVars = @{}
Get-Content .env | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -gt 0) {
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        $envVars[$key] = $val
    }
}

$requiredKeys = @(
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION", "REDIS_URL", "REDIS_TTL_SECONDS",
    "COSMOS_ENDPOINT", "COSMOS_KEY", "COSMOS_DATABASE", "COSMOS_CONTAINER",
    "API_KEY_VALUE"
)
foreach ($k in $requiredKeys) {
    if (-not $envVars.ContainsKey($k)) {
        throw "Variable manquante dans .env : $k"
    }
}
Write-Host "  -> $($requiredKeys.Count) variables chargees."

Write-Host "Etape 4/5 : identifiants ACR..."
$acrCreds = az acr credential show --name acrhaithamdhaimismartovate | ConvertFrom-Json
$acrUser = $acrCreds.username
$acrPass = $acrCreds.passwords[0].value

$secretArgs = @()
$envVarArgs = @()
foreach ($k in $requiredKeys) {
    $secretName = $k.ToLower().Replace("_", "-")
    $secretArgs += "$secretName=$($envVars[$k])"
    $envVarArgs += "$k=secretref:$secretName"
}

Write-Host "Etape 5/5 : creation de l'environnement et deploiement..."
az containerapp env create `
    --name env-smartovate-mas `
    --resource-group HaithamDHAIMI `
    --location francecentral

az containerapp create `
    --name smartovate-mas-api `
    --resource-group HaithamDHAIMI `
    --environment env-smartovate-mas `
    --image acrhaithamdhaimismartovate.azurecr.io/smartovate-mas-api:v1 `
    --registry-server acrhaithamdhaimismartovate.azurecr.io `
    --registry-username $acrUser `
    --registry-password $acrPass `
    --target-port 8000 `
    --ingress external `
    --min-replicas 0 `
    --max-replicas 1 `
    --secrets $secretArgs `
    --env-vars $envVarArgs

$fqdn = az containerapp show --name smartovate-mas-api --resource-group HaithamDHAIMI --query properties.configuration.ingress.fqdn -o tsv
Write-Host ""
Write-Host "Deploiement termine."
Write-Host "URL publique : https://$fqdn"