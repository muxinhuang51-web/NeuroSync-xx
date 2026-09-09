from collections import defaultdict
import pprint

class DataSimplifier:
    def __init__(self, intent_tree, task_graph, mapping):
        """
        初始化简化器。
        :param intent_tree: Intent Tree 数据结构
        :param task_graph: Task Graph 数据结构
        :param mapping: 映射关系数据结构
        """
        self.intent_tree = intent_tree
        self.task_graph = task_graph
        self.mapping = mapping
        self.simplified_graph = None  # 简化后的图
        self.subgraph_cache = {}  # 子图缓存

    def simplify(self, focus_nodes):
        """
        根据指定的被关注节点（focus_nodes）对任务图进行化简。
        :param focus_nodes: 被关注的节点列表
        """
        simplified_nodes = []
        simplified_links = []

        # Step 1: 找到所有被关注节点对应的子图
        focused_node_ids = set()
        for node in focus_nodes:
            if node in self.mapping:
                subgraph = self._get_subgraph(node)
                simplified_nodes.extend(subgraph["nodes"])
                simplified_links.extend(subgraph["links"])
                focused_node_ids.update([n["id"] for n in subgraph["nodes"]])

        # Step 2: 合并未被关注的部分
        all_task_nodes = {node["id"]: node for node in self.task_graph["nodes"]}
        unfocused_nodes = set(all_task_nodes.keys()) - focused_node_ids

        # 按照 Intent Tree 的第二层节点合并未被关注的部分
        merged_nodes = {}
        for top_intent, second_layer in self.intent_tree.items():
            if isinstance(second_layer, dict):  # 确保第二层是字典结构
                for sub_intent, data in second_layer.items():
                    if sub_intent not in focus_nodes:  # 如果当前子意图不在被关注节点中
                        intent_node_ids = set(data.get("nodes", []))
                        intersected_unfocused = intent_node_ids & unfocused_nodes

                        if intersected_unfocused:
                            merged_node_id = f"Merged_{sub_intent}"
                            merged_nodes[merged_node_id] = {
                                "id": merged_node_id,
                                "description": f"Merged nodes from sub-intent: {sub_intent}"
                            }
                            simplified_nodes.append(merged_nodes[merged_node_id])

                            # 添加连接关系
                            for link in self.task_graph["links"]:
                                source, target = link["source"], link["target"]
                                if source in intersected_unfocused and target in focused_node_ids:
                                    simplified_links.append({"source": merged_node_id, "target": target, "type": link["type"]})
                                elif source in focused_node_ids and target in intersected_unfocused:
                                    simplified_links.append({"source": source, "target": merged_node_id, "type": link["type"]})

        # 构建简化后的图
        self.simplified_graph = {
            "nodes": list({node["id"]: node for node in simplified_nodes}.values()),  # 去重
            "links": list({f"{link['source']}->{link['target']}": link for link in simplified_links}.values())  # 去重
        }

    def _get_subgraph(self, intent_node):
        """
        获取某个意图节点对应的子图。
        :param intent_node: 意图树中的节点名称
        :return: 子图数据结构
        """
        if intent_node not in self.mapping:
            return {"nodes": [], "links": []}

        # 缓存机制：避免重复计算
        if intent_node in self.subgraph_cache:
            return self.subgraph_cache[intent_node]

        # 提取子图
        subgraph = {
            "nodes": [node for node in self.task_graph["nodes"] if node["id"] in self.mapping[intent_node]["nodes"]],
            "links": [link for link in self.task_graph["links"] if
                      link["source"] in self.mapping[intent_node]["nodes"] and
                      link["target"] in self.mapping[intent_node]["nodes"]]
        }

        self.subgraph_cache[intent_node] = subgraph
        return subgraph

    def get_subgraph(self, node_id):
        """
        查询任意节点对应的子图。
        :param node_id: 节点ID
        :return: 子图数据结构
        """
        for intent_node, data in self.mapping.items():
            if node_id in data["nodes"]:
                return self._get_subgraph(intent_node)
        return {"nodes": [], "links": []}

    def get_simplified_graph(self):
        """获取简化后的图"""
        return self.simplified_graph


# 测试用例
if __name__ == "__main__":
    from demo_data_full import intent_tree, task_graph, mapping  # 假设测试数据在 demodata 文件中

    # 初始化简化器
    simplifier = DataSimplifier(intent_tree, task_graph, mapping)

    # 指定被关注的节点（假设这些节点来自 intent_tree 的第二层）
    focus_nodes = ["保存文本内容到本地文件"]

    # 执行化简
    simplifier.simplify(focus_nodes)

    # 输出简化后的图
    simplified_graph = simplifier.get_simplified_graph()
    print("Simplified Graph:")
    pprint.pprint(simplified_graph)

    # 查询子图
    subgraph = simplifier.get_subgraph("Node5")  # 示例查询 Node5 的子图
    print("\nSubgraph for Node5:")
    pprint.pprint(subgraph)