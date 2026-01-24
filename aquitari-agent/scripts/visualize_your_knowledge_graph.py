"""
visualize_kg.py
----------------
This script loads a knowledge graph from JSON (located in brain-api/data),
builds a directed graph using NetworkX, and visualizes it with Matplotlib.

Features:
- Reads nodes and edges from brain_graph.json
- Colors nodes based on their type (system_state, physiological_marker, etc.)
- Draws edges with labels showing relations
- Saves the visualization as knowledge_graph.png in the data folder
- Displays the graph interactively

Usage:
Run the script directly. Ensure brain_graph.json exists in brain-api/data.
"""

import json
import os
import networkx as nx
import matplotlib.pyplot as plt

# -------- CONFIG --------
# Define the base directory for data files (portable, no static C:/ path)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

KG_FILE = os.path.join(DATA_DIR, "brain_graph.json")  # knowledge graph JSON

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
output_path = os.path.join(DATA_DIR, "knowledge_graph.png")
plt.savefig(output_path, dpi=300)
plt.show()

print(f"Graph saved to: {output_path}")