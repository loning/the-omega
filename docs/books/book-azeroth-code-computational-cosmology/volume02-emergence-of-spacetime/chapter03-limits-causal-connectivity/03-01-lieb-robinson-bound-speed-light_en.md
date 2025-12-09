# 3.1 Max Transfer Rate (Lieb-Robinson Bound and the Speed of Light)

**(Max Transfer Rate - Lieb-Robinson Bound and the Speed of Light)**

> **"The speed of light is not about how fast light travels, but about the server's maximum data transmission bandwidth limit. You think spacetime is an empty box, but actually it's a local area network woven from countless network cables."**

In Volume I, we established the "world as code" axiomatic system. Now, we need to make this code run.

For this abstract system to become the physical world we see with length, width, and height, the system must have a **topological structure**.

The core constraint of this structure is **locality**. Simply put, **you can only attack monsters within your attack range**.

This section will prove that as long as the server follows this rule, information propagation must have a maximum speed limit. In physics, this is called the **speed of light (c)**. In our theory, this is **global maximum bandwidth**.

### 3.1.1 Interaction Graph: Who Are Your Neighbors?

In classical physics, distance is innate. But in computational cosmology, distance comes later.

We first define the system's **interaction graph**:
*   **Nodes**: Each independent quantum bit, or each smallest spatial pixel.
*   **Edges**: Who can directly exchange data with whom.

If physical laws are **local** (to prevent server overload, cannot allow full connection between all pixels), then interactions can only occur between adjacent pixels.

This means information cannot teleport. It must be transmitted step by step, like running across the map.

### 3.1.2 Lieb-Robinson Bound: Physical Limit of Ping

In 1972, two physicists Lieb and Robinson proved a theorem. Translated into World of Warcraft language:

**Theorem 3.1.1 (Lieb-Robinson Bound / Maximum Ping Theorem)**

In a grid system, as long as each cell only interacts with adjacent cells, the influence range of any event has an **upper limit on diffusion speed**.

**Physical meaning**:

Outside the **light cone** defined by slope $v_{LR}$, that is, places this speed cannot catch up, no event can affect you.

This is like shouting in the Eastern Kingdoms; people in Kalimdor absolutely cannot hear. Although mathematically there may be extremely weak probability (due to continuous evolution tails), at physical measurement precision, this constitutes an **effective causal horizon**.

### 3.1.3 The True Face of Light Speed: System Bus Bandwidth

If we adopt a more fundamental **cellular automaton** model, time is discrete (Server Tick). In this case, the limit becomes absolutely strict.

Each time the system ticks, data can only be transmitted from one cell to an adjacent cell.

From this, we derive **the true definition of light speed c**:

$$ c \equiv \frac{\text{minimum pixel side length}}{\text{minimum server refresh period}} = \frac{l_P}{t_P} $$

In this framework, light speed invariance is no longer a strange assumption, but a direct manifestation of **system bus bandwidth**.

*   **Bus frequency**: The server's refresh rate is locked (Planck time).
*   **Bus bit width**: Each cycle, data can only be moved this far.

Therefore, any attempt to exceed light speed is computationally equivalent to **trying to transmit data to an address outside the bus architecture in one cycle**. This will be directly intercepted by underlying hardware logic, and the chat box will show: **"Target not in view"** or **"Too far away"**.

### 3.1.4 Preventing Server Avalanche

Special relativity is usually thought to limit our exploration of the universe, but in computational cosmology, this is actually to **protect the server**.

If **teleportation** (superluminal/infinite propagation speed) were allowed, then any tiny disturbance in the network (like you sneezing in Stormwind) would instantly spread throughout the universe. This means every pixel must simultaneously process information from the entire universe.

This would cause computational complexity to explode from $O(N)$ to $O(N^2)$ or even exponential. The server would instantly **avalanche**, directly blue screen crash.

**Corollary 3.1.1 (Instance Partitioning)**

The existence of light speed divides the universe into countless relatively independent **causal diamonds**, like diverting players to different **planes or channels**.

This allows the system to process local tasks in parallel without waiting for global synchronization. Relativity is not just about motion; it's the **partition tolerance protocol** that this supercomputer universe must follow to achieve **large-scale parallel computation**.

Therefore, we should thank the light speed limit. It's precisely because of it that lag in Stormwind doesn't affect Orgrimmar.
