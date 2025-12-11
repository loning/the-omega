
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 10))
ax.set_aspect('equal')
ax.axis('off')

# Parameters
N = 1000
golden_angle = np.pi * (3 - np.sqrt(5))

# Generate points
n = np.arange(1, N + 1)
r = np.sqrt(n)
theta = n * golden_angle

# Coordinates
x = r * np.cos(theta)
y = r * np.sin(theta)

# Color and Size
colors = theta  # Color by angle
sizes = 50 * (1 - n / (N + 100)) + 5 # Smaller as they go out

# Plot
scatter = ax.scatter(x, y, c=colors, s=sizes, cmap='viridis', alpha=0.8, edgecolors='none')

# Annotations (optional - minimalist is better)
# ax.set_title("The Omega Network Projection", color='black', fontsize=20)

# Save
output_path = "../images/golden_spiral.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.1, transparent=False)
print(f"Saved to {output_path}")
