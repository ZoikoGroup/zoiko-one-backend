try {
    $body = @{email="admin@zoiko.com";password="admin123"} | ConvertTo-Json
    $r = Invoke-WebRequest -Uri "http://localhost:8000/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
    Write-Host "LOGIN: $($r.StatusCode)"
    $data = $r.Content | ConvertFrom-Json
    $token = $data.access_token
    $headers = @{Authorization="Bearer $token"; accept="application/json"}

    $tests = @(
        @{name="ASSETS LIST"; url="http://localhost:8000/hr/assets"}
        @{name="DASHBOARD"; url="http://localhost:8000/hr/assets/dashboard"}
        @{name="COURSES"; url="http://localhost:8000/hr/learning/courses"}
        @{name="ENROLLMENTS"; url="http://localhost:8000/hr/learning/enrollments"}
        @{name="ASSESSMENTS"; url="http://localhost:8000/hr/learning/assessments"}
        @{name="CATEGORIES"; url="http://localhost:8000/hr/assets/categories"}
        @{name="MAINTENANCE"; url="http://localhost:8000/hr/assets/maintenance"}
        @{name="REQUESTS"; url="http://localhost:8000/hr/assets/requests"}
        @{name="SETTINGS"; url="http://localhost:8000/hr/assets/settings"}
    )

    $allPass = $true
    foreach ($t in $tests) {
        try {
            $resp = Invoke-WebRequest -Uri $t.url -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
            Write-Host "[PASS] $($t.name): $($resp.StatusCode)"
        } catch {
            $code = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "?" }
            Write-Host "[FAIL] $($t.name): $code"
            $allPass = $false
        }
    }

    if ($allPass) { Write-Host "`nALL ENDPOINTS PASSED" }
    else { Write-Host "`nSOME ENDPOINTS FAILED"; exit 1 }
}
catch {
    Write-Host "LOGIN FAILED: $($_.Exception.Message)"
}
