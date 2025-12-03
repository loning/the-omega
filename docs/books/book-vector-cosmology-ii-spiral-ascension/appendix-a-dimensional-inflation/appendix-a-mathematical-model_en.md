# Appendix A: Mathematical Model of Dimensional Inflation

In the main text of *Vector Cosmology II*, we proposed a revolutionary hypothesis: the universe's total budget $c_{FS}$ is not constant, but undergoes exponential inflation with the passage of intrinsic time $\tau$. This hypothesis explains the origin of dark energy and the inevitable growth of complexity.

This appendix provides a rigorous mathematical formulation for this "Red Queen's race." We will derive the modified FS capacity equation under dimensional inflation and show how it naturally leads to a cosmological constant-like term.

## A.1 Dynamic Budget Axiom

In the first book, we defined the FS speed constraint as $||\dot{\Psi}(\tau)||_{FS} = c_{FS}$, where $c_{FS}$ is a constant.

In the spiral universe model, we elevate $c_{FS}$ to a time-evolving function $C(\tau)$.

Assume the effective dimension $D(\tau)$ of Hilbert space grows exponentially with intrinsic time $\tau$ (corresponding to continuous insertion of QCA grid points or release of degrees of freedom):

$$D(\tau) = D_0 e^{\lambda \tau}$$

where $\lambda > 0$ is the **Dimensional Inflation Rate**.

To maintain the "existence density" per unit degree of freedom from collapsing, the total information update rate $C(\tau)$ must keep pace with (or at least be driven by) dimensional growth. We set:

$$C(\tau) = c_0 e^{\lambda \tau}$$

## A.2 Modified Pythagorean Identity

In an expanding reference frame, we need to reconsider the decomposition of tangent vectors.

Consider the global vector $|\Psi(\tau)\rangle$. Its evolution velocity now contains two parts:

1.  **Unitary Rotation Component ($v_{rot}$)**: Corresponds to traditional physical evolution (motion, mass).

2.  **Radial Expansion Component ($v_{rad}$)**: Corresponds to the expansion of Hilbert space itself (dark energy flow).

According to the geometric intuition of Naimark's dilation theorem, if we attempt to describe this process in a "comoving frame" (the stationary reference frame we perceive macroscopically), we need to introduce a **Scale Factor** $a(\tau) = e^{\lambda \tau}$.

The modified capacity identity is written as:

$$v_{ext}^2(\tau) + v_{int}^2(\tau) + v_{env}^2(\tau) = C^2(\tau) - \mathcal{K}(\tau)$$

where $\mathcal{K}(\tau)$ is the **Expansion Curvature Term**.

If we divide both sides by the square of the scale factor $a^2(\tau)$ to obtain the "renormalized" physical quantities we observe $\tilde{v} = v/a(\tau)$:

$$\tilde{v}_{ext}^2 + \tilde{v}_{int}^2 + \tilde{v}_{env}^2 = c_0^2 - \frac{\mathcal{K}(\tau)}{e^{2\lambda \tau}}$$

## A.3 Geometric Derivation of Dark Energy

Now let us analyze this residual term.

In standard cosmology, the Friedmann equation contains a cosmological constant $\Lambda$. In our geometric model, this term directly arises from the **Slippage** between the growth rate of $C(\tau)$ and the actual evolution rate of the system.

If the system's evolution perfectly keeps pace with expansion (perfect running in the Red Queen's race), physical laws appear conserved. But if there is a slight mismatch, a non-zero background flow emerges.

We define the **Effective Dark Energy Density** $\rho_{DE}$ as the extra budget flow per unit volume:

$$\rho_{DE} \propto \frac{d}{d\tau} C(\tau) - \text{Tr}(\text{Matter Flux})$$

Substituting the exponential growth model, we obtain:

$$\rho_{DE} \approx \lambda^2 c_0^2$$

This is a remarkable result: **Dark energy density is proportional to the square of the dimensional inflation rate $\lambda$.**

* It is not vacuum zero-point energy (which would lead to a $10^{120}$-fold error).

* It is the **acceleration of geometric growth**.

This means that the so-called "repulsive force" is actually an **inertial force**. Just as you feel pushed against the seatback in an accelerating car, we feel galaxies being "pushed apart" in an accelerating expanding Hilbert space. That is not a force; it is the **non-inertial expansion** of the reference frame.

## A.4 Dilution and Survival Equations

Finally, we derive the decay equation for material weight.

Let a particle (e.g., a proton) maintain an internal structure velocity $v_{int}^{proton}$. If it remains static (non-evolving), then $v_{int}^{proton}$ is constant.

Its **Relative Ontological Weight** $W$ in the universe's total budget is:

$$W(\tau) = \frac{v_{int}^{proton}}{C(\tau)} = \frac{v_{int}^{proton}}{c_0} e^{-\lambda \tau}$$

This gives a half-life prediction for material decay. When $W(\tau)$ drops to Planck-scale quantum fluctuation levels (i.e., $W \sim 1/\sqrt{D}$), the particle becomes indistinguishable from background noise, leading to **Dissolution**.

To avoid dissolution, the system must make its own $v_{int}$ grow with time:

$$\frac{\dot{v}_{int}}{v_{int}} \ge \lambda$$

This is the **"Evolution Inequality"**. It mathematically proves that in a spiral universe, only exponentially growing complexity (life/civilization) possesses long-term ontological status.

