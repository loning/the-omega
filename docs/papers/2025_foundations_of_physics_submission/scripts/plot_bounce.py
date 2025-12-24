
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 6))

# Parameters
t = np.linspace(-3, 3, 500)
rho_crit = 1.0
ho = 1.0

# Scale factor for Big Bounce (simplified analytic form for LQC)
# a(t) = (3/4 * rho_crit * t^2 + 1)^(1/3) roughly
# A more standard LQC bounce is a(t) = (1 + rho_crit * t^2)^(1/3)
# Let's use the explicit hyper-cosh form often found in bounce models
a = (np.cosh(t)) ** (1/3)

# Plot
ax.plot(t, a, color='navy', linewidth=3, label=r'$a(t)$ Scale Factor')

# Dashed lines for Big Bang scenario (t=0 singularity)
t_bb = np.linspace(0.1, 3, 250)
a_bb = t_bb ** (2/3) # Radiation dominated
ax.plot(t_bb, a_bb, color='gray', linestyle='--', linewidth=2, label='Standard Big Bang')
ax.plot(-t_bb, a_bb, color='gray', linestyle='--', linewidth=2)

# Annotations
ax.text(0, 1.05, 'The Big Bounce', color='darkorange', fontsize=12, ha='center', va='bottom', fontweight='bold')
ax.plot([0], [1], 'o', color='darkorange', markersize=10)

# Labels
ax.set_xlabel(r'Cosmic Time $t$ (Planck units)', fontsize=14, color='black')
ax.set_ylabel(r'Scale Factor $a(t)$', fontsize=14, color='black')
ax.set_title('Resolving the Singularity', fontsize=18, color='black')

# Legend
ax.legend(fontsize=12, facecolor='white', edgecolor='black')

# Stylizing ticks
ax.tick_params(colors='black')
for spine in ax.spines.values():
    spine.set_color('black')

# Save
output_path = "../images/bounce.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
