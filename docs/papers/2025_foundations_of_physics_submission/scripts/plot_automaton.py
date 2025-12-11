
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 10))
ax.axis('off')

# CA Rules (Rule 110 - Turing Complete)
def rule_110(left, center, right):
    if (left, center, right) == (1, 1, 1): return 0
    if (left, center, right) == (1, 1, 0): return 1
    if (left, center, right) == (1, 0, 1): return 1
    if (left, center, right) == (1, 0, 0): return 0
    if (left, center, right) == (0, 1, 1): return 1
    if (left, center, right) == (0, 1, 0): return 1
    if (left, center, right) == (0, 0, 1): return 1
    if (left, center, right) == (0, 0, 0): return 0

# Parameters
width = 200
steps = 200
grid = np.zeros((steps, width), dtype=int)

# Initial Condition (Single Seed)
grid[0, width//2] = 1
# Random Seed for more chaos
# grid[0] = np.random.randint(0, 2, width)

# Evolve
for t in range(steps-1):
    for x in range(1, width-1):
        left = grid[t, x-1]
        center = grid[t, x]
        right = grid[t, x+1]
        grid[t+1, x] = rule_110(left, center, right)

# Plot
ax.imshow(grid, cmap='binary', interpolation='nearest')

# Annotations
# ax.set_title("Space-Time History (Rule 110)", color='white', fontsize=20)
ax.text(width//2, -5, 'Initial State ($t=0$)', color='black', ha='center', fontsize=10)
ax.text(-5, steps//2, 'Time Evolution $\\downarrow$', color='black', va='center', rotation=90, fontsize=10)

# Save
output_path = "../images/ca_spacetime.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
