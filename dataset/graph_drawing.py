import os
import json
import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout

class GraphDrawer:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    def draw_intent_tree(self, intent_tree, filename="intent_tree.png"):
        G = nx.DiGraph()
        self._add_nodes_edges(G, intent_tree)
        pos = graphviz_layout(G, prog="dot")
        plt.figure(figsize=(12, 8))
        nx.draw(G, pos, with_labels=True, arrows=True)
        plt.savefig(os.path.join(self.output_folder, filename))
        plt.close()

    def draw_task_graph(self, task_graph, filename="task_graph.png"):
        G = nx.DiGraph()
        for node in task_graph["nodes"]:
            G.add_node(node["id"], label=node["description"])
        for link in task_graph["links"]:
            G.add_edge(link["source"], link["target"])
        pos = graphviz_layout(G, prog="dot")
        plt.figure(figsize=(12, 8))
        nx.draw(G, pos, with_labels=True, arrows=True)
        plt.savefig(os.path.join(self.output_folder, filename))
        plt.close()

    def draw_mapping(self, intent_tree, task_graph, mapping, filename="mapping.png"):
        G = nx.DiGraph()
        self._add_nodes_edges(G, intent_tree)
        pos = graphviz_layout(G, prog="dot")
        plt.figure(figsize=(12, 8))
        nx.draw(G, pos, with_labels=True, arrows=True, node_color='lightblue')

        colors = ['lightgreen', 'lightcoral', 'lightgoldenrodyellow', 'lightpink', 'lightcyan']
        for i, (intent, details) in enumerate(mapping.items()):
            subG = nx.DiGraph()
            for node in details["nodes"]:
                subG.add_node(node)
            for link in details["links"]:
                subG.add_edge(link["source"], link["target"])
            sub_pos = graphviz_layout(subG, prog="dot")
            offset = pos[intent]
            for sub_node in subG.nodes():
                sub_pos[sub_node] = (sub_pos[sub_node][0] * 0.35 + offset[0], sub_pos[sub_node][1] * 0.35 + offset[1])
            nx.draw(subG, sub_pos, with_labels=True, arrows=False, node_color=colors[i % len(colors)])

        plt.savefig(os.path.join(self.output_folder, filename))
        plt.close()

    def _add_nodes_edges(self, G, tree, parent=None):
        for key, value in tree.items():
            G.add_node(key)
            if parent:
                G.add_edge(parent, key)
            self._add_nodes_edges(G, value, key)

