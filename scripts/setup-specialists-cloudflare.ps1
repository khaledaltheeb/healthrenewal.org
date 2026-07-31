[CmdletBinding()]
param(
    [string]$Repository = "khaledaltheeb/",
    [string]$AccountId = "826ac34927c1e045c06145a327c2ac52",
    [string]$WorkerName = "pterminology-specialists",
    [string]$DatabaseName = "pterminology-specialists",
    [string]$WidgetName = "pterminology-specialists-forms",
    [string]$Hostname = "khaledaltheeb.github.io"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if ($PSVersionTable.PSVersion.Major -lt 6) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Assert-Command {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$InstallHint
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed. $InstallHint"
    }
}

function Read-PlainSecret {
    param([Parameter(Mandatory)][string]$Prompt)
    $secureValue = Read-Host -Prompt $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        $secureValue.Dispose()
    }
}

function New-RandomSecret {
    param([ValidateRange(32, 128)][int]$ByteCount = 48)
    $bytes = New-Object byte[] $ByteCount
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
        return ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    }
    finally {
        $generator.Dispose()
        [Array]::Clear($bytes, 0, $bytes.Length)
    }
}

function Set-RepositorySecret {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "The value for secret $Name is empty."
    }

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Value | & gh secret set $Name --repo $Repository
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to save GitHub secret: $Name"
        }
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Save-AdminCredential {
    param([Parameter(Mandatory)][string]$AdminKey)

    $directory = Join-Path $HOME ".pterminology"
    $path = Join-Path $directory "specialists-admin-key.clixml"
    New-Item -ItemType Directory -Path $directory -Force | Out-Null

    $secure = ConvertTo-SecureString $AdminKey -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential("specialists-admin", $secure)
    $credential | Export-Clixml -Path $path -Force

    try {
        $acl = Get-Acl $path
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object Security.AccessControl.FileSystemAccessRule(
            [Security.Principal.WindowsIdentity]::GetCurrent().Name,
            "FullControl",
            "Allow"
        )
        $acl.SetAccessRule($rule)
        Set-Acl -Path $path -AclObject $acl
    }
    catch {
        Write-Warning "Unable to restrict the credential file ACL. The file remains encrypted for the current Windows account."
    }

    return $path
}

function Test-CloudflareToken {
    param([Parameter(Mandatory)][string]$Token)

    $uri = "https://api.cloudflare.com/client/v4/accounts/$AccountId/tokens/verify"
    $response = Invoke-RestMethod -Method Get -Uri $uri -Headers @{ Authorization = "Bearer $Token" }
    if ($response.success -ne $true -or $response.result.status -ne "active") {
        throw "The Cloudflare token is inactive or does not belong to the selected account."
    }
}

