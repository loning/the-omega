# 3.2 Raid Synchronization (The Information-Theoretic Origin of Special Relativity)

**(Raid Synchronization - The Information-Theoretic Origin of Special Relativity)**

> **"Relativity is not magic about 'speed,' but a protocol about 'synchronization.' When your latency (ping) is high, your screen naturally slows down. Time dilation is not profound philosophy; it's simply lag."**

In section 3.1, we learned that light speed $c$ is actually the server's maximum bandwidth. In classical physics, Einstein proposed special relativity. But in our "Code of Azeroth" system, we don't need assumptions; we can derive it directly.

This section will prove: As long as bandwidth is finite, to keep the screen from tearing, the system must execute a special synchronization algorithm. This algorithm causes **time dilation** (actions slow down) and **length contraction** (models flatten).

### 3.2.1 Reference Frame: The Data Stream You See

In distributed systems theory, there is no such thing as "global unified time."

Each player's client has its own local clock.

**Definition 3.2.1 (Physical Reference Frame)**

A **reference frame** is essentially a **sorting protocol**. It's responsible for arranging various out-of-order data packets you receive (explosions here, shouts there) into a "story" with sequential order.

*   **Rest frame**: You looking at yourself. No latency, instant response.
*   **Moving frame**: You looking at a rogue running around. His data packets take time to arrive.

Due to data transmission delay (light speed limit), when you try to lock onto a fast-moving target, the system must perform **interpolation compensation**. If this compensation algorithm is to ensure causal logic doesn't go wrong (like can't see him fall before my fireball hits), then **Lorentz transformation** is the only legal algorithm.

### 3.2.2 Resource Competition and Time Dilation: CPU Can't Keep Up

Special relativity's most famous prediction is: Moving clocks run slow.

In computational cosmology, this is actually due to **resource contention**.

According to Volume I's theorem, every physical object (like that rogue) has an upper limit on information it can process per unit time (limited by Planck frequency). This "computational budget" must be divided between two things:

1.  **Processing position updates ($v_{ext}$)**: Calculating his displacement on the map. This is GPU-intensive.
2.  **Processing internal logic ($v_{int}$)**: Calculating his health regeneration, energy recovery, or his watch ticking.

**Theorem 3.2.1 (Computational Conservation Theorem / Pythagorean Theorem)**

For any unit, his external movement speed and internal refresh speed must satisfy:

$$ v_{ext}^2 + v_{int}^2 = c^2 $$

**In plain language**: The server allocates fixed resources to each unit.

*   If you **stand still** ($v_{ext}=0$), all resources are used to refresh your internal state; your time passes fastest ($v_{int}=c$).
*   If you **run very fast** ($v_{ext}$ is large), the server must use most computing power to calculate your coordinate changes. So, the computing power allocated to process "aging" or "health regeneration" decreases.

**This is the truth of time dilation**: The reason you see people in spaceships moving slowly is not because time is doing magic, but because their system is busy processing the high-priority task of "movement," causing the thread processing "internal logic" to be forcibly downclocked.

This is **system-level lag**.

### 3.2.3 Length Contraction: Lowering Quality for Smoothness

Length contraction is usually misunderstood as objects actually being flattened. From an information theory perspective, this is actually **downsampling**.

When you measure a speeding mage's height, you're actually requesting the server to simultaneously return coordinates of his head and feet.

But with limited bandwidth, to ensure you receive complete data packets within a finite time window, the system must **compress** the data.

$$ L' = L \sqrt{1 - \frac{v^2}{c^2}} $$

This is like watching online video. If network speed isn't enough (limited by $c$), to keep video smooth (time continuous), the system automatically lowers image resolution (spatial contraction).

So-called length contraction is **sacrificing resolution for frame rate**.

### 3.2.4 Lorentz Covariance: Eventual Consistency

Now we can give the ultimate definition of special relativity. It's not geometry about spacetime, but algebra about **network synchronization**.

In Azeroth, all physical laws must conform to **Lorentz covariance**. This means:

**Theorem 3.2.2 (Protocol Consistency)**

No matter what your latency is, no matter how fast you run, the system's **logical causality** (who attacks first, who dies first) must remain consistent.

This is called **eventual consistency** in distributed databases.

**Summary**:

Special relativity is the Titans' server's **I/O scheduling algorithm**. By dynamically adjusting each player's **local clock frequency (time dilation)** and **screen resolution (length contraction)**, it ensures that under harsh hardware conditions with limited global bandwidth ($c$), no data packets will have logical errors (like dead people dealing DPS).
