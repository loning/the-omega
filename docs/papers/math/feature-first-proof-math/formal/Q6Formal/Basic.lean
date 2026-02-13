namespace Q6Formal

def ratioNumerator (k : Nat) : Nat := k + 4

theorem ratio_unbounded_nat (C : Nat) : Exists (fun k : Nat => ratioNumerator k > 5 * C) := by
  refine Exists.intro (5 * C + 1) ?_
  have h1 : 5 * C < 5 * C + 1 := Nat.lt_succ_self (5 * C)
  have h2 : 5 * C + 1 <= 5 * C + 1 + 4 := Nat.le_add_right (5 * C + 1) 4
  exact
    Nat.lt_of_lt_of_le h1
      (by
        simpa [ratioNumerator, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm] using h2)

theorem no_uniform_bound_nat :
    Not (Exists (fun C : Nat => forall k : Nat, ratioNumerator k <= 5 * C)) := by
  intro h
  cases h with
  | intro C hC =>
      cases ratio_unbounded_nat C with
      | intro k hk =>
          exact Nat.not_le_of_lt hk (hC k)

end Q6Formal
