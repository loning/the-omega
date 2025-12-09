# 2.1 The Global Server State (Global Unitary Model)

**(The Global Server State - Global Unitary Model)**

> **"In the server's database, there is no 'if.' You got this item not only because you rolled 100, but because in some version snapshot of the database, that data was already written. The real puzzle is not why you rolled 100, but why you cannot see the other 99 parallel universes of yourself."**

This chapter will expound the core of the "Code of Azeroth" theory—**the Holographic Equivalence Principle**. To prove this, we need to understand two endpoints: one is the world as seen by Blizzard's server (God's perspective/global model), and the other is the world as seen by players (local perspective/client model).

In this section, we first discuss God's perspective: **Global Server State**.

### 2.1.1 The Global Database

According to the **video memory limit** (Axiom of Finite Information) we set in Chapter 1, the universe's data volume is finite.

Imagine Blizzard headquarters' core database. It can be seen as composed of countless basic data units (quantum bits). These data units record the position of every murloc, every herb spawn point, every player's bag data.

At any moment, the entire state of Azeroth can be described by a **global quantum state** $|\Psi(t)\rangle$ connected through **huge hyperlinks**. This state vector contains everything in the universe.

From this perspective, the universe is **complete**. It shows all possible historical branches. Like in developer debug mode, you can simultaneously see:
1. Branch A: You wiped in that raid.
2. Branch B: You got the world first.
3. Branch C: You didn't log in at all.

All of this exists simultaneously as **superposition states** in the server's underlying logic.

### 2.1.2 Eternal Maintenance: The Global Update Script $\hat{U}$

In this model, the universe is a closed server that doesn't interact with any other game. Its evolution strictly follows a hardcoded script, which we call the **global unitary operator** $\hat{U}$.

This is like the weekly Thursday maintenance script. Each jump of the universe's state with time $t$ is the result of running this script once:

$$ |\Psi(t+1)\rangle = \hat{U} |\Psi(t)\rangle $$

This script must satisfy **data conservation** (unitarity). This means:

**Physical Corollary: No Data Loss**

At the server level, **data is never created or destroyed**. You think you destroyed an item, but in the database log, that operation record exists forever. If you have administrator privileges ($\hat{U}^\dagger$), you can always recover the equipment by rolling back the log.

In the eyes of an omniscient administrator, the universe never becomes more chaotic (entropy increase), because he masters all information.

### 2.1.3 Block Universe: Static Save File

If we connect all database snapshots at all times, we find this model is actually a **"Block Universe"**.

This is like a **complete backup file** containing all data from the first day the server opened to the day it closes.

In this picture:

1.  **Multiple histories coexist**: All histories that conform to game rules (like Alliance winning or Horde winning) are recorded at the data bottom layer.
2.  **No collapse**: Because the server itself doesn't observe; it only computes. From the server's perspective, all possibilities are equal. Schrödinger's cat is marked as both `State: Dead` and `State: Alive` in the database; they are parallel data streams.
3.  **Static spacetime**: Time is just an index field in the database. The entire history is like a burned disc, already written long ago.

### 2.1.4 Why No "I'm Playing a Game" Feeling?

Although this God model is mathematically perfect, it has a big problem: **It has no concept of 'now.'**

In the database, data from 2005 and 2025 are stored side by side. No line of code marks: "Because we're reading this line, it's now 2025."

This leads to the core question of this book:
**Why do we, as players, feel not seeing all endings simultaneously, but a unidirectional, unknown timeline?**

To answer this question, we need to introduce another perspective—**your client** (local interactive automaton), which will be detailed in the next section.
