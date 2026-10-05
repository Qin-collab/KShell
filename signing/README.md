# 代码签名说明

本目录存放 KShell Windows 可执行文件的签名材料。

> ⚠️ **`*.pfx` 含私钥，绝对不能提交到仓库或分享。** 已在 `.gitignore` 中排除。

## 文件说明

| 文件 | 内容 | 可否公开 |
|------|------|---------|
| `kshell-codesign.pfx` | 证书 + **私钥**（受密码保护） | ❌ **绝对不可** |
| `kshell-codesign.cer` | 只含公钥的证书 | ✅ 可分发，供用户验证/信任 |
| `README.md` | 本说明 | ✅ |

---

## 关于自签名证书的重要说明

当前使用的是**自签名证书**（自己生成，免费）。它能证明：

- ✅ 文件由持钥者签名，**签名后未被篡改**
- ✅ 带有可信时间戳，证书过期后签名依然有效

但它**不能**做到：

- ❌ Windows 显示"已验证的发布者" —— 仍会显示"未知发布者"
- ❌ 消除 SmartScreen 警告
- ❌ 消除浏览器下载警告

**要消除这些警告，必须购买 CA 签发的代码签名证书**（DigiCert / Sectigo / GlobalSign 等，
OV 证书约 ¥2000/年，EV 证书约 ¥4000/年）。购买后把 CA 给你的 `.pfx` 放到本目录，
用同一个签名脚本即可（`-Pfx` 指定新文件）。

自签名的实际用途：内部/自用分发，以及让"签名后文件未被篡改"可被校验。

---

## 创建证书（首次）

用 PowerShell 内置命令，**不需要下载任何工具**：

```powershell
$pwd = ConvertTo-SecureString -String '你的密码' -Force -AsPlainText

$cert = New-SelfSignedCertificate `
  -Subject "CN=KShell, O=你的组织, OU=KShell Project, C=CN" `
  -Type CodeSigningCert `
  -KeyUsage DigitalSignature `
  -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
  -CertStoreLocation "Cert:\CurrentUser\My" `
  -NotAfter (Get-Date).AddYears(3) `
  -KeyExportPolicy Exportable

# 导出私钥（受密码保护）
Export-PfxCertificate -Cert $cert -FilePath .\signing\kshell-codesign.pfx -Password $pwd

# 导出公钥证书（可分发给用户）
Export-Certificate -Cert $cert -FilePath .\signing\kshell-codesign.cer -Type CERT
```

---

## 签名

```powershell
# 签名 dist 下所有 exe（会提示输入证书密码）
.\tools\sign-windows.ps1

# 只签名指定文件
.\tools\sign-windows.ps1 -Path .\dist\kshell_windows_x64_v2.1.exe

# 自动化：密码从环境变量读取，不写进脚本
$env:KSH_SIGN_PASSWORD = '你的密码'
.\tools\sign-windows.ps1
```

**为什么不用 signtool**：PowerShell 的 `Set-AuthenticodeSignature` 基于同一套
CryptoAPI，功能等效，而 `signtool.exe` 需要安装 Windows SDK。网上第三方站点提供的
`signtool.exe` 是常见的恶意软件载体，不建议下载。

---

## 验证

```powershell
Get-AuthenticodeSignature .\dist\kshell_windows_x64_v2.1.exe | Format-List *
```

自签名证书下 `Status` 会是 `UnknownError`（提示"证书链在不受信任的根证书中终止"），
这是**预期行为** —— 表示签名存在但根证书未被本机信任。可以查看：

```powershell
$sig = Get-AuthenticodeSignature .\dist\kshell_windows_x64_v2.1.exe
$sig.SignerCertificate.Subject        # 签名者
$sig.SignerCertificate.Thumbprint     # 证书指纹
$sig.TimeStamperCertificate.Subject   # 时间戳颁发者
```

---

## 让本机信任自签名证书（可选）

若希望本机把该签名识别为"有效"，需把公钥证书装进**受信任的根证书颁发机构**：

```powershell
# 需要管理员权限的 PowerShell
Import-Certificate -FilePath .\signing\kshell-codesign.cer `
  -CertStoreLocation Cert:\LocalMachine\Root
```

⚠️ **注意**：把自己的自签名证书装入"受信任的根"意味着本机**完全信任**由该私钥签名的
任何内容。只应在你掌控私钥、且理解该风险的机器上这样做。**不要要求用户这样做**。

---

## 换用正式证书（购买后）

1. 把 CA 提供的 `.pfx` 放到本目录（例如 `kshell-official.pfx`）
2. 签名时指定：
   ```powershell
   .\tools\sign-windows.ps1 -Pfx .\signing\kshell-official.pfx
   ```
3. 建议改用 CA 推荐的时间戳服务器：
   ```powershell
   .\tools\sign-windows.ps1 -TimestampServer http://timestamp.sectigo.com
   ```
4. 换掉证书后，用户侧看到的发布者名称会变成证书里的组织名，SmartScreen 警告
   会随下载量累积逐步消除。
