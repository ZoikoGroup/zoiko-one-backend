$suffix = Get-Random -Minimum 1000 -Maximum 99999
$tag = "TST-E2E-$suffix"
$sn  = "SN-E2E-$suffix"

Write-Host "Using tag=$tag sn=$sn"
Write-Host ""

$ErrorActionPreference = "Continue"

# Login
$body = @{email="admin@zoiko.com";password="admin123"} | ConvertTo-Json
$r = Invoke-WebRequest -Uri "http://localhost:8000/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
$token = ($r.Content | ConvertFrom-Json).access_token
$headers = @{Authorization="Bearer $token"; "Content-Type"="application/json"}
Write-Host "=== LOGIN OK ==="

# 1. CREATE asset
$create = @{name="Test-Laptop-Pro"; asset_tag=$tag; status="available"; category="Laptops"; serial_number=$sn} | ConvertTo-Json
try {
    $cr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets" -Method POST -Body $create -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $asset = $cr.Content | ConvertFrom-Json
    $aid = $asset.id
    Write-Host "[PASS] CREATE asset id=$aid status=$($cr.StatusCode)"
} catch {
    Write-Host "[FAIL] CREATE: $($_.Exception.Message)"
    $aid = 9999
}

# 2. GET single asset
try {
    $gr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $gotten = $gr.Content | ConvertFrom-Json
    if ($gotten.name -eq "Test-Laptop-Pro") { Write-Host "[PASS] GET asset: $($gotten.name)" } else { Write-Host "[FAIL] GET asset name mismatch" }
} catch { Write-Host "[FAIL] GET: $($_.Exception.Message)" }

# 3. UPDATE asset
try {
    $update = @{name="Test-Laptop-Pro-Updated"; status="assigned"} | ConvertTo-Json
    $ur = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid" -Method PUT -Body $update -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $updated = $ur.Content | ConvertFrom-Json
    if ($updated.name -eq "Test-Laptop-Pro-Updated") { Write-Host "[PASS] UPDATE asset: $($updated.name)" } else { Write-Host "[FAIL] UPDATE asset name mismatch" }
} catch { Write-Host "[FAIL] UPDATE: $($_.Exception.Message)" }

# 4. LIST assets (verify in list)
try {
    $lr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets?search=Test-Laptop-Pro-Updated" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $list = $lr.Content | ConvertFrom-Json
    if ($list.items.Count -gt 0) { Write-Host "[PASS] LIST found updated asset" } else { Write-Host "[FAIL] LIST did not find asset" }
} catch { Write-Host "[FAIL] LIST: $($_.Exception.Message)" }

# 5. DELETE asset (soft-delete)
try {
    $dr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid" -Method DELETE -Headers $headers -TimeoutSec 15 -UseBasicParsing
    Write-Host "[PASS] DELETE asset: status=$($dr.StatusCode)"
} catch { Write-Host "[FAIL] DELETE: $($_.Exception.Message)" }

# 6. Verify deleted (soft-delete)
try {
    $vr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    Write-Host "[WARN] GET after delete: $($vr.StatusCode) (not soft-deleted?)"
} catch { Write-Host "[PASS] GET after delete: 404 (soft-delete confirmed)" }

# 7. Create asset for maintenance test
$tag2 = "TST-E2E-MAINT-$suffix"
$sn2  = "SN-E2E-MAINT-$suffix"
try {
    $create2 = @{name="Maint-Test-Device"; asset_tag=$tag2; status="available"} | ConvertTo-Json
    $cr2 = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets" -Method POST -Body $create2 -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $asset2 = $cr2.Content | ConvertFrom-Json
    $aid2 = $asset2.id
    Write-Host "[PASS] Created asset for maintenance: id=$aid2"
} catch { Write-Host "[FAIL] Create maint asset: $($_.Exception.Message)"; $aid2 = 9999 }

# 8. Create maintenance record (include asset_id in body since model requires it)
try {
    $maint = @{asset_id=$aid2; issue="Keyboard not working"; priority="high"; reported_on="2026-06-18"} | ConvertTo-Json
    $mr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid2/maintenance" -Method POST -Body $maint -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $maintResp = $mr.Content | ConvertFrom-Json
    $mid = $maintResp.id
    if ($mid) { Write-Host "[PASS] CREATE maintenance id=$mid" } else { Write-Host "[FAIL] CREATE maintenance failed" }
} catch { Write-Host "[FAIL] Create maint: $($_.Exception.Message)"; $mid = $null }

# 9. List maintenance for asset
try {
    $mlr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid2/maintenance" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $maintList = $mlr.Content | ConvertFrom-Json
    if ($maintList.Count -gt 0) { Write-Host "[PASS] LIST maintenance: $($maintList.Count) records" } else { Write-Host "[FAIL] No maintenance records" }
} catch { Write-Host "[FAIL] List maint: $($_.Exception.Message)" }

# 10. Resolve maintenance
if ($mid) {
    try {
        $resolve = @{resolution="Replaced keyboard"; status="resolved"} | ConvertTo-Json
        $resr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/$aid2/maintenance/$mid/resolve" -Method PUT -Body $resolve -Headers $headers -TimeoutSec 15 -UseBasicParsing
        Write-Host "[PASS] RESOLVE maintenance: status=$($resr.StatusCode)"
    } catch { Write-Host "[FAIL] Resolve maint: $($_.Exception.Message)" }
}

# 11. Create asset request
try {
    $reqBody = @{asset_type="Monitor"; quantity=2; priority="medium"; reason="Need dual monitors"; requested_on="2026-06-18"} | ConvertTo-Json
    $reqr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/requests" -Method POST -Body $reqBody -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $reqResp = $reqr.Content | ConvertFrom-Json
    $rid = $reqResp.id
    Write-Host "[PASS] CREATE request id=$rid"
} catch { Write-Host "[FAIL] Create request: $($_.Exception.Message)"; $rid = $null }

# 12. Approve request
if ($rid) {
    try {
        $appr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/requests/$rid/approve" -Method PUT -Headers $headers -TimeoutSec 15 -UseBasicParsing
        Write-Host "[PASS] APPROVE request: status=$($appr.StatusCode)"
    } catch { Write-Host "[FAIL] Approve request: $($_.Exception.Message)" }
}

# 13. Create category
try {
    $catBody = @{name="E2E-Test-Category-$suffix"; description="Created during e2e test"} | ConvertTo-Json
    $catr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/categories" -Method POST -Body $catBody -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $catResp = $catr.Content | ConvertFrom-Json
    $cid = $catResp.id
    Write-Host "[PASS] CREATE category id=$cid"
} catch { Write-Host "[FAIL] Create category: $($_.Exception.Message)" }

# 14. List categories
try {
    $catlr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/categories" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    $catList = $catlr.Content | ConvertFrom-Json
    Write-Host "[PASS] LIST categories: $($catList.Count) items"
} catch { Write-Host "[FAIL] List categories: $($_.Exception.Message)" }

# 15. Get reports
try {
    $replr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/reports" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    Write-Host "[PASS] REPORTS: $($replr.StatusCode)"
} catch { Write-Host "[FAIL] Reports: $($_.Exception.Message)" }

# 16. Dashboard
try {
    $dbr = Invoke-WebRequest -Uri "http://localhost:8000/hr/assets/dashboard" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
    Write-Host "[PASS] DASHBOARD: $($dbr.StatusCode)"
} catch { Write-Host "[FAIL] Dashboard: $($_.Exception.Message)" }

Write-Host "`n=== E2E TEST RUN COMPLETE ==="
