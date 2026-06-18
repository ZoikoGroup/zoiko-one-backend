$ErrorActionPreference = "Stop"
try {
    $body = @{email="admin@zoiko.com";password="admin123"} | ConvertTo-Json
    $r = Invoke-WebRequest -Uri "http://localhost:8000/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
    $token = ($r.Content | ConvertFrom-Json).access_token
    $headers = @{Authorization="Bearer $token"; accept="application/json"}

    $urls = @(
        "http://localhost:8000/hr/assets/categories"
        "http://localhost:8000/hr/assets/settings"
        "http://localhost:8000/hr/assets/requests"
    )

    foreach ($url in $urls) {
        try {
            $resp = Invoke-WebRequest -Uri $url -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
            Write-Host "[200] $url"
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errBody = $sr.ReadToEnd()
            $sr.Close()
            Write-Host "[$code] $url"
            Write-Host "  Body: $errBody"
        }
    }
} catch {
    Write-Host "FATAL: $_"
}
