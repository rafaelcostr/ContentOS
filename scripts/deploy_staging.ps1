# Deploy ContentOS staging overlay (Tier E5)
param(
    [Parameter(Mandatory = $true)]
    [string]$ImageRoot,
    [Parameter(Mandatory = $true)]
    [string]$Tag,
    [string]$OverlayPath = "k8s/overlays/staging"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location (Join-Path $root $OverlayPath)

$services = @("gateway", "workflow-engine", "agents-worker", "ai-gateway", "dashboard")
$args = @("edit", "set", "image")
foreach ($svc in $services) {
    $args += "contentos/${svc}=${ImageRoot}/${svc}:${Tag}"
}
kubectl kustomize --help | Out-Null
kustomize @args

Set-Location $root
kubectl apply -k $OverlayPath
Write-Host "Deployed staging with tag $Tag"
