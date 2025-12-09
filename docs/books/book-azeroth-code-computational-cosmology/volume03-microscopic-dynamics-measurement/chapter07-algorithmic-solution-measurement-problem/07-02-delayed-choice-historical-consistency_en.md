# 7.2 Loot Roll (Delayed Choice and Historical Consistency)

**(Loot Roll - Delayed Choice and Historical Consistency)**

> **"History is not a read-only file written on hard drive, but a log dynamically generated based on your current query request. The past didn't determine the present; it's when you check the loot table that the system retroactively generates the BOSS's drop history."**

In section 7.1, we said measurement is instantiation. This immediately raises a logical question: If you only now decide whether this cat is dead or alive, was it dead or alive in the past hour? Did we change the past?

This section will use **delayed choice experiments** to demonstrate **Code of Azeroth**'s most insane historical view: **History is generated based on queries**.
We will prove that the past is not objectively real, but a **log** made up on the spot by the system to match current plot.

### 7.2.1 The Illusion of Established History

Intuition tells us:
1.  The past has happened and is unique.
2.  Whether we look or not, the past won't change.

But **Wheeler's delayed choice experiment** shatters this illusion.
Imagine a photon flying from billions of light-years away. It faces two choices: go left, or go right.
*   If on Earth we decide to measure its path (particle nature), we force it to take a certain path billions of years ago.
*   If on Earth we decide to measure its interference (wave nature), we force it to take both paths simultaneously billions of years ago.

**Key point**: Our decision on Earth (now) determines the photon's behavior billions of years ago (past).

**Computational explanation**:
If the system stored every second of the photon's trajectory for billions of years, that wastes too much hard drive space.
In our model, the system **never stored** intermediate process trajectories.
*   **Intermediate state**: Photon propagates as **class** form, doesn't occupy coordinate memory.
*   **Final state**: Only when photon hits your detector on Earth does the system execute instantiation.

### 7.2.2 Dynamic Log Generation Algorithm

In computer science, this is called **lazy logging**.

**Definition 7.2.1 (Dynamic History)**

Physical object's historical trajectory $H(t)$ is not a static array, but a **function**.
$$ H(t) = \text{GenerateHistory}(\text{Now}, \text{Seed}) $$

This is like **procedural generation** in games.
Have you played those infinite map games? When you look back at the road behind, the game engine generates terrain behind based on current coordinate seed. As long as the generated road connects with the road under your feet, you can't tell if it "was always there" or "just generated."

Wheeler used a **"dragon"** metaphor:
*   **Dragon tail** (light source): Determined.
*   **Dragon head** (detector): Determined.
*   **Dragon body** (intermediate process): Is a cloud of **probability smoke**. The system never calculated how the dragon body flew; only when the dragon head bites does the system casually draw a line connecting them.

### 7.2.3 Quantum Erasure: Database Rollback

**Quantum erasure experiments** demonstrate the system's **editing permissions** on history.

We can first measure the photon's path, then **after** the photon reaches the screen, decide whether to **"erase"** this information.
*   If retain information: No interference (particle).
*   If erase information: Interference restored (wave).

This seems like time reversal physically, but computationally, this is standard **database transaction**.

1.  **Write-ahead log**: System records "path marker" in cache. At this point, history is in **Pending** state.
2.  **Rollback**: If we execute erasure, equivalent to sending `ABORT` command. System deletes cache marker, photon reverts to superposition state, re-renders interference fringes.
3.  **Commit**: If we read information, equivalent to sending `COMMIT` command. History is locked, forever written to read-only storage.

**Theorem 7.2.1 (History Mutability Theorem)**

Before information diffuses to the entire server, history is just **dirty data** in memory, can be rewritten anytime.

### 7.2.4 Why Can't We Resurrect Caesar?

Since history is generated, why can't we use "delayed choice" to make Caesar not die?
Because there's **consistency checking**.

Generated history must satisfy boundary conditions: **Logic must be self-consistent**.

*   **Macroscopic history (hard)**: Caesar's death has been `COMMIT`ed countless times by countless observers (people, air, photons). Its entanglement network locks the entire server. To rollback it requires entire server rollback, needs administrator privileges.
*   **Microscopic history (soft)**: Photons in labs only entangle with you. System can easily rewrite their history; no one knows anyway.

Therefore, **we have the divine power to change microscopic history, but are imprisoned by macroscopic history's inertia**.

### 7.2.5 Summary: History Generated for Plot

This section proved: **Causality is bidirectional at the computational level.**

*   **Physical layer (forward)**: Past determines future.
*   **Computational layer (reverse)**: Current observation **filters** and **instantiates** past that matches conditions.

We don't live on a one-way street. We live on an **instant-calculated stage**. The script (history) is generated in real-time to match the actors' (us) current performance.

The reason the past seems determined is because the system, to maintain logical self-consistency, perfectly fills all plot holes.
