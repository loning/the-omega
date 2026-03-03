param(
  [switch]$KeepAux
)

$ErrorActionPreference = "Stop"
$paperDir = Split-Path -Parent $PSScriptRoot
Set-Location $paperDir

function Invoke-Checked {
  param([string]$File, [string[]]$CommandArgs)
  Write-Host ">> $File $($CommandArgs -join ' ')"
  & $File @CommandArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$File failed with exit code $LASTEXITCODE"
  }
}

function Which {
  param([string]$Name)
  return (Get-Command $Name -ErrorAction SilentlyContinue) -ne $null
}

if (Which "latexmk") {
  Invoke-Checked -File "latexmk" -CommandArgs @(
    "-pdf",
    "-interaction=nonstopmode",
    "-file-line-error",
    "main.tex"
  )
}
else {
  $engine = if (Which "pdflatex") { "pdflatex" } else { throw "No latex engine found. Install MiKTeX/TeX Live." }
  $bibtex = Which "bibtex"

  Invoke-Checked -File $engine -CommandArgs @("-interaction=nonstopmode","-halt-on-error","main.tex")
  if ($bibtex) {
    Invoke-Checked -File "bibtex" -CommandArgs @("main")
  }
  Invoke-Checked -File $engine -CommandArgs @("-interaction=nonstopmode","-halt-on-error","main.tex")
  Invoke-Checked -File $engine -CommandArgs @("-interaction=nonstopmode","-halt-on-error","main.tex")
}

if (-not $KeepAux) {
  $auxFiles = @(
    "main.aux","main.log","main.bbl","main.blg","main.out","main.toc","main.lof","main.lot",
    "main.fdb_latexmk","main.fls","main.synctex.gz","main.xdv"
  )
  $auxFiles | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -ErrorAction SilentlyContinue }
  }
}

if (-not (Test-Path "main.pdf")) {
  throw "Build completed but main.pdf not found."
}

Write-Host "Build succeeded: $paperDir\main.pdf"
