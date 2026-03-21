import Omega.Audit.SourceMap

namespace Omega.Audit

def phaseZeroArtifacts : List String :=
  [ "lakefile.lean"
  , "lean-toolchain"
  , "Omega.lean"
  , "Omega/Core/Fib.lean"
  , "Omega/Core/Word.lean"
  , "Omega/Core/No11.lean"
  , "Omega/Folding/StableSyntax.lean"
  , "Omega/Folding/Weight.lean"
  , "Omega/Folding/Value.lean"
  , "Omega/Folding/Zeckendorf.lean"
  , "Omega/Folding/Fold.lean"
  , "Omega/Folding/InverseLimit.lean"
  , "Omega/Folding/Rewrite.lean"
  , "Omega/Folding/Defect.lean"
  , "Omega/SPG/Cylinder.lean"
  , "Omega/SPG/PrefixMetric.lean"
  , "Omega/SPG/Clopen.lean"
  , "Omega/Frontier/Assumptions.lean"
  , "Omega/Frontier/Conditional.lean"
  , "Omega/Frontier/Conjectures.lean"
  , "Omega/Frontier/Certificates.lean"
  , "Omega/Audit/SourceMap.lean" ]

def phaseOneTargets : List String :=
  [ "stable syntax"
  , "prefix closure"
  , "Fibonacci backbone"
  , "stable cardinality recurrence"
  , "Zeckendorf bridge"
  , "finite Fold interface"
  , "inverse-limit bridge"
  , "rewrite kernel"
  , "finite defect telescope"
  , "SPG prefix cylinder layer"
  , "frontier interfaces"
  , "source map bootstrap" ]

end Omega.Audit
