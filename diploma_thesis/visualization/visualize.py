import networkx as nx
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output

from diploma_thesis.pubtator3.parse_xml import get_edges_from_xml, get_nodes_from_xml, node_pretty_print
from diploma_thesis.settings import PACKAGE_DIR

# Load graph data
G = nx.DiGraph()
nodes = get_nodes_from_xml(PACKAGE_DIR / "pubtator3" / "test.xml")
edges = get_edges_from_xml(PACKAGE_DIR / "pubtator3" / "test.xml")

# print([node_pretty_print(node) for node in nodes])

# Build a map from identifier to node for easy lookup
node_map = {node.identifier: node for node in nodes}

# Initialize graph using node.identifier as unique key
for node in nodes:
    G.add_node(node.identifier,
               name=node.name,
               ner_type=node.ner_type,
               count=node.count)

# Add edges using node identifiers
for edge in edges:
    if edge.node1 in node_map and edge.node2 in node_map:
        G.add_edge(edge.node1, edge.node2, score=edge.score)

# Compute positions
pos = nx.spring_layout(G, seed=42)
for node in G.nodes:
    G.nodes[node]["pos"] = pos[node]

# Create edge trace
edge_trace = go.Scatter(
    x=[],
    y=[],
    line=dict(width=0.5, color="#888"),
    hoverinfo="none",
    mode="lines"
)

for edge in G.edges:
    x0, y0 = G.nodes[edge[0]]["pos"]
    x1, y1 = G.nodes[edge[1]]["pos"]
    edge_trace["x"] += (x0, x1, None)
    edge_trace["y"] += (y0, y1, None)

# Create node trace with customdata
node_x, node_y, node_text, node_customdata = [], [], [], []


for node in G.nodes:
    x, y = G.nodes[node]["pos"]
    node_x.append(x)
    node_y.append(y)
    attrs = G.nodes[node]
    # print(attrs)
    node_text.append(attrs.get("name"))
    node_customdata.append({
        "name": attrs.get("name"),
        "id": node,
        "ner_type": attrs.get("ner_type", "N/A"),
        "count": attrs.get("count", "N/A")
    })

node_trace = go.Scatter(
    x=node_x,
    y=node_y,
    mode="markers+text",
    text=node_text,
    hoverinfo="text",
    textposition="bottom center",
    customdata=node_customdata,
    marker=dict(
        showscale=True,
        colorscale="YlGnBu",
        size=12,
        color=list(range(len(node_x))),  # just some differentiation
        colorbar=dict(
            thickness=15,
            title="Node Index",
            xanchor="left"
        )
    )
)

# Create figure
fig = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title="Gene-Disease Network",
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
)

# Create Dash app
app = dash.Dash(__name__)
app.layout = html.Div([
    dcc.Graph(id="graph", figure=fig),
    html.Div(id="node-info", style={"whiteSpace": "pre-wrap", "marginTop": "20px"})
])


@app.callback(
    Output("node-info", "children"),
    Input("graph", "clickData")
)
def display_node_info(clickData):
    """
    Display attributes of the clicked node from the graph.
    """
    if clickData is None:
        return "Click on a node to see its attributes."

    data = clickData["points"][0]["customdata"]
    return f"""Node Name: {data["name"]}
Type: {data["ner_type"]}
ID: {data["id"]}
Count: {data["count"]}"""


if __name__ == "__main__":
    # pass
    app.run(debug=True)
