try {
    $body = @{email="admin@zoiko.com";password="SecurePassword123"} | ConvertTo-Json
    Write-Host "Request body: $body"
    $r = Invoke-WebRequest -Uri "http://localhost:8000/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
    Write-Host "Status: $($r.StatusCode)"
    $r.Content | ConvertFrom-Json | ConvertTo-Json
}
catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host "Body: $($reader.ReadToEnd())"
    $reader.Close()
}
