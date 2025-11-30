# Appendix D.1: The Kernel Source & Dependencies

**—— Refactoring Code on the Shoulders of Giants**

**"No great system is written from scratch. We cite predecessors' libraries, but rewrite the calling logic."**

---

## 1. Primary Source

The core theoretical architecture, mathematical derivations, and main theorems of this book (including the Generalized Parseval Identity, the relationship between FS speed and Wigner-Smith delay, FS-Levinson relation, etc.) directly originate from the following foundational document. This is the initial Commit of this "refactoring project."

* **[Kernel v1.0]** **Ma, Haobo.** "Time as Fubini-Study Arc-Length: A Unified Geometric Capacity Framework for Quantum, Relativistic, and Scattering Time Scales." *AELF PTE LTD., Singapore*, Dec 1, 2025.

  * *Note:* This book is an expansion and engineering interpretation of that paper. All derivations regarding $v_{ext}^2 + v_{int}^2 = c_{FS}^2$ and details of QCA microscopic implementation are based on this work.

## 2. Foundational Libraries

The FS-QCA architecture did not emerge from nothing; it deeply depends on time-tested "standard libraries" in physics and information science. The following are key modules we call when building the universe kernel.

### Geometry & QSL

* **Anandan, J., & Aharonov, Y.** "Geometry of Quantum Evolution." *Phys. Rev. Lett.* 65, 1697 (1990).

  * *Function Called:* Provides fundamental algorithms for geometric phases and distances in projective Hilbert space.

* **Mandelstam, L., & Tamm, I.** "The Uncertainty Relation Between Energy and Time in Non-relativistic Quantum Mechanics." *J. Phys. USSR* 9, 249 (1945).

  * *Function Called:* Provides the original implementation of `SpeedLimit`. This book reconstructs it as geodesic constraints in FS geometry.

### Micro-Architecture & Causality

* **Lieb, E. H., & Robinson, D. W.** "The Finite Group Velocity of Quantum Spin Systems." *Commun. Math. Phys.* 28, 251 (1972).

  * *Function Called:* Provides mathematical proof of `v_LR` (maximum signal speed). This is a core dependency of Chapter 2.2 in this book.

* **Arrighi, P.** "Quantum Cellular Automata." *Natural Computing* (2019).

  * *Function Called:* Provides standard model definition of QCA, used to replace continuous field theory as underlying hardware.

### I/O Interface & Scattering

* **Wigner, E. P.** "Lower Limit for the Energy Derivative of the Scattering Phase Shift." *Phys. Rev.* 98, 145 (1955).

  * *Function Called:* Defines the original concept of `TimeDelay`.

* **Smith, F. T.** "Lifetime Matrix in Collision Theory." *Phys. Rev.* 118, 349 (1960).

  * *Function Called:* Defines the `Q` operator (Wigner-Smith operator), which is the core object of Chapter 4.1 in this book.

* **Levinson, N.** "On the Uniqueness of the Potential in a Schrödinger Equation for a Given Asymptotic Phase." *Kgl. Danske Videnskab. Selskab Mat.-fys. Medd.* 25 (1949).

  * *Function Called:* Provides the original theorem for topological checksum (bound state counting).

### System Logs & Entropy

* **Landauer, R.** "Irreversibility and Heat Generation in the Computing Process." *IBM J. Res. Dev.* 5, 183 (1961).

  * *Function Called:* Establishes the `Cost` function between information erasure and physical resource consumption.

* **Fannes, M.** "A Continuity Property of the Entropy Density for Spin Lattice Systems." *Commun. Math. Phys.* 31, 291 (1973).

  * *Function Called:* Provides continuity bounds required for entropy speed limits.

---

## 3. Acknowledgments

**To the Legacy Architects:**

Thanks to **Albert Einstein**—although we refactored your spacetime code, your vision that "geometry is physics" remains the design blueprint of this project.

Thanks to **Erwin Schrödinger** and **Werner Heisenberg**—the `WaveFunction` and `MatrixMechanics` class libraries you wrote remain the most stable parts of the kernel to this day.

Thanks to **Claude Shannon** and **Alan Turing**—you made us realize that the universe is ultimately about information (Bit) and computation (Logic).

**To the Community:**

This project is deeply influenced by the open-source spirit of the quantum information, holographic principle (AdS/CFT), and digital physics communities. Special thanks to those pioneers who dared to question continuous spacetime and propose "It from Bit."

**To the Reader & Future Hackers:**

This book is now in your hands.

The code is open source, the documentation is written.

The universe still has countless bugs waiting for you to discover, countless extension modules waiting for you to write.

Don't be satisfied with reading documentation—go **run** it.

**EOF (End of File).**

