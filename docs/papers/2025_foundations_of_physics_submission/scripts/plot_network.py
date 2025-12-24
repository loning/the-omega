
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# Set style
plt.style.use('default')
fig, ax = plt.subplots(figsize=(10, 10))
ax.axis('off')

# Create a graph
G = nx.watts_strogatz_graph(n=200, k=4, p=0.1)

# Position nodes using spring layout for organic look
pos = nx.spring_layout(G, seed=42)

# Visualization
# Nodes: Color by degree or centrality
centrality = nx.betweenness_centrality(G)
node_colors = [centrality[node] for node in G.nodes()]
node_sizes = [v * 1000 + 10 for v in node_colors]

# Edges: Thin alpha lines
nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.3, edge_color='darkblue')
nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors, cmap='plasma', alpha=0.9, linewidths=0.5, edgecolors='black')

# Highlights (Hubs)
# Maybe highlight the most central nodes as "Information Hubs"

# Title (Clean)
# ax.set_title("The Discrete Omega Network", color='black', fontsize=20)

# Save
output_path = "../images/omega_network.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
print(f"Saved to {output_path}")
