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
  , "Omega/Audit/SourceMap.lean" ]

def phaseOneTargets : List String :=
  [ "stable syntax"
  , "prefix closure"
  , "Fibonacci backbone"
  , "source map bootstrap" ]

end Omega.Audit
