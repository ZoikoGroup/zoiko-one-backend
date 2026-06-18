$ErrorActionPreference = "Stop"
try {
    $body = @{email="admin@zoiko.com";password="admin123"} | ConvertTo-Json
    $r = Invoke-WebRequest -Uri "http://localhost:8000/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
    $data = $r.Content | ConvertFrom-Json
    $token = $data.access_token
    $headers = @{Authorization="Bearer $token"; accept="application/json"}

    $tests = @(
        @{name="CATEGORIES"; url="http://localhost:8000/hr/assets/categories"; params=$null}
        @{name="MAINTENANCE"; url="http://localhost:8000/hr/assets/maintenance"; params=$null}
        @{name="REQUESTS"; url="http://localhost:8000/hr/assets/requests"; params=$null}
        @{name="SETTINGS"; url="http://localhost:8000/hr/assets/settings"; params=$null}
        @{name="LEARNING PATHS"; url="http://localhost:8000/hr/learning/paths"; params=$null}
        @{name="CERTIFICATIONS"; url="http://localhost:8000/hr/learning/certifications"; params=$null}
        @{name="SKILLS"; url="http://localhost:8000/hr/learning/skills"; params=$null}
        @{name="PROGRAMS"; url="http://localhost:8000/hr/learning/programs"; params=$null}
        @{name="CALENDAR"; url="http://localhost:8000/hr/learning/calendar"; params=$null}
        @{name="REPORTS"; url="http://localhost:8000/hr/learning/reports/course-completion"; params=$null}
    )

    foreach ($t in $tests) {
        try {
            $resp = Invoke-WebRequest -Uri $t.url -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
            Write-Host "[PASS] $($t.name): $($resp.StatusCode)"
        } catch {
            $code = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "?" }
            $body = if ($_.Exception.Response) { $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); $sr.ReadToEnd(); $sr.Close() } else { $_.Exception.Message }
            Write-Host "[FAIL] $($t.name): $code - $body".Substring(0, [Math]::Min(200, ("[FAIL] $($t.name): $code - $body").Length))
        }
    }

    # Now try CREATE tests
    Write-Host "`n--- CREATE ASSET TEST ---"
    $createBody = @{name="Test Laptop"; asset_tag="TST-001"; status="available"} | ConvertTo-Json
    $cr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets" -Method POST -Body $createBody -ContentType "application/json" -Headers $headers -TimeoutSec 15 -UseBasicParsing
    Write-Host "CREATE ASSET: $($cr.StatusCode) - $($cr.Content)"
}
catch {
    Write-Host "FATAL: $($_.Exception.Message)"
}
