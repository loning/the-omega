# 6.2 Textures vs Models (Complementarity Principle and Data Compression)

**(Textures vs Models - Complementarity Principle and Data Compression)**

> **"Waves and particles are not two properties of matter, but two formats of the same data. Like game files are compressed packages (waves) on hard drive, but decompressed files (particles) in running memory. The universe dynamically switches data formats based on whether you want to 'transmit' or 'interact'."**

In section 6.1, we discussed that Heisenberg's principle is resolution limitation. This leads to another big question: **Wave-particle duality**.

Why does light sometimes act like waves, sometimes like particles?
In **Code of Azeroth**, this is not mysterious; this is **dynamic data compression strategy**.

### 6.2.1 Format Conversion: Bitmap vs Vector Graphics

At the code level, waves and particles are just two **representations** of data.

1.  **Particle view (bitmap/entity)**:
    *   Information is **localized** (at this coordinate point).
    *   Suitable for **collision, pickup, combat**.
    *   This is the BOSS you see in instances that can be fought.

2.  **Wave view (spectrum/compressed package)**:
    *   Information is **dispersed** (everywhere).
    *   Suitable for **propagation, loading, cutscenes**.
    *   This is the BOSS data packet in "may appear" state.

**Mathematical essence**:
Converting from particle to wave is doing a **format conversion (ZIP compression)**.
The so-called complementarity principle means you cannot keep a file simultaneously in "compressed" and "decompressed" states.

### 6.2.2 Compress When Transmitting, Decompress When Interacting

Why does the universe bother with these two formats? To **save bandwidth**.

**Scenario one: Running across map (free propagation)**
*   **Task**: A fireball flies from your hand to the monster's face.
*   **Particle mode (dumb method)**: If using particle mode, the server must calculate its position at every pixel every frame to prevent clipping. This is exhausting.
*   **Wave mode (smart method)**: If using wave mode, it's just a mathematical formula (phase rotation). Extremely simple to calculate.
*   **Conclusion**: **Wave is the most efficient transmission format**. As long as nothing hits, the system defaults to packing all flying things as waves (compressed packages), greatly reducing computation.

**Scenario two: Hit (local interaction)**
*   **Task**: Fireball hits the face.
*   **Wave mode (dumb method)**: Waves are spread out; can't calculate specific damage judgment point.
*   **Particle mode (smart method)**: System needs to know precise coordinates $(\text{x}, \text{y}, \text{z})$ to deduct health.
*   **Conclusion**: **Particle is the most efficient interaction format**. When collision occurs, the system must **decompress** the wave back to particle, execute collision detection. This is physics' **"collapse"**.

### 6.2.3 Observer's Choice: Double-Slit Experiment

When you do the double-slit interference experiment, you're actually configuring a **decoder** as a player.

*   **No detector**: You tell the server: "I don't care which path it takes." Server thinks: "Great, saves trouble." So it maintains **wave encoding** (compressed package mode), passes through double slits, draws interference fringes on screen.
*   **Place detector**: You tell the server: "I want to see its precise path." Server is forced to execute `Unzip()`, decompress data back to **particle encoding**. After becoming particle, it can only pass through one slit; interference fringes disappear.

**Theorem 6.2.1 (What You See Is What You Ask For)**

Reality appears as what (wave or particle) depends on what format you ask the system for.
$$ \text{reality} = \text{data} + \text{your request} $$

### 6.2.4 Delayed Choice: Render on Demand

Wheeler's **delayed choice experiment** proved that even if photons have already flown over, as long as you haven't looked at the result, you can still change its past.

This is too normal from a code perspective: This is **lazy evaluation**.

*   Photons remain **compressed packages** during flight.
*   **Log** hasn't been generated yet.
*   Only at the last moment when you decide how to look at it does the system **generate on-the-fly** its historical trajectory based on your decision.

This is like **frustum culling** in games: Graphics cards always only render the instant you're looking at.

### 6.2.5 Summary: The Coding of Reality

The complementarity principle reveals a core optimization technique of the universe operating system: **dynamic transcoding**.

1.  **Vacuum is frequency domain**: To save bandwidth, empty places are all waves.
2.  **Matter is time domain**: To calculate collisions, populated places are all particles.
3.  **Observation is decoding**: Your eyes determine the data decompression method.

The wave-particle debate physicists argued for a hundred years actually confused **source files** with **display formats**. The universe has only one thing—quantum information flow—which switches between compression and decompression as needed.
