# Local synthetic test launcher. No host Python/Node installation required.
[CmdletBinding()]
param(
    [ValidateSet('Start','Stop','Status','Check','Credentials')]
    [string]$Action = 'Start',
    [ValidateRange(1024,65535)] [int]$Port = 8000
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$privatePath = Join-Path $repoPath 'deploy/laptop-private'
$envPath = Join-Path $privatePath '.env'
$composePath = Join-Path $repoPath 'deploy/compose.laptop.yml'

function Invoke-Compose {
    param([string[]]$DockerArguments)
    & docker compose --env-file $envPath -f $composePath @DockerArguments
    if ($LASTEXITCODE -ne 0) { throw 'Docker operation failed; check Docker Desktop and the local test services.' }
}
function New-LocalHex {
    $buffer = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($buffer)).Replace('-','').ToLowerInvariant()
}
function Protect-PrivateFolder {
    if ((Get-Item -LiteralPath $privatePath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'The private folder must not be a junction or symbolic link.'
    }
    if ($env:OS -eq 'Windows_NT') {
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $acl.SetAccessRuleProtection($true, $false)
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
        $inheritance = [System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
        foreach ($sid in @($identity, [System.Security.Principal.SecurityIdentifier]'S-1-5-18', [System.Security.Principal.SecurityIdentifier]'S-1-5-32-544')) {
            $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', $inheritance, 'None', 'Allow')
            $acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $privatePath -AclObject $acl
    } else {
        & chmod 700 $privatePath
        if ($LASTEXITCODE -ne 0) { throw 'Private directory permissions unavailable.' }
    }
}

function Protect-PrivateFile {
    if ((Get-Item -LiteralPath $envPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'The private env file must not be a symbolic link.'
    }
    if ($env:OS -eq 'Windows_NT') {
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $acl.SetAccessRuleProtection($true, $false)
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
        foreach ($sid in @($identity, [System.Security.Principal.SecurityIdentifier]'S-1-5-18', [System.Security.Principal.SecurityIdentifier]'S-1-5-32-544')) {
            $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'Allow')
            $acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $envPath -AclObject $acl
    } else {
        & chmod 600 $envPath
        if ($LASTEXITCODE -ne 0) { throw 'Private file permissions unavailable.' }
    }
}

Push-Location $repoPath
try {
    $containerOs = & docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0 -or $containerOs -ne 'linux') { throw 'Start Docker Desktop with Linux containers / WSL2 first.' }
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose v2 is required.' }
    $existingEnv = Get-Item -LiteralPath $envPath -Force -ErrorAction SilentlyContinue
    if ($existingEnv -and ($existingEnv.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Symbolic configuration rejected.' }
    if (-not (Test-Path -LiteralPath $envPath)) {
        if ($Action -ne 'Start') { throw 'Run Start once to initialize the synthetic test installation.' }
        New-Item -ItemType Directory -Path $privatePath -Force | Out-Null
        Protect-PrivateFolder
        $commit = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $commit -notmatch '^[a-f0-9]{40}$') { throw 'A reviewed Git checkout is required.' }
        $configuration = @(
            "LAPTOP_OWNER_PASSWORD=$(New-LocalHex)",
            "LAPTOP_RUNTIME_PASSWORD=$(New-LocalHex)",
            "LAPTOP_MFA_KEY=$(New-LocalHex)",
            "LAPTOP_STORAGE_KEY=$(New-LocalHex)",
            "LAPTOP_RELEASE_COMMIT=$commit",
            "LAPTOP_HTTP_PORT=$Port"
        ) -join "`n"
        # Do not overwrite prior keys/database credentials on a restart.
        [IO.File]::WriteAllText($envPath, $configuration + "`n", [Text.UTF8Encoding]::new($false))
        if ($env:OS -ne 'Windows_NT') { & chmod 600 $envPath }
    } else {
        Protect-PrivateFolder
        if ((Get-Item -LiteralPath $envPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'The private env file must not be a symbolic link.'
        }
    }
    Protect-PrivateFile
    switch ($Action) {
        'Start' {
            Invoke-Compose -DockerArguments @('build','api')
            Invoke-Compose -DockerArguments @('up','-d','--wait','db')
            Invoke-Compose -DockerArguments @('run','--rm','--no-deps','setup')
            Invoke-Compose -DockerArguments @('up','-d','--wait','api')
            Invoke-Compose -DockerArguments @('exec','-T','api','python','-m','mcias.seed.laptop','check')
            $portLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^LAPTOP_HTTP_PORT=' }
            $activePort = $portLine.Split('=',2)[1]
            Write-Host "Synthetic test installation ready: http://127.0.0.1:$activePort"
            Write-Host 'Use -Action Credentials privately for test passwords and TOTP enrollment secrets. Production approval: NO.'
        }
        'Stop' { Invoke-Compose -DockerArguments @('stop') }
        'Status' { Invoke-Compose -DockerArguments @('ps') }
        'Check' { Invoke-Compose -DockerArguments @('exec','-T','api','python','-m','mcias.seed.laptop','check') }
        'Credentials' {
            Write-Host 'Private test credentials follow. Do not share, screenshot or include them in reports.'
            Invoke-Compose -DockerArguments @('exec','-T','api','python','-m','mcias.seed.laptop','credentials')
        }
    }
} finally { Pop-Location }
