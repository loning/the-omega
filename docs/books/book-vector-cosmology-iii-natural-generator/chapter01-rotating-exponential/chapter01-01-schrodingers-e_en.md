# 1.1 Schrödinger's $e$

![Continuous Compounding](../../assets/ch01_continuous_compounding_1765302141350.png)

> "Why does the universe not only allow time superposition but also require that this superposition must transform into state multiplication? Because in the logic of $e$, each second is not merely added after the previous second; it 'grows' from the previous second."

## Physics' Exponential Dependence

In classical mechanics, we are accustomed to linear thinking. If you push a box, its acceleration is proportional to the force. This is an additive logic.

But in quantum mechanics, the Schrödinger equation $|\dot{\psi}\rangle = -iH|\psi\rangle$ describes a completely different dynamics. It tells us: **The rate of change of state is proportional to the state itself.**

This relationship has only one mathematical solution: **the exponential function**.

$$|\psi(t)\rangle = e^{-iHt} |\psi(0)\rangle$$

Here, $H$ (the Hamiltonian) plays the role of the "generator" we mentioned in the prologue. And $e$ is the machine that "unfolds" this generator into the long river of time.

Why must physical laws be written in this form?

This is not merely for mathematical convenience; it is determined jointly by **the continuity of time** and **the cumulativeness of causality**.

## Addition Becomes Multiplication: The Magic of Groups

Let us perform a thought experiment.

Suppose the universe evolves for $t_1$ seconds, then evolves for another $t_2$ seconds.

* In the dimension of **time**, this is an additive process: total time $T = t_1 + t_2$.

* In the dimension of **state**, this is the sequential action of two operations: $U(T) = U(t_2) \cdot U(t_1)$.

To make these two logics self-consistent, we need a function $f(t)$ that satisfies:

$$f(t_1 + t_2) = f(t_2) \cdot f(t_1)$$

In the mathematical kingdom, only the **exponential function** possesses this magic of transforming "addition" into "multiplication":

$$e^{A+B} = e^A \cdot e^B$$

(when $A$ and $B$ commute).

This is called **the relationship between Lie groups and Lie algebras** in group theory.

* **The time axis ($t$)** is flat and linear (Lie algebra parameter).

* **The evolution operator ($U$)** is curved and multiplicative (Lie group element).

**$e$ is the only bridge connecting these two worlds.**

It tells us that the evolution of the universe is not like laying bricks, adding one piece after another. The evolution of the universe is like cell division or bank interest, accumulated through **"self-multiplication"**.

When we discuss discrete updates of QCA (Quantum Cellular Automata) in the paper, we write $|\Psi_n\rangle = U^n |\Psi_0\rangle$.

Notice that $n$-th power.

At the microscopic discrete level, evolution is $U$ multiplied $n$ times.

In the macroscopic continuous limit, the limit of $(1 + \epsilon)^n$ naturally emerges as $e^{t}$.

## Continuous Compounding

If we regard $c_{FS}$ as the universe's "principal" and the Hamiltonian $H$ as the "interest rate," then physical evolution is a calculation of **Continuous Compounding**.

* **Classical thinking**: If you have 1 dollar and the interest rate is 100%, after one year you have 2 dollars.

* **Quantum thinking ($e$)**: If you settle interest at every moment, and the interest immediately becomes principal participating in the next round of interest generation, then after one year you will have $e \approx 2.718$ dollars.

The universe chooses the latter.

It does not wait. It does not pay in installments. At every moment of birth and death at the Planck scale, it is performing this ultimate "compound interest."

It is precisely this mechanism of **"every moment evolving based on all information from the previous moment"** that endows the physical world with continuity and the weightiness of causality.

## Physical Embodiment of the Generator

In the first book of this series, we defined FS speed $v_{FS} = \Delta K$ (variance of the generator).

Now we understand the true status of $K$.

$K$ (or $H$) is not a passive descriptor; it is a **seed**.

The entire history of the universe—that grand trajectory extending billions of years in Hilbert space—is actually already folded and compressed into the generator $H$ at the moment $t=0$.

As long as we have $H$ and the initial state, then through **$e$**, this decompression algorithm, all futures automatically flow forth.

This gives us a deeper understanding of "determinism": **The universe does not need to make decisions every second. The universe only needs to define its generator at the beginning, and the rest is left to $e$ for automatic generation.**

However, careful readers will notice that Schrödinger's formula contains not only $e$ but also a strange symbol—**$i$ (the imaginary unit)**.

Without this $i$, the universe would be a pure exponential explosion (like bacterial reproduction), and all budgets would be instantly exhausted.

It is precisely because of $i$ that the exponential explosion is tamed into **"rotation"**.

This leads to the theme of the next section: **Imaginary as Orthogonal**. We will see why the universe must operate in the imaginary dimension to maintain that perfect conservation and circle.

