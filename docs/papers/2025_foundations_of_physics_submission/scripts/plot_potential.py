
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 6))

# Parameters
x = np.linspace(-2.5, 2.5, 400)
mu_sq = 2.0
lam = 1.0
potential = -0.5 * mu_sq * x**2 + 0.25 * lam * x**4

# Plot
ax.plot(x, potential, color='navy', linewidth=3, label=r'$V_{eff}(\Phi)$')

# Annotations for Vacuum States
vev = np.sqrt(mu_sq / lam)
ax.plot([vev], [potential.min()], 'o', color='darkorange', markersize=12, label='Vacuum State')
ax.plot([-vev], [potential.min()], 'o', color='darkorange', markersize=12)

# Grid and Lines
ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
ax.axvline(0, color='gray', linestyle='--', alpha=0.5)

# Labels
ax.set_xlabel(r'Geometric Field $\Phi$ (Volume deformation)', fontsize=14, color='black')
ax.set_ylabel(r'Effective Potential $V_{eff}(\Phi)$', fontsize=14, color='black')
ax.set_title('Geometric Symmetry Breaking', fontsize=18, color='black')

# Legend
ax.legend(fontsize=12, facecolor='white', edgecolor='black')

# Stylizing ticks
ax.tick_params(colors='black')
for spine in ax.spines.values():
    spine.set_color('black')

# Save
output_path = "../images/geometric_potential.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
