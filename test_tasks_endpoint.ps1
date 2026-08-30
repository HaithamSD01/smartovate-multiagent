param(
    [string]$BaseUrl = "http://localhost:8000"
)

$envLine = Get-Content .env | Where-Object { $_ -match '^API_KEY_VALUE=' }
$apiKey  = ($envLine -split '=', 2)[1].Trim()

$headers = @{ "X-API-Key" = $apiKey }
$bodyText = '{"task": "Ecris une fonction Python qui calcule la suite de Fibonacci."}'
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($bodyText)

Invoke-RestMethod -Uri "$BaseUrl/tasks" -Method Post -Headers $headers -Body $bodyBytes -ContentType "application/json; charset=utf-8"