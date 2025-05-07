import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib import cm, colors as mcolors
from pyvis.network import Network
import logging
import math
import re

def visualize_graph(result, config):
    """
    Generate PNG and HTML visualization of the knowledge graph.
    Requires config["ENABLE_GRAPH_VISUALIZATION"] True and config["RELATION_EXTRACTION"] True.
    """
    if not config.get("ENABLE_GRAPH_VISUALIZATION", False):
        return
    if not config.get("RELATION_EXTRACTION", False):
        logging.warning("Graph visualization requires RELATION_EXTRACTION=True, skipping.")
        return

    # Prepare output filenames and log status
    png_filename = "knowledge_graph.png"
    html_filename = "knowledge_graph_interactive.html"
    logging.info(f"Graph visualization enabled - PNG: {png_filename}, HTML: {html_filename}")

    entities = result.get("entities", [])
    relationships = result.get("relationships", [])

    # If no relationships, abort visualization to avoid errors
    if not relationships:
        logging.error("Graph visualization aborted: no relationships available.")
        return

    # Build MultiDiGraph
    G = nx.MultiDiGraph()
    for rel in relationships:
        inferred = rel.get("inferred", "")
        subj = rel.get("subject")
        obj = rel.get("object")
        pred = rel.get("predicate")
        style = "solid" if inferred == "explicit" else "dashed"
        if subj:
            G.add_node(subj)
        if obj:
            G.add_node(obj)
        if subj and obj and pred:
            G.add_edge(subj, obj, label=pred, style=style)

    # Determine colors by entity type
    base_colors = {
        "person": "#ffe6e6",
        "organisation": "#e6f0ff",
        "location": "#e7ffe6",
        "event": "#fff6e6",
        "concept": "#f0e6ff",
        "work": "#ffe6cc"
    }

    def get_entity_type(node):
        for rel in relationships:
            if rel.get("subject") == node and rel.get("subject_type"):
                return rel.get("subject_type").lower()
            if rel.get("object") == node and rel.get("object_type"):
                return rel.get("object_type").lower()
        for ent in entities:
            name = ent.get("entity") or ent.get("name")
            if name == node and ent.get("entity_type"):
                return ent.get("entity_type").lower()
        return ""

    # Build list of unique types in order encountered
    unique_types = []
    for node in G.nodes():
        etype = get_entity_type(node)
        if etype not in unique_types:
            unique_types.append(etype)
    # Build mapping: base colors first
    type_color_map = {}
    for etype in unique_types:
        if etype in base_colors:
            type_color_map[etype] = base_colors[etype]
    # Other types via dynamic tab20 colormap
    other_types = [t for t in unique_types if t not in type_color_map]
    cmap = cm.get_cmap('tab20', len(other_types) or 1)
    for idx, etype in enumerate(other_types):
        type_color_map[etype] = mcolors.to_hex(cmap(idx))
    # Assign each node its fill color
    type_fill_colors = {node: type_color_map.get(get_entity_type(node), '#f2f2f2') for node in G.nodes()}

    # -- PNG Visualization --
    # Determine layout method and parameters
    layout_method = config.get("GRAPH_LAYOUT_METHOD", "kamada_kawai")
    layout_k = config.get("GRAPH_LAYOUT_K")
    layout_iters = config.get("GRAPH_LAYOUT_ITERATIONS", 50)
    # Compute positions based on configured layout
    if layout_method == "spring":
        pos = nx.spring_layout(G, k=layout_k, iterations=layout_iters)
    else:
        pos = nx.kamada_kawai_layout(G)
    # Scale positions according to GRAPH_PNG_SCALE setting
    scale = config.get("GRAPH_PNG_SCALE", 0.33)
    pos = {node: (coords[0] * scale, coords[1] * scale) for node, coords in pos.items()}
    # Prevent node overlap if enabled
    if config.get("GRAPH_PHYSICS_PREVENT_OVERLAP", True):
        nodes = list(pos.keys())
        min_dist = config.get("GRAPH_PHYSICS_PREVENT_OVERLAP_DISTANCE", 0.1)
        for _ in range(config.get("GRAPH_PHYSICS_PREVENT_OVERLAP_ITERATIONS", 50)):
            moved = False
            for i in range(len(nodes)):
                for j in range(i+1, len(nodes)):
                    n1, n2 = nodes[i], nodes[j]
                    x1, y1 = pos[n1]
                    x2, y2 = pos[n2]
                    dx, dy = x1 - x2, y1 - y2
                    dist = math.hypot(dx, dy)
                    if dist < min_dist:
                        if dist == 0:
                            dx, dy = 0.01, 0.01
                            dist = math.hypot(dx, dy)
                        shift = (min_dist - dist) / 2
                        ux, uy = dx / dist, dy / dist
                        pos[n1] = (x1 + ux * shift, y1 + uy * shift)
                        pos[n2] = (x2 - ux * shift, y2 - uy * shift)
                        moved = True
            if not moved:
                break
    # Center graph positions by subtracting mean coordinates
    mean_x = sum(x for x, _ in pos.values()) / len(pos)
    mean_y = sum(y for _, y in pos.values()) / len(pos)
    pos = {node: (x - mean_x, y - mean_y) for node, (x, y) in pos.items()}
    # Static PNG layout with fixed scaling
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_aspect('equal')
    node_colors = [type_fill_colors.get(n, "#f2f2f2") for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color=node_colors, edgecolors="#222", ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)
    edge_styles = [d.get("style", "solid") for _, _, d in G.edges(data=True)]
    nx.draw_networkx_edges(G, pos, arrows=True, style=edge_styles, ax=ax)
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, ax=ax)
    # Set symmetric axis limits to center graph with buffer
    xs = [coords[0] for coords in pos.values()]
    ys = [coords[1] for coords in pos.values()]
    if xs and ys:
        max_x = max(abs(x) for x in xs)
        max_y = max(abs(y) for y in ys)
        max_range = max(max_x, max_y)
        # Use 15% buffer for more breathing room and to avoid clipping
        buffer = max_range * 0.15
        ax.set_xlim(-max_range - buffer, max_range + buffer)
        ax.set_ylim(-max_range - buffer, max_range + buffer)
    ax.set_axis_off()
    # Keine automatische Neuberechnung mehr – statische Achsenlimits nutzen
    legend_elements = [
        Line2D([0], [0], color="#222", lw=2.4, label="Explicit relationship →"),
        Line2D([0], [0], color="#888", lw=2.0, linestyle="dashed", label="Implicit relationship →")
    ]
    # Typ-Farben-Legende auf Basis der Knoten
    type_color_map = {}
    for node, color in type_fill_colors.items():
        typ = get_entity_type(node)
        if typ:
            type_color_map[typ] = color
    for typ, color in sorted(type_color_map.items()):
        legend_elements.append(Patch(facecolor=color, edgecolor="#444", label=typ.capitalize()))
    # Add legend at figure level (lower-left image corner)
    fig.legend(handles=legend_elements, loc="lower left",
               bbox_to_anchor=(0.02, 0.02), bbox_transform=fig.transFigure,
               fontsize=9, frameon=True, facecolor="white", edgecolor="#aaa")
    # Remove all subplot margins for maximal drawing area
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(png_filename, dpi=180)
    plt.close(fig)
    logging.info(f"Knowledge Graph PNG gespeichert: {png_filename}")
    print(f"Knowledge Graph PNG gespeichert: {png_filename}")

    # -- HTML Visualization (interactive) using PyVis --
    net = Network(height="800px", width="100%", directed=True, bgcolor="#ffffff", font_color="#222", notebook=False)
    # Reuse static positions and invert Y for matching orientation
    scale_px = config.get("GRAPH_INTERACTIVE_SCALE", 1000)
    pos_inter = {node: (coords[0] * scale_px, -coords[1] * scale_px) for node, coords in pos.items()}
    for node in G.nodes():
        x, y = pos_inter.get(node, (0, 0))
        net.add_node(node, label=node, color=type_fill_colors.get(node, "#f2f2f2"), x=x, y=y, physics=False)
    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, label=d.get("label", ""), color="#333", arrows="to",
                     dashes=(d.get("style") == "dashed"), font={"size": 10}, smooth=False)
    # Save interactive HTML directly
    net.write_html(html_filename)
    # Inject HTML-Legende am Seitenanfang
    legend_html = '<div style="padding:8px; background:#f9f9f9; border:1px solid #ddd; margin:0 auto 8px auto; border-radius:5px; font-size:12px; max-width:800px; text-align:center;">'
    legend_html += '<h4 style="margin-top:0; margin-bottom:5px;">Knowledge Graph</h4>'
    legend_html += '<div style="margin:5px 0"><b>Entity Types:</b> '
    for typ, color in sorted(type_color_map.items()):
        legend_html += f'<span style="background:{color};border:1px solid #444;padding:1px 4px;margin-right:4px;display:inline-block;font-size:11px;">{typ.capitalize()}</span>'
    legend_html += '</div>'
    legend_html += '<div style="margin:5px 0"><b>Relationships:</b> '
    legend_html += '<span style="border-bottom:1px solid #333;padding:1px 4px;margin-right:5px;display:inline-block;font-size:11px;">Explicit</span>'
    legend_html += '<span style="border-bottom:1px dashed #555;padding:1px 4px;display:inline-block;font-size:11px;">Implicit</span>'
    legend_html += '</div></div>'
    with open(html_filename, 'r', encoding='utf-8') as f:
        html_content = f.read()
    if '<body>' in html_content:
        html_content = html_content.replace('<body>', '<body>\n' + legend_html + '\n')
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logging.info(f"Interaktive Knowledge Graph HTML gespeichert: {html_filename}")
    print(f"Interaktive Knowledge Graph HTML gespeichert: {html_filename}")
    return {"png": png_filename, "html": html_filename}
