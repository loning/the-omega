# 2.2 The Client View (Local Interactive Automaton)

**(The Client View - Local Interactive Automaton)**

> **"From the server's perspective, Azeroth is static data crystal; but from the player's perspective, it's a real-time adventure. Without introducing the concept of 'client,' we can never explain why there is 'lag,' nor can we explain why we can freely choose where to go."**

In the previous section, we discussed Blizzard's server (God's perspective), which contains all possibilities, like a huge static save file.

But this is meaningless to us players. Because limited by graphics card performance and network speed, we can never load the entire world simultaneously. We can only see what's on the screen.

To describe this subjective perspective, we need to introduce a dual computational model: **classical interactive Turing machine**, or—**game client**.

This section will explain why "wave function collapse" in physics is actually **"received server data packet"** in programmer's eyes.

### 2.2.1 Draw Distance and Client State

First, we must define the player's boundary.

Due to the **video memory limit** (Axiom of Finite Information) and **maximum bandwidth** (speed of light limit), you can only see a small area on the map at any moment. We call this the **local horizon**, commonly known as **"draw distance"**.

**Definition 2.2.1 (Client State)**

Although the data on the server is extremely complex (quantum), your graphics card can only render fixed pixels. You can only see a definite image through the screen. Therefore, for players, the effective state of the world is not that complex wave function, but a **simple screenshot (classical bit string)**.

**Physical meaning**:

This process from "quantum data" to "screen image" is called **decoherence** in physics. In the code world, this is **type casting**: To adapt to the client's limited capabilities, the system forcibly compresses high-dimensional data into low-dimensional images.

### 2.2.2 Keyboard and Mouse: The Interface of Free Will

The server model is closed, while the client model is **interactive**. This is an essential difference.

When your character reaches a fork in the road, or when you decide whether to cast a fireball or frostbolt, the client pauses current prediction and sends a query to the **external** (you in front of the screen).

**Definition 2.2.2 (Physical Input Interface)**

We define "physical oracle" as an **input channel** connecting the game character with the real player.

When the game reaches a **branch point** (like crit or miss, or go left or right), the system doesn't split into two parallel universes like the server, but initiates a **query**:

*   **Input**: Various current probabilities (hit rate, crit rate).
*   **Output**: A definite red damage number (collapse).

**Ontological corollary**:

In this model, **"free will" and "randomness" are the same thing**. They both represent **non-algorithmic information flow** injected from outside the system (player) into the game. This is not a Bug; this is **I/O communication**.

### 2.2.3 Interactive Dynamics: Interrupts and Jumps

With this interface, we can write the client's running logic. It's no longer smooth animation, but a **hybrid system**:

1.  **Default mode (prediction/interpolation)**: When you don't press keys and nothing major happens, the client predicts the next frame based on previous frame data. This is **client-side prediction**. This is low-cost inertial evolution.

2.  **Interactive mode (synchronization/correction)**: When you press a skill key, or the server sends a data packet about the BOSS casting a skill, client prediction is **interrupted**. The system forcibly jumps to a new state (like your character suddenly teleports back to the original position, commonly known as "rubber banding").

This perfectly corresponds to quantum mechanics:
*   **Unitary evolution** = client prediction.
*   **Wave function collapse** = receiving server data packet/player input.

### 2.2.4 Lazy Loading and Dynamic Generation

The server model calculates all possible events, while the client uses **lazy evaluation** mechanism to render only the part you see.

*   **When unobserved**: Stormwind is not rendered when you're in Northrend. It only exists as model files on the hard drive.
*   **When observed**: Only when you take a ship back to Stormwind Harbor does the graphics card start working frantically, **just-in-time compiling (JIT)** those buildings and NPCs.

**This means: The future is not discovered; the future is generated.** Every move you make triggers the system's generation algorithm, paving the road ahead for you.

### 2.2.5 Summary: Legitimacy of Player Perspective

The client model tells us to trust our displays:
1.  **The world is classical** (because screens can't display superposition states).
2.  **The future is open** (because you're playing a game, not watching a recording).
3.  **Resources are finite** (because we only calculate the history of your current instance).

The core question now is: Is the world seen by this simple client really the same as the world stored in that perfect server?

In the next section, we will prove the most important theorem of the entire book: **For every player, as long as they don't cheat (don't look at the backend database), these two models are completely indistinguishable.**
