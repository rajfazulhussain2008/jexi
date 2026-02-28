param([string]$Name, [string]$Value, [string]$Env = "production")
# Write value to temp file WITHOUT newline (critical for Vercel)
[System.IO.File]::WriteAllText("$env:TEMP\vercel_val.txt", $Value, [System.Text.Encoding]::UTF8)
Write-Host "Setting $Name..."
Get-Content "$env:TEMP\vercel_val.txt" -Raw | vercel env add $Name $Env
