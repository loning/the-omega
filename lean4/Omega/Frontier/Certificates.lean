import Omega.Frontier.Assumptions

namespace Omega.Frontier

/-- A finite certificate for a claimed global defect pattern. -/
structure DefectCertificate where
  m : Nat
  k : Nat
  input : Word (m + k)
  claimed : Word m

/-- The Lean-side verifier for a global defect certificate. -/
def DefectCertificate.Valid (c : DefectCertificate) : Prop :=
  globalDefect (Nat.le_add_right c.m c.k) c.input = c.claimed

theorem DefectCertificate.sound (c : DefectCertificate) (h : c.Valid) :
    globalDefect (Nat.le_add_right c.m c.k) c.input = c.claimed :=
  h

/-- A one-step certificate for a local defect claim. -/
structure LocalDefectCertificate where
  m : Nat
  input : Word (m + 1)
  claimed : Word m

def LocalDefectCertificate.Valid (c : LocalDefectCertificate) : Prop :=
  localDefect c.input = c.claimed

theorem LocalDefectCertificate.sound (c : LocalDefectCertificate) (h : c.Valid) :
    localDefect c.input = c.claimed :=
  h

end Omega.Frontier
