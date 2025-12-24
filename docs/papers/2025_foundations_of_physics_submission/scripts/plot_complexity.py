
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 6))

# Parameters
t = np.linspace(0, 10, 500)
entropy = 1 - np.exp(-0.5 * t) # Saturates to Heat Death
complexity = t * np.exp(-0.2 * t * (t - 8)) # Scales up, simulating open ended evolution (simplified model)
complexity = 0.1 * t**2 # Let's use simple power law growth for "Anti-Heat Death"

# Refine models
# Heat Death (Standard)
s_standard = 1 - np.exp(-0.3 * t)
# Omega Evolution (Logical Depth)
k_omega = 0.05 * np.exp(0.4 * t)

# Plot
ax.plot(t, s_standard, color='gray', linestyle='--', linewidth=2, label='Standard Entropy (Heat Death)')
ax.plot(t, k_omega, color='purple', linewidth=3, label='Logical Depth (Complexity)')

# Annotations
ax.text(8, 0.95, 'Thermal Equilibrium', color='gray', fontsize=10, ha='center')
ax.arrow(8, 2, 0, 1, color='purple', head_width=0.2, head_length=0.2)
ax.text(8, 3.2, 'Open-Ended Evolution', color='purple', fontsize=12, ha='center', fontweight='bold')

# Labels
ax.set_xlabel(r'Cosmic Time $\tau$', fontsize=14, color='black')
ax.set_ylabel(r'Measure Value', fontsize=14, color='black')
ax.set_title('Entropy vs. Complexity', fontsize=18, color='black')

# Legend
ax.legend(fontsize=12, facecolor='white', edgecolor='black')

# Stylizing ticks
ax.tick_params(colors='black')
for spine in ax.spines.values():
    spine.set_color('black')

# Save
output_path = "../images/complexity_growth.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