# Example usage:
if __name__ == "__main__":
    output_folder = "/home/wzhangeb/lancet/dataset/graph_drawing_output"
    drawer = GraphDrawer(output_folder)

    intent_tree = {
        "Write a crawler to scrape content from a specified URL": {
            "Scrape images": {},
            "Scrape text": {},
            "Save full content": {
                "Save text": {
                    "Extract and save titles": {
                        "Annotate different levels of titles (e.g., H1, H2, H3)": {}
                    },
                    "Save main content": {}
                },
                "Save images": {},
                "Replace images in text with filenames": {}
            }
        }
    }

    task_graph = {
        "nodes": [
            {"id": "Node1", "description": "Initiate an HTTP request with a User-Agent header to get the target webpage content"},
            {"id": "Node2", "description": "Parse HTML using BeautifulSoup"},
            {"id": "Node3", "description": "Extract all text from the WeChat article and handle paragraph breaks"},
            {"id": "Node4", "description": "Save extracted text to text_with_images.txt, replacing image positions with filenames and inserting image captions"},
            {"id": "Node5", "description": "Find all images in the WeChat article"},
            {"id": "Node6", "description": "Download and save images"},
            {"id": "Node7", "description": "Save full content to full_content.html"},
            {"id": "Node8", "description": "Extract article title"},
            {"id": "Node9", "description": "Combine title and main content"},
            {"id": "Node10", "description": "Extract and annotate different levels of titles (e.g., H1, H2, H3)"}
        ],
        "links": [
            {"source": "Node1", "target": "Node2", "type": "parseHTML"},
            {"source": "Node2", "target": "Node3", "type": "extractText"},
            {"source": "Node3", "target": "Node4", "type": "saveTextWithImages"},
            {"source": "Node2", "target": "Node5", "type": "findImages"},
            {"source": "Node5", "target": "Node6", "type": "downloadImages"},
            {"source": "Node2", "target": "Node7", "type": "saveFullContent"},
            {"source": "Node2", "target": "Node8", "type": "extractTitle"},
            {"source": "Node8", "target": "Node9", "type": "combineTitleAndContent"},
            {"source": "Node3", "target": "Node9", "type": "combineTitleAndContent"},
            {"source": "Node2", "target": "Node10", "type": "extractHeadings"},
            {"source": "Node10", "target": "Node9", "type": "combineHeadingsAndContent"}
        ]
    }

    mapping = {
        "Write a crawler to scrape content from a specified URL": {
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6", "Node7", "Node8", "Node9", "Node10"],
            "links": [
                {"source": "Node1", "target": "Node2", "type": "parseHTML"},
                {"source": "Node2", "target": "Node3", "type": "extractText"},
                {"source": "Node3", "target": "Node4", "type": "saveTextWithImages"},
                {"source": "Node2", "target": "Node5", "type": "findImages"},
                {"source": "Node5", "target": "Node6", "type": "downloadImages"},
                {"source": "Node2", "target": "Node7", "type": "saveFullContent"},
                {"source": "Node2", "target": "Node8", "type": "extractTitle"},
                {"source": "Node8", "target": "Node9", "type": "combineTitleAndContent"},
                {"source": "Node3", "target": "Node9", "type": "combineTitleAndContent"},
                {"source": "Node2", "target": "Node10", "type": "extractHeadings"},
                {"source": "Node10", "target": "Node9", "type": "combineHeadingsAndContent"}
            ]
        },
        "Scrape images": {
            "nodes": ["Node5", "Node6"],
            "links": [
                {"source": "Node5", "target": "Node6", "type": "downloadImages"}
            ]
        },
        "Scrape text": {
            "nodes": ["Node3", "Node4"],
            "links": [
                {"source": "Node3", "target": "Node4", "type": "saveTextWithImages"}
            ]
        },
        "Save full content": {
            "nodes": ["Node7", "Node9", "Node10"],
            "links": [
                {"source": "Node2", "target": "Node7", "type": "saveFullContent"},
                {"source": "Node8", "target": "Node9", "type": "combineTitleAndContent"},
                {"source": "Node3", "target": "Node9", "type": "combineTitleAndContent"},
                {"source": "Node2", "target": "Node10", "type": "extractHeadings"},
                {"source": "Node10", "target": "Node9", "type": "combineHeadingsAndContent"}
            ]
        },
        "Save text": {
            "nodes": ["Node4", "Node8", "Node9", "Node10"],
            "links": [
                {"source": "Node3", "target": "Node4", "type": "saveTextWithImages"},
                {"source": "Node2", "target": "Node8", "type": "extractTitle"},
                {"source": "Node8", "target": "Node9", "type": "combineTitleAndContent"},
                {"source": "Node3", "target": "Node9", "type": "combineTitleAndContent"},
                {"source": "Node2", "target": "Node10", "type": "extractHeadings"},
                {"source": "Node10", "target": "Node9", "type": "combineHeadingsAndContent"}
            ]
        },
        "Save images": {
            "nodes": ["Node6"],
            "links": [
                {"source": "Node5", "target": "Node6", "type": "downloadImages"}
            ]
        },
        "Replace images in text with filenames": {
            "nodes": ["Node4"],
            "links": [
                {"source": "Node3", "target": "Node4", "type": "saveTextWithImages"}
            ]
        },
        "Extract and save titles": {
            "nodes": ["Node8"],
            "links": [
                {"source": "Node2", "target": "Node8", "type": "extractTitle"}
            ]
        },
        "Save main content": {
            "nodes": ["Node3", "Node9"],
            "links": [
                {"source": "Node3", "target": "Node9", "type": "combineTitleAndContent"}
            ]
        },
        "Annotate different levels of titles (e.g., H1, H2, H3)": {
            "nodes": ["Node10"],
            "links": [
                {"source": "Node2", "target": "Node10", "type": "extractHeadings"},
                {"source": "Node10", "target": "Node9", "type": "combineHeadingsAndContent"}
            ]
        }
    }

    drawer.draw_intent_tree(intent_tree)
    drawer.draw_task_graph(task_graph)
    drawer.draw_mapping(intent_tree, task_graph, mapping)