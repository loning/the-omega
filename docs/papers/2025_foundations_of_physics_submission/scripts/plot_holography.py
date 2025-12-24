
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 6))

# Parameters
r = np.linspace(0.1, 10, 500)

# Scaling laws
volume_info = r**3 # Standard QFT intuition (Extensive)
area_info = 5 * r**2 # Holographic Bound (Bekenstein) - scaled for visibility intersection

# Plot
ax.plot(r, volume_info, color='gray', linestyle='--', linewidth=2, label=r'Volume Law ($\sim R^3$)')
ax.plot(r, area_info, color='darkcyan', linewidth=3, label=r'Holographic Bound ($\sim R^2$)')

# Fill the "Forbidden Region"
ax.fill_between(r, area_info, volume_info, where=(volume_info > area_info), color='darkred', alpha=0.2, label='Forbidden (Black Hole Formation)')

# Annotations
ax.text(8, 200, 'Black Hole\nCollapse', color='darkred', fontsize=12, ha='center', fontweight='bold', rotation=45)
ax.text(2, 5, 'Allowed\nStates', color='darkcyan', fontsize=12, ha='center')

# Labels
ax.set_xlabel(r'Region Size $R$ (Planck units)', fontsize=14, color='black')
ax.set_ylabel(r'Max Information $S_{max}$', fontsize=14, color='black')
ax.set_title('The Holographic Bound', fontsize=18, color='black')
ax.set_xlim(0, 10)
ax.set_ylim(0, 600)

# Legend
ax.legend(fontsize=12, facecolor='white', edgecolor='black')

# Stylizing ticks
ax.tick_params(colors='black')
for spine in ax.spines.values():
    spine.set_color('black')

# Save
output_path = "../images/holographic_scaling.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