function Get-LatestBootstrapRun {
    param([Parameter(Mandatory)][datetime]$NotBefore)

    $json = & gh run list `
        --repo $Repository `
        --workflow "bootstrap-specialists-cloudflare.yml" `
        --event workflow_dispatch `
        --limit 10 `
        --json databaseId,status,conclusion,url,createdAt
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read GitHub Actions workflow runs."
    }

    $runs = @($json | ConvertFrom-Json)
    return $runs |
        Where-Object { [datetime]$_.createdAt -ge $NotBefore.AddMinutes(-1) } |
        Sort-Object {[datetime]$_.createdAt} -Descending |
        Select-Object -First 1
}

Write-Host "Secure specialists setup - Cloudflare and GitHub" -ForegroundColor Green
Write-Host "Do not use the Cloudflare token that appeared in the chat. Create and use a replacement token." -ForegroundColor Yellow

Write-Step "Checking GitHub CLI and repository access"
Assert-Command -Name "gh" -InstallHint "Install it with: winget install --id GitHub.cli"

& gh auth status --hostname github.com
if ($LASTEXITCODE -ne 0) {
    throw "Sign in first with: gh auth login"
}

& gh repo view $Repository --json nameWithOwner,defaultBranchRef | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "The current GitHub account cannot access $Repository."
}

if ($AccountId -notmatch '^[0-9a-f]{32}$') {
    throw "The Cloudflare account ID is invalid."
}

Write-Step "Reading secrets securely in this terminal"
$cloudflareToken = Read-PlainSecret "Paste the replacement Cloudflare token"
$resendApiKey = Read-PlainSecret "Paste the Resend API key"
$fromEmail = Read-Host "Verified sender email, for example notifications@example.com"

if ($cloudflareToken.Length -lt 20) {
    throw "The Cloudflare token is shorter than expected."
}
if ($resendApiKey.Length -lt 20) {
    throw "The Resend API key is shorter than expected."
}
if ($fromEmail -notmatch '@') {
    throw "The sender email is invalid. Use an address on a domain verified in Resend."
}

Write-Step "Verifying the replacement Cloudflare token"
Test-CloudflareToken -Token $cloudflareToken
Write-Host "The token is active for the selected account." -ForegroundColor Green

Write-Step "Generating strong local operation keys"
$adminApiKey = New-RandomSecret -ByteCount 48
$rateLimitSalt = New-RandomSecret -ByteCount 48
$credentialPath = Save-AdminCredential -AdminKey $adminApiKey
Write-Host "The admin key was encrypted locally at:" -ForegroundColor Green
Write-Host $credentialPath

Write-Step "Saving GitHub Actions secrets"
Set-RepositorySecret -Name "CLOUDFLARE_API_TOKEN" -Value $cloudflareToken
Set-RepositorySecret -Name "RESEND_API_KEY" -Value $resendApiKey
Set-RepositorySecret -Name "SPECIALISTS_ADMIN_API_KEY" -Value $adminApiKey
Set-RepositorySecret -Name "SPECIALISTS_RATE_LIMIT_SALT" -Value $rateLimitSalt
Set-RepositorySecret -Name "SPECIALISTS_FROM_EMAIL" -Value $fromEmail

$cloudflareToken = $null
$resendApiKey = $null
$adminApiKey = $null
$rateLimitSalt = $null
[GC]::Collect()
[GC]::WaitForPendingFinalizers()

Write-Step "Starting Cloudflare provisioning and deployment"
$dispatchStartedAt = [datetime]::UtcNow
& gh workflow run "bootstrap-specialists-cloudflare.yml" `
    --repo $Repository `
    --ref main `
    -f "account_id=$AccountId" `
    -f "worker_name=$WorkerName" `
    -f "database_name=$DatabaseName" `
    -f "widget_name=$WidgetName" `
    -f "hostname=$Hostname"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to start the bootstrap workflow."
}

$run = $null
for ($attempt = 1; $attempt -le 12 -and -not $run; $attempt++) {
    Start-Sleep -Seconds 5
    $run = Get-LatestBootstrapRun -NotBefore $dispatchStartedAt
}
if (-not $run) {
    throw "The workflow was requested, but its run could not be located. Open the repository Actions tab."
}

Write-Host "Workflow run: $($run.url)" -ForegroundColor Cyan
& gh run watch $run.databaseId --repo $Repository --exit-status
if ($LASTEXITCODE -ne 0) {
    throw "Deployment failed. Open the workflow link above and inspect the failed step without copying any secret into logs."
}

Write-Step "Checking frontend runtime configuration"
Start-Sleep -Seconds 3
$runtime = & gh api "repos/$Repository/contents/specialists-partners/assets/runtime-config.js?ref=main" --jq '.content'
if ($LASTEXITCODE -eq 0 -and $runtime) {
    $decoded = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($runtime -replace '\s', '')))
    if ($decoded -match 'apiBase:\s*"https://') {
        Write-Host "The public Worker URL is connected to the frontend." -ForegroundColor Green
    }
    else {
        Write-Warning "The workflow finished, but runtime-config.js does not contain the API URL yet. Review the final workflow step."
    }
}

Write-Host "`nResource setup, deployment, and frontend connection completed." -ForegroundColor Green
Write-Host "Sector page: https://healthrenewal.org/specialists-partners/"
Write-Host "Admin page: https://healthrenewal.org/specialists-partners/admin/"
Write-Host "`nTo recover the admin key locally:" -ForegroundColor Yellow
Write-Host "(Import-Clixml '$credentialPath').GetNetworkCredential().Password"
Write-Host "`nAfter a successful live test, revoke the temporary Cloudflare token or replace it with an operational token." -ForegroundColor Yellow
