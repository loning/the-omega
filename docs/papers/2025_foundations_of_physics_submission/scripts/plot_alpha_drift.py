
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('default')
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='mollweide')

# Generate data grid
ra = np.linspace(-np.pi, np.pi, 200)
dec = np.linspace(-np.pi/2, np.pi/2, 100)
RA, DEC = np.meshgrid(ra, dec)

# Dipole direction (arbitrary for visualization, near Webb's detection)
ra_dipole = 4.5 * np.pi / 4 # ~ Right Ascension ~ 20h
dec_dipole = -0.5 # ~ Declination ~ -30 deg

# Calculate Angle Theta relative to Dipole
# cos(Theta) = sin(d1)sin(d2) + cos(d1)cos(d2)cos(ra1-ra2)
cos_theta = np.sin(DEC) * np.sin(dec_dipole) + np.cos(DEC) * np.cos(dec_dipole) * np.cos(RA - ra_dipole)

# Variation Amplitude
delta_alpha = 1e-5 * cos_theta

# Plot Heatmap
mesh = ax.pcolormesh(RA, DEC, delta_alpha, cmap='RdBu_r', shading='auto')

# Colorbar
cbar = plt.colorbar(mesh, ax=ax, orientation='vertical', shrink=0.7, pad=0.05)
cbar.set_label(r'$\Delta \alpha / \alpha$', color='black', fontsize=14)
cbar.ax.yaxis.set_tick_params(color='black', labelcolor='black')

# Dipole Marker
ax.scatter([ra_dipole], [dec_dipole], color='gold', s=100, marker='*', label='Max Variation', edgecolors='black')
ax.scatter([ra_dipole - np.pi], [-dec_dipole], color='cyan', s=100, marker='*', label='Min Variation', edgecolors='black')

# Grid
ax.grid(color='gray', linestyle='--', alpha=0.5)

# Title
ax.set_title(r'Spatial Variation of $\alpha$ (Dipole)', color='black', fontsize=18, pad=20)

# Stylizing
ax.tick_params(colors='gray') # Lat/Lon labels are tricky in Mollweide, keep subtle

# Save
output_path = "../images/alpha_drift.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
