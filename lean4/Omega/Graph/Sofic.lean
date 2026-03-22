import Omega.Core.No11
import Omega.Folding.StableSyntax
import Omega.Graph.LabeledGraph

namespace Omega.Graph

/-- The two-state golden-mean graph: the state records the previous bit. -/
def goldenMeanGraph : LabeledGraph Bool Bool where
  edge q b q' := q' = b ∧ ¬ (q = true ∧ b = true)

/-- Canonical state path induced by a binary word. -/
def canonicalPathState (w : Word m) (j : Fin (m + 1)) : Bool :=
  match j.1 with
  | 0 => false
  | k + 1 => get w k

@[simp] theorem canonicalPathState_zero (w : Word m) :
    canonicalPathState w ⟨0, Nat.succ_pos m⟩ = false := by
  simp [canonicalPathState]

@[simp] theorem canonicalPathState_after (w : Word m) (i : Fin m) :
    canonicalPathState w (after i) = w i := by
  simp [canonicalPathState, after, get_of_lt, i.isLt]

theorem acceptsWord_goldenMean_of_no11 {w : Word m} (hNo11 : No11 w) :
    AcceptsWord goldenMeanGraph false w := by
  refine ⟨canonicalPathState w, canonicalPathState_zero w, ?_⟩
  intro i
  refine ⟨canonicalPathState_after w i, ?_⟩
  intro hBad
  rcases i with ⟨n, hn⟩
  rcases hBad with ⟨hPrev, hCur⟩
  cases n with
  | zero =>
      simp [canonicalPathState, before] at hPrev
  | succ k =>
      have hPrev' : get w k = true := by
        simpa [canonicalPathState, before] using hPrev
      have hCur' : get w (k + 1) = true := by
        simpa [get_of_lt w hn] using hCur
      exact hNo11 k hPrev' hCur'

theorem no11_of_acceptsWord_goldenMean {w : Word m} :
    AcceptsWord goldenMeanGraph false w → No11 w := by
  intro hAcc i hi hi1
  rcases hAcc with ⟨qs, _hStart, hStep⟩
  let fi : Fin m := ⟨i, lt_of_get_eq_true hi⟩
  let fi1 : Fin m := ⟨i + 1, lt_of_get_eq_true_succ hi1⟩
  have hEdge : goldenMeanGraph.edge (qs (before fi)) (w fi) (qs (after fi)) := hStep fi
  have hEdgeNext : goldenMeanGraph.edge (qs (before fi1)) (w fi1) (qs (after fi1)) := hStep fi1
  have hWord : w fi = true := by
    simpa [fi, get_of_lt w (lt_of_get_eq_true hi)] using hi
  have hWordNext : w fi1 = true := by
    simpa [fi1, get_of_lt w (lt_of_get_eq_true_succ hi1)] using hi1
  have hAfter : qs (after fi) = true := by
    simpa [hWord] using hEdge.1
  have hIdx : before fi1 = after fi := Fin.ext rfl
  have hBeforeNext : qs (before fi1) = true := by
    simpa [hIdx] using hAfter
  exact hEdgeNext.2 ⟨hBeforeNext, hWordNext⟩

theorem acceptsWord_goldenMean_iff_no11 (w : Word m) :
    AcceptsWord goldenMeanGraph false w ↔ No11 w := by
  constructor
  · exact no11_of_acceptsWord_goldenMean
  · exact acceptsWord_goldenMean_of_no11

/-- The finite stable language is exactly the language accepted by the golden-mean graph. -/
theorem stableLanguage_eq_goldenMean (m : Nat) :
    {w : Word m | No11 w} = {w : Word m | AcceptsWord goldenMeanGraph false w} := by
  ext w
  simp [acceptsWord_goldenMean_iff_no11]

/-- Stable syntax points are accepted by the explicit two-state sofic presentation. -/
theorem acceptsWord_of_stable (x : Omega.X m) :
    AcceptsWord goldenMeanGraph false x.1 :=
  acceptsWord_goldenMean_of_no11 x.2

/-- The golden-mean graph admits edge (false, false, false): state 0 → emit 0 → state 0. -/
theorem goldenMean_edge_ff : goldenMeanGraph.edge false false false := by
  simp [goldenMeanGraph]

/-- The golden-mean graph admits edge (false, true, true): state 0 → emit 1 → state 1. -/
theorem goldenMean_edge_ft : goldenMeanGraph.edge false true true := by
  simp [goldenMeanGraph]

/-- The golden-mean graph admits edge (true, false, false): state 1 → emit 0 → state 0. -/
theorem goldenMean_edge_tf : goldenMeanGraph.edge true false false := by
  simp [goldenMeanGraph]

/-- The golden-mean graph forbids edge (true, true, _): state 1 → emit 1 is forbidden. -/
theorem goldenMean_no_edge_tt (q' : Bool) : ¬ goldenMeanGraph.edge true true q' := by
  simp [goldenMeanGraph]

/-- The golden-mean transfer rule: from state false, both bits are valid. -/
theorem goldenMean_transfer_false (b : Bool) :
    goldenMeanGraph.edge false b b := by
  cases b <;> simp [goldenMeanGraph]

/-- The golden-mean transfer rule: from state true, only bit false is valid. -/
theorem goldenMean_transfer_true_false :
    goldenMeanGraph.edge true false false := goldenMean_edge_tf


end Omega.Graph
