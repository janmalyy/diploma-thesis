import networkx as nx
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output

from diploma_thesis.utils.parse_xml import get_edges_from_xml, get_nodes_from_xml, Node, Edge
from diploma_thesis.settings import PACKAGE_DIR, DATA_DIR


def load_graph_data(xml_path) -> tuple[list[Node], list[Edge]]:
    nodes = get_nodes_from_xml(xml_path)
    edges = get_edges_from_xml(xml_path)
    return nodes, edges


def build_graph(nodes, edges) -> nx.Graph:
    G = nx.DiGraph()
    node_map = {node.identifier: node for node in nodes}

    for node in nodes:
        G.add_node(node.identifier,
                   name=node.name,
                   ner_type=node.ner_type,
                   count=node.count)

    for edge in edges:
        if edge.node1 in node_map and edge.node2 in node_map:
            G.add_edge(edge.node1, edge.node2, score=edge.score, relation_type=edge.relation_type)

    return G


def compute_node_positions(G) -> nx.Graph:
    pos = nx.spring_layout(G, seed=42)
    for node in G.nodes:
        G.nodes[node]["pos"] = pos[node]
    return G


def create_edge_traces_with_labels(G) -> list[go.Scatter]:
    """
    Create edge line traces and permanent text annotations for each edge.

    Parameters:
        G (networkx.Graph): Graph with node positions and edge attributes.

    Returns:
        list[go.Scatter]: List containing edge lines and text annotations as Scatter traces.
    """
    edge_lines_x = []
    edge_lines_y = []
    label_x = []
    label_y = []
    label_text = []

    for edge in G.edges:
        x0, y0 = G.nodes[edge[0]]["pos"]
        x1, y1 = G.nodes[edge[1]]["pos"]

        edge_lines_x += [x0, x1, None]
        edge_lines_y += [y0, y1, None]

        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2

        attrs = G.edges[edge]
        relation = attrs.get("relation_type", "N/A")
        score = attrs.get("score", "N/A")
        label = f"{relation} (score: {score})"

        label_x.append(mx)
        label_y.append(my)
        label_text.append(label)

    edge_trace = go.Scatter(
        x=edge_lines_x,
        y=edge_lines_y,
        line=dict(width=1, color="#1f1f1f"),
        mode="lines",
        hoverinfo="none",
        showlegend=False
    )

    label_trace = go.Scatter(
        x=label_x,
        y=label_y,
        text=label_text,
        mode="text",
        textposition="top center",
        textfont=dict(color="gray", size=12),
        hoverinfo="none",
        showlegend=False
    )

    return [edge_trace, label_trace]


def create_node_trace(G) -> go.Scatter:
    node_x, node_y, node_text, node_customdata, node_colors = [], [], [], [], []
    color_map = {"Gene": "purple", "Disease": "orange", "Chemical": "green",    # same mapping as in pubtator web app
                 "CellLine": "cyan", "Variant": "red", "Species": "blue"}

    for node in G.nodes:
        x, y = G.nodes[node]["pos"]
        attrs = G.nodes[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(attrs.get("name"))
        node_customdata.append({
            "name": attrs.get("name"),
            "id": node,
            "ner_type": attrs.get("ner_type", "N/A"),
            "count": attrs.get("count", "N/A")
        })
        node_colors.append(color_map.get(attrs.get("ner_type"), "gray"))  # Default to gray if type not found

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        hoverinfo="text",
        textposition="bottom center",
        textfont=dict(size=12),
        customdata=node_customdata,
        marker=dict(
            size=12,
            color=node_colors  # Use the list of colors
        )
    )
    return node_trace


def create_figure(edge_trace, node_trace, label_trace) -> go.Figure:
    return go.Figure(
        data=[edge_trace, node_trace, label_trace],
        layout=go.Layout(
            title="Gene-Disease Network",
            showlegend=True,  # Enable legend to see color mapping
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )


def create_dash_app(fig) -> dash.Dash:
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
        if clickData is None:
            return "Click on a node to see its attributes."
        data = clickData["points"][0]["customdata"]
        return f"""Node Name: {data["name"]}\nType: {data["ner_type"]}\nID: {data["id"]}\nCount: {data["count"]}"""

    return app


def main() -> None:
    xml_path = DATA_DIR / "test2" / "article_31888550.xml"
    nodes, edges = load_graph_data(xml_path)
    G = build_graph(nodes, edges)
    G = compute_node_positions(G)
    edge_trace, label_trace = create_edge_traces_with_labels(G)
    node_trace = create_node_trace(G)
    fig = create_figure(edge_trace, node_trace, label_trace)
    app = create_dash_app(fig)
    app.run(debug=True)


if __name__ == "__main__":
    main()
