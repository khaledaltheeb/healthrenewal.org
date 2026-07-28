[CmdletBinding()]
param(
    [string]$Repository = "khaledaltheeb/pterminology-site",
    [string]$AccountId = "826ac34927c1e045c06145a327c2ac52",
    [string]$WorkerName = "pterminology-specialists",
    [string]$DatabaseName = "pterminology-specialists",
    [string]$WidgetName = "pterminology-specialists-forms",
    [string]$Hostname = "khaledaltheeb.github.io"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

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
        throw "الأداة '$Name' غير مثبتة. $InstallHint"
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
        throw "القيمة المطلوبة للسر $Name فارغة."
    }

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Value | & gh secret set $Name --repo $Repository
        if ($LASTEXITCODE -ne 0) {
            throw "تعذر حفظ GitHub Secret: $Name"
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
        Write-Warning "تعذر تضييق أذونات ملف الاعتماد، لكنه ما يزال مشفرًا بواسطة حساب Windows الحالي."
    }

    return $path
}

function Test-CloudflareToken {
    param([Parameter(Mandatory)][string]$Token)

    $uri = "https://api.cloudflare.com/client/v4/accounts/$AccountId/tokens/verify"
    $response = Invoke-RestMethod -Method Get -Uri $uri -Headers @{ Authorization = "Bearer $Token" }
    if ($response.success -ne $true -or $response.result.status -ne "active") {
        throw "رمز Cloudflare غير نشط أو لا يخص الحساب المحدد."
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
        throw "تعذر قراءة تشغيلات GitHub Actions."
    }

    $runs = @($json | ConvertFrom-Json)
    return $runs |
        Where-Object { [datetime]$_.createdAt -ge $NotBefore.AddMinutes(-1) } |
        Sort-Object {[datetime]$_.createdAt} -Descending |
        Select-Object -First 1
}

Write-Host "إعداد آمن لقطاع المختصين — Cloudflare وGitHub" -ForegroundColor Green
Write-Host "لا تُدخل الرمز السابق الذي ظهر في المحادثة. أنشئ رمزًا بديلًا محدود الصلاحيات أولًا." -ForegroundColor Yellow

Write-Step "فحص الأدوات والاتصال بحساب GitHub"
Assert-Command -Name "gh" -InstallHint "ثبّتها عبر: winget install --id GitHub.cli"
Assert-Command -Name "git" -InstallHint "ثبّت Git for Windows من الموقع الرسمي."

& gh auth status --hostname github.com
if ($LASTEXITCODE -ne 0) {
    throw "سجّل الدخول أولًا بالأمر: gh auth login"
}

& gh repo view $Repository --json nameWithOwner,defaultBranchRef | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "لا توجد صلاحية للوصول إلى المستودع $Repository بالحساب الحالي."
}

if ($AccountId -notmatch '^[0-9a-f]{32}$') {
    throw "معرّف حساب Cloudflare غير صالح."
}

Write-Step "إدخال القيم الحساسة داخل الطرفية"
$cloudflareToken = Read-PlainSecret "ألصق رمز Cloudflare البديل المحدود"
$resendApiKey = Read-PlainSecret "ألصق Resend API key"
$fromEmail = Read-Host "عنوان المرسل الموثق، مثال: notifications@example.com"

if ($cloudflareToken.Length -lt 20) {
    throw "رمز Cloudflare أقصر من المتوقع."
}
if ($resendApiKey.Length -lt 20) {
    throw "مفتاح Resend أقصر من المتوقع."
}
if ($fromEmail -notmatch '@') {
    throw "عنوان المرسل غير صالح. استخدم عنوانًا على نطاق موثق في Resend."
}

Write-Step "التحقق من رمز Cloudflare البديل"
Test-CloudflareToken -Token $cloudflareToken
Write-Host "تم التحقق من نشاط الرمز للحساب المحدد." -ForegroundColor Green

Write-Step "توليد مفاتيح تشغيل محلية قوية"
$adminApiKey = New-RandomSecret -ByteCount 48
$rateLimitSalt = New-RandomSecret -ByteCount 48
$credentialPath = Save-AdminCredential -AdminKey $adminApiKey
Write-Host "تم حفظ مفتاح الإدارة محليًا بصورة مشفرة في:" -ForegroundColor Green
Write-Host $credentialPath

Write-Step "حفظ الأسرار في GitHub Actions Secrets"
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

Write-Step "تشغيل تهيئة Cloudflare والنشر"
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
    throw "تعذر بدء Workflow التهيئة."
}

$run = $null
for ($attempt = 1; $attempt -le 12 -and -not $run; $attempt++) {
    Start-Sleep -Seconds 5
    $run = Get-LatestBootstrapRun -NotBefore $dispatchStartedAt
}
if (-not $run) {
    throw "بدأ الطلب لكن تعذر تحديد تشغيل GitHub Actions. افتح تبويب Actions في المستودع."
}

Write-Host "رابط التشغيل: $($run.url)" -ForegroundColor Cyan
& gh run watch $run.databaseId --repo $Repository --exit-status
if ($LASTEXITCODE -ne 0) {
    throw "فشل النشر. افتح رابط التشغيل أعلاه لمراجعة الخطوة المتوقفة دون نسخ أي سر إلى السجل."
}

Write-Step "التحقق من ربط الواجهة"
Start-Sleep -Seconds 3
$runtime = & gh api "repos/$Repository/contents/specialists-partners/assets/runtime-config.js?ref=main" --jq '.content'
if ($LASTEXITCODE -eq 0 -and $runtime) {
    $decoded = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($runtime -replace '\s', '')))
    if ($decoded -match 'apiBase:\s*"https://') {
        Write-Host "تم ربط عنوان Worker العام بالواجهة." -ForegroundColor Green
    }
    else {
        Write-Warning "اكتمل Workflow لكن runtime-config.js لا يعرض عنوان API بعد. راجع آخر خطوة في التشغيل."
    }
}

Write-Host "`nاكتمل إعداد الموارد والنشر والربط." -ForegroundColor Green
Write-Host "صفحة القطاع: https://khaledaltheeb.github.io/pterminology-site/specialists-partners/"
Write-Host "لوحة الإدارة: https://khaledaltheeb.github.io/pterminology-site/specialists-partners/admin/"
Write-Host "`nلاسترجاع مفتاح الإدارة محليًا:" -ForegroundColor Yellow
Write-Host "(Import-Clixml '$credentialPath').GetNetworkCredential().Password"
Write-Host "`nبعد نجاح الاختبار الحي، يمكن إلغاء رمز Cloudflare المؤقت وإنشاء رمز تشغيل جديد عند الحاجة." -ForegroundColor Yellow
