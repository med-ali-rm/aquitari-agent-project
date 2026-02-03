# visualize_kg.py
import json
import os
import networkx as nx
import matplotlib.pyplot as plt

# -------- CONFIG --------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KG_FILE = os.path.join(BASE_DIR, "brain_graph.json")  # knowledge graph JSON

# -------- LOAD KNOWLEDGE GRAPH --------
with open(KG_FILE, "r", encoding="utf-8") as f:
    kg = json.load(f)

# -------- CREATE GRAPH --------
G = nx.DiGraph()

# Add nodes
for node in kg.get("nodes", []):
    G.add_node(node["id"], type=node.get("type", ""))

# Add edges
for edge in kg.get("edges", []):
    G.add_edge(
        edge["source"],
        edge["target"],
        relation=edge.get("relation", "")
    )

# -------- DRAW GRAPH --------
plt.figure(figsize=(12, 8))

# Layout
pos = nx.spring_layout(G, seed=42)

# Color nodes by type
color_map = []
for _, data in G.nodes(data=True):
    node_type = data.get("type", "")
    if node_type == "system_state":
        color_map.append("orange")
    elif node_type == "physiological_marker":
        color_map.append("lightcoral")
    elif node_type == "cognitive_condition":
        color_map.append("gold")
    elif node_type == "behavioral_risk":
        color_map.append("red")
    elif node_type == "protection_state":
        color_map.append("lightgreen")
    elif node_type == "system_metric":
        color_map.append("skyblue")
    else:
        color_map.append("gray")

# Draw nodes
nx.draw_networkx_nodes(
    G,
    pos,
    node_color=color_map,
    node_size=1400,
    alpha=0.9
)

# Draw edges
nx.draw_networkx_edges(
    G,
    pos,
    arrowstyle="->",
    arrowsize=20,
    edge_color="black",
    width=2
)

# Node labels
nx.draw_networkx_labels(
    G,
    pos,
    font_size=10,
    font_weight="bold"
)

# Edge labels
edge_labels = nx.get_edge_attributes(G, "relation")
nx.draw_networkx_edge_labels(
    G,
    pos,
    edge_labels=edge_labels,
    font_color="darkred",
    font_size=9
)

plt.title("Knowledge Graph Visualization", fontsize=14)
plt.axis("off")
plt.tight_layout()

# -------- SAVE & SHOW --------
output_path = os.path.join(BASE_DIR, "knowledge_graph.png")
plt.savefig(output_path, dpi=300)
plt.show()

print(f"Graph saved to: {output_path}")
