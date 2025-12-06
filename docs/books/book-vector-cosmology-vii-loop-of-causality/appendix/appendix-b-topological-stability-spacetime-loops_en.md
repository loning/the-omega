# Appendix B: Topological Stability of Spacetime Loops

In the main text chapters "Solution to the Grandfather Paradox" and "The Bootstrap," we proposed a seemingly counterintuitive view: the universe allows the existence of Closed Timelike Curves (CTCs), but these loops must be logically self-consistent. In other words, you can go back to the past, but you can only do things that **"cause you to go back"**.

This appendix will provide mathematical proof for this self-consistency principle from the perspectives of **topology** and **nonlinear dynamics**. We will show that time loops are not fragile anomalous structures but extremely robust **Topological Solitons** in Hilbert space.

## B.1 Geometrizing the Novikov Principle

Igor Novikov's self-consistency principle states: in a spacetime containing CTCs, the probability of any locally occurring event must be 1 if self-consistent, and 0 if not.

In **FS geometry**, we can transform this into a **phase condition for path integrals**.

Consider a particle moving along a closed timelike curve, returning to the starting point with state $|\psi_{final}\rangle$, initial state $|\psi_{initial}\rangle$.

For this closed loop to physically exist, the wave function must satisfy the **"Single-valuedness"** condition after one complete cycle (at most differing by a global phase factor):

$$|\psi_{final}\rangle = U_{loop} |\psi_{initial}\rangle = e^{i\theta} |\psi_{initial}\rangle$$

where $U_{loop}$ is the unitary evolution operator along the time closed loop.

This means **the initial state $|\psi_{initial}\rangle$ must be an eigenstate (Eigenstate) of the cyclic evolution operator $U_{loop}$.**

* **Paradox paths** (such as killing grandfather): would cause $|\psi_{final}\rangle$ to be orthogonal to $|\psi_{initial}\rangle$ (alive $\to$ dead). This is not an eigenstate. Their interference terms in the path integral cancel each other, causing the probability amplitude to approach zero.

* **Self-consistent paths** (such as saving grandfather): initial and final states coincide. This constitutes **constructive interference**, amplifying the probability amplitude.

**Conclusion:** Physical laws automatically filter out histories that "can self-close." This requires no external time police; it is a property of wave function self-interference.

## B.2 Topological Protection and Fixed Points

Why are these loops stable? Why don't small perturbations (like the butterfly effect) destroy causal cycles?

This involves the **Fixed Point Theorem**.

Consider the entire history of the universe as a mapping function $f: \text{History} \to \text{History}$.

Time travel means we take an output of history and use it as input again: $x_{new} = f(x_{old})$.

A stable time loop is a **fixed point** of this mapping: $x^* = f(x^*)$.

According to **Brouwer's Fixed Point Theorem**, for any continuous transformation, there exists at least one fixed point on a compact convex set.

In quantum mechanics, since evolution is unitary (continuous and norm-preserving), the density matrix space is a compact convex set. Therefore, **self-consistent quantum histories necessarily exist.**

Moreover, these fixed points often have **topological stability**.

Like a knot on a rope, once tied (causal chain closed), local continuous deformations (small perturbations, fine-tuning of free will) cannot untie the knot.

You are either completely outside the loop or completely inside it.

**Physical Corollary:**

This is why you cannot "accidentally" change history.

History has **"elasticity"**. If you try to deviate from that self-consistent script, physical laws generate a **"topological restoring force"** (manifested as coincidences, malfunctions, or probability distortions), forcibly pushing you back onto the orbit of that fixed point.

## B.3 Entropy of Bootstrap

Finally, let us examine the information entropy problem of "creation from nothing."

In bootstrap (such as the *Hamlet* paradox), information seems to have no origin. Does this violate the second law of thermodynamics?

The answer is: **No. Because the closed loop itself is a maximum entropy state.**

In a time closed loop, information flow is cyclic: $I(t) \to I(t+\Delta t) \to \dots \to I(t)$.

According to Landauer's principle, erasing information produces heat. But in a perfect unitary closed loop, **no information is erased**.

State A evolves to B, and B evolves back to A. This is a **reversible process**.

Therefore, in a perfect bootstrap cycle, **the net entropy production is zero ($\Delta S_{loop} = 0$)**.

This not only does not violate thermodynamics but is even the **most efficient** structure thermodynamically—a **perpetual motion machine (in the geometric sense)**.

**Conclusion:**

Grand loops like "I created the universe, and the universe created me" are **zero-dissipation** superconducting circuits in terms of energy.

Once established, they rotate eternally in Hilbert space, consuming no energy and producing no waste heat. They are the most economical form of **"existence"**.

