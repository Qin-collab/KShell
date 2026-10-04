# 备份 2.0 全部文件（排除 .git / 构建中间产物 / 截图 / 备份自身）
# 生成: .backup/v2.0.0_<时间戳>/  + 同名 zip + manifest.json

$ErrorActionPreference = 'Stop'

$root = 'D:\Code\KShell'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $root '.backup'
$dest = Join-Path $backupRoot "v2.0.0_$stamp"

# 排除规则（相对于项目根）
$excludeDirs = @('.git', '.backup', '__pycache__', 'build', '.shots', 'node_modules')
$excludeNames = @('*.pyc', '*.pyo')

Write-Host "备份目标: $dest" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $dest | Out-Null

# ---------- 收集文件 ----------
function Get-ProjectFiles($base, $current) {
  $items = Get-ChildItem -LiteralPath $current -Force
  foreach ($item in $items) {
    $rel = $item.FullName.Substring($base.Length).TrimStart('\')
    if ($item.PSIsContainer) {
      if ($excludeDirs -contains $item.Name) { continue }
      Get-ProjectFiles $base $item.FullName
    } else {
      $skip = $false
      foreach ($pat in $excludeNames) { if ($item.Name -like $pat) { $skip = $true } }
      if (-not $skip) { $rel }
    }
  }
}

$files = Get-ProjectFiles $root $root | Sort-Object
Write-Host "待备份文件数: $($files.Count)"

# ---------- 复制并计算哈希 ----------
$manifest = @()
$totalBytes = 0
foreach ($rel in $files) {
  $src = Join-Path $root $rel
  $dst = Join-Path $dest $rel
  $dstDir = Split-Path $dst -Parent
  if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
  Copy-Item -LiteralPath $src -Destination $dst -Force

  $hash = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
  $len = (Get-Item -LiteralPath $src).Length
  $totalBytes += $len
  $manifest += [ordered]@{
    path   = $rel.Replace('\', '/')
    size   = $len
    sha256 = $hash
  }
}

# ---------- 写入清单 ----------
$manifestObj = [ordered]@{
  project      = 'KShell'
  version      = '2.0.0'
  backupTime   = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
  fileCount    = $manifest.Count
  totalBytes   = $totalBytes
  note         = '本备份包含 HTML/data/（内含管理员密码哈希），请勿对外分享'
  excludes     = ($excludeDirs + $excludeNames)
  files        = $manifest
}
$manifestPath = Join-Path $dest 'BACKUP-MANIFEST.json'
$json = $manifestObj | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($manifestPath, $json, (New-Object System.Text.UTF8Encoding $false))

# 清单自身不算入文件列表
Write-Host "已复制 $($manifest.Count) 个文件，共 $([math]::Round($totalBytes/1MB,2)) MB"

# ---------- 额外记录 git 状态，便于回滚 ----------
$gitInfo = @()
try {
  $gitInfo += "HEAD: " + (git -C $root rev-parse HEAD 2>$null)
  $gitInfo += "tags: " + ((git -C $root tag -l 2>$null) -join ', ')
  $gitInfo += ""
  $gitInfo += "git status --short:"
  $gitInfo += (git -C $root status --short 2>$null)
} catch { $gitInfo += "（git 信息获取失败）" }
[System.IO.File]::WriteAllLines((Join-Path $dest 'GIT-STATE.txt'), $gitInfo, (New-Object System.Text.UTF8Encoding $false))

# ---------- 打包 zip ----------
$zip = "$dest.zip"
Write-Host "正在压缩..." -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $dest '*') -DestinationPath $zip -CompressionLevel Optimal
$zipMB = [math]::Round((Get-Item $zip).Length / 1MB, 2)

Write-Host ""
Write-Host "备份完成" -ForegroundColor Green
Write-Host "  目录 : $dest"
Write-Host "  压缩 : $zip ($zipMB MB)"
Write-Host "  文件 : $($manifestObj.fileCount) 个"
