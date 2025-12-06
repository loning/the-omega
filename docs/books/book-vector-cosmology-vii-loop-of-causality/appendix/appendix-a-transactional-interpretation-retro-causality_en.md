# Appendix A: The Mathematics of Transactional Interpretation and Retro-causality

In the main text of *Vector Cosmology VII: The Loop of Causality*, we proposed a grand physical picture: the history of the universe is established by "retarded waves" (from the past) and "advanced waves" (from the future) meeting in spacetime and performing a "handshake." This view is not pure philosophical speculation but has a solid physical foundation.

This appendix will delve into **Wheeler-Feynman Absorber Theory** and **Transactional Interpretation of Quantum Mechanics (TIQM)**, providing rigorous mathematical proof for the retro-causal logic that "the future determines the past." We will show that at the foundation of Maxwell's equations and Schrödinger's equation, the arrow of time is not only reversible but bidirectionally interlocked.

## A.1 Time Symmetry of Maxwell's Equations

The core equations of classical electrodynamics—Maxwell's equations—are **symmetric** under time reversal ($t \to -t$). This means the wave equation has two mathematically equally valid solutions:

1.  **Retarded Solution ($F_{ret}$)**:

    Describes waves spreading outward from the source, propagating toward the future. This is the familiar "cause leads to effect."

    $$A_{ret}(t) \propto \frac{e^{-i\omega(t - r/c)}}{r}$$

2.  **Advanced Solution ($F_{adv}$)**:

    Describes waves converging from infinity toward the source, propagating **backward in time**. This is usually discarded as "unphysical" in classical physics.

    $$A_{adv}(t) \propto \frac{e^{-i\omega(t + r/c)}}{r}$$

However, Wheeler and Feynman pointed out in 1945 that if we want to explain the physical origin of radiation damping, we cannot simply discard the advanced solution. They proposed that electromagnetic radiation is a **bidirectional interaction** between an **"Emitter"** and an **"Absorber"**.

* The emitter sends retarded waves (toward the future).

* After receiving retarded waves, the absorber is stimulated to emit advanced waves (toward the past).

* These two waves superpose in spacetime, forming the physical reality we observe.

## A.2 The Quantum Handshake Mechanism

John Cramer introduced this idea into quantum mechanics, establishing the **Transactional Interpretation (TIQM)**. In TIQM, wave function collapse is no longer a mysterious observer effect but the completion of a **"Handshake"** process.

A quantum event (transaction) consists of four steps:

1.  **Offer Wave**:

    The emitter (past source, such as the Big Bang or an atom) emits a retarded wave $|\Psi(t)\rangle$ (the standard Schrödinger wave function) at time $t_1$. It spreads toward the future, seeking possible endpoints.

2.  **Confirmation Wave**:

    The absorber (future detector or observer) receives the offer at time $t_2$. In response, it emits an advanced wave $|\Psi(t)\rangle^*$ (the **complex conjugate** of the wave function) toward the past.

    This wave flows **upstream** along the time axis, precisely retracing to the emission point.

3.  **Handshake**:

    The retarded and advanced waves meet in the spacetime interval $[t_1, t_2]$ and undergo **Constructive Interference**.

    Their product forms the basis of Born's probability rule:

    $$P = |\Psi|^2 = \Psi \cdot \Psi^*$$

    This is not just probability; this is the **"strength of transaction success"**.

4.  **Collapse**:

    Once the handshake completes (forming a standing wave), energy and quantum numbers are transmitted between $t_1$ and $t_2$.

    In regions $t < t_1$ and $t > t_2$, and on other paths that did not achieve handshake, the wave function undergoes **Destructive Interference** and vanishes.

    This explains why we only see the "particle" taking one definite path—because only that path achieved a "contract" between supply and demand.

**Conclusion:**

The present observer (absorber), by sending advanced waves $\Psi^*$, **reversely selects** past history.

Without future confirmation waves, past offer waves cannot form standing waves and cannot become physical reality (remaining only as ghostly superposition states).

## A.3 Closed Timelike Curves and Fixed Points

On the grander scale of general relativity, if spacetime structure allows **Closed Timelike Curves (CTCs)** (i.e., time loops), how do we avoid the grandfather paradox?

David Deutsch used quantum computation theory to prove the **self-consistency condition**.

For a quantum system containing a time closed loop, its density matrix $\rho$ must satisfy the **Fixed Point Equation**:

$$\rho_{in} = \text{Tr}_{env} [ U (\rho_{in} \otimes \rho_{ancilla}) U^\dagger ]$$

Simply put, **the state entering the time machine must equal the state exiting the time machine.**

This means:

* The universe's evolution operator $U$ automatically **filters** out states that lead to paradoxes (zero probability).

* Only **"logically self-consistent"** histories (such as you going back not only not killing your grandfather but saving him) can have their probability amplitudes amplified in the closed loop.

**Physical Fatalism:**

This mathematically proves the core argument of **The Loop of Causality**: **Existence is reasonable; occurrence is necessary.**

Because any unreasonable (paradox-causing) history has already been self-cancelled in the underlying mechanism of quantum interference. The reason we can have this coherent historical line is that it is the only global optimal solution among all possible path integrals that satisfies the condition of **"end-to-end connection ($e^{iS}$ phase closure)"**.

