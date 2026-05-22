param(
    [Parameter(Mandatory=$true)]
    [string]$Message
)

$BridgePath = "c:\Users\채송이\Desktop\Antigravity(AI Work)\.mcp_bridge\task.md"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$NewContent = @"

## 💬 User Message ($Timestamp)
$Message
"@

Add-Content -Path $BridgePath -Value $NewContent

Write-Host "✅ 명령이 클로드 브릿지에 전달되었습니다: $BridgePath" -ForegroundColor Cyan
