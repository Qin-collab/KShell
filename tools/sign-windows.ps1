# ============================================================
# KShell Windows 可执行文件数字签名脚本
#
# 用法:
#   .\tools\sign-windows.ps1                     # 签名 dist\*.exe
#   .\tools\sign-windows.ps1 -Path foo.exe       # 签名指定文件
#   .\tools\sign-windows.ps1 -Pfx other.pfx      # 使用其他证书
#
# 证书密码来源（按优先级）:
#   1. -Password 参数
#   2. 环境变量 KSH_SIGN_PASSWORD
#   3. 交互式安全提示输入
#
# 注意: 密码不要写进本脚本或任何提交到仓库的文件。
#
# 为什么不用 signtool:
#   PowerShell 内置 Set-AuthenticodeSignature（基于 CryptoAPI），
#   功能与 signtool 等效，无需安装 Windows SDK，也避免下载第三方 exe。
# ============================================================

[CmdletBinding()]
param(
    # 要签名的文件（默认 dist 目录下所有 exe）
    [string[]]$Path,

    # PFX 证书路径
    [string]$Pfx = (Join-Path $PSScriptRoot '..\signing\kshell-codesign.pfx'),

    # 证书密码
    [string]$Password,

    # 时间戳服务器（RFC3161）。设为空字符串可跳过时间戳
    [string]$TimestampServer = 'http://timestamp.digicert.com'
)

$ErrorActionPreference = 'Stop'

function Get-SignPassword {
    if ($Password) { return $Password }
    if ($env:KSH_SIGN_PASSWORD) { return $env:KSH_SIGN_PASSWORD }
    $secure = Read-Host -Prompt '请输入证书密码' -AsSecureString
    return [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}

# ---------- 定位待签名文件 ----------
if (-not $Path -or $Path.Count -eq 0) {
    $distDir = Join-Path $PSScriptRoot '..\dist'
    $Path = @(Get-ChildItem -LiteralPath $distDir -Filter '*.exe' -ErrorAction SilentlyContinue |
              Select-Object -ExpandProperty FullName)
}

if (-not $Path -or $Path.Count -eq 0) {
    Write-Error "没有找到要签名的 exe 文件"
}

# ---------- 检查证书 ----------
if (-not (Test-Path -LiteralPath $Pfx)) {
    Write-Error "找不到证书文件: $Pfx`n先执行 signing 目录下 README 中的'创建证书'步骤。"
}

$plainPwd = Get-SignPassword
$securePwd = ConvertTo-SecureString -String $plainPwd -Force -AsPlainText

Write-Host "导入证书: $Pfx" -ForegroundColor Cyan
$cert = Get-PfxCertificate -FilePath $Pfx -Password $securePwd

if (-not $cert) { Write-Error "证书导入失败（密码是否正确？）" }

Write-Host "  签名者: $($cert.Subject)" -ForegroundColor Gray
Write-Host "  指纹  : $($cert.Thumbprint)" -ForegroundColor Gray
Write-Host "  有效期: $($cert.NotBefore.ToString('yyyy-MM-dd')) ~ $($cert.NotAfter.ToString('yyyy-MM-dd'))" -ForegroundColor Gray
Write-Host ''

# ---------- 逐个签名 ----------
$ok = 0
$fail = 0

foreach ($file in $Path) {
    if (-not (Test-Path -LiteralPath $file)) {
        Write-Host "  跳过（不存在）: $file" -ForegroundColor Yellow
        $fail++
        continue
    }

    $name = Split-Path $file -Leaf
    Write-Host "签名: $name" -ForegroundColor Cyan

    try {
        if ($TimestampServer) {
            $result = Set-AuthenticodeSignature -FilePath $file -Certificate $cert `
                      -HashAlgorithm SHA256 -TimestampServer $TimestampServer
        } else {
            $result = Set-AuthenticodeSignature -FilePath $file -Certificate $cert `
                      -HashAlgorithm SHA256
        }

        $sig = Get-AuthenticodeSignature -FilePath $file
        $stamp = if ($sig.TimeStamperCertificate) { '已加时间戳' } else { '无时间戳' }

        if ($sig.SignerCertificate) {
            Write-Host "  完成: SHA256 / $stamp" -ForegroundColor Green
            Write-Host "  状态: $($sig.Status)（自签名证书会显示 UnknownError，属正常）" -ForegroundColor Gray
            $ok++
        } else {
            Write-Host "  失败: $($result.StatusMessage)" -ForegroundColor Red
            $fail++
        }
    } catch {
        Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
        $fail++
    }
    Write-Host ''
}

Write-Host "签名完成: 成功 $ok 个，失败 $fail 个" -ForegroundColor $(if ($fail) { 'Yellow' } else { 'Green' })

if ($fail -gt 0) { exit 1 }
