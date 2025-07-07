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
        self.merged_node_mapping = {}  # 合并节点到原始节点的映射
        
        # 计算task graph中的最大节点编号
        self.max_node_id = 0
        for node in self.task_graph["nodes"]:
            try:
                # 假设节点ID格式为"Node数字"
                node_num = int(node["id"].replace("Node", ""))
                self.max_node_id = max(self.max_node_id, node_num)
            except (ValueError, AttributeError):
                # 如果节点ID不符合预期格式，则忽略
                pass

    def simplify(self, focus_nodes):
        """
        根据指定的被关注节点（focus_nodes）对任务图进行化简。
        :param focus_nodes: 被关注的节点列表
        """
        simplified_nodes = []
        simplified_links = []
        focused_node_ids = set()
        # 用于跟踪节点合并信息的映射
        node_mapping = {}  # 原节点ID -> 合并后的节点ID

        # 确定基准层：提取所有第二层节点
        second_layer_nodes = []
        for top_intent, second_layer in self.intent_tree.items():
            if isinstance(second_layer, dict):
                second_layer_nodes.extend(second_layer.keys())

        # 遍历每个第二层节点
        for second_layer_node in second_layer_nodes:
            # 如果当前节点是被关注的节点
            if second_layer_node in focus_nodes:
                subgraph = self._get_subgraph(second_layer_node)
                simplified_nodes.extend(subgraph["nodes"])
                simplified_links.extend(subgraph["links"])
                focused_node_ids.update([n["id"] for n in subgraph["nodes"]])
            else:
                # 检查以该节点为root的sub intent tree中是否有被关注的node
                has_focus = False
                # 首先检查二级节点的子树中是否有被关注的节点
                for top_intent, second_layer in self.intent_tree.items():
                    if isinstance(second_layer, dict) and second_layer_node in second_layer:
                        if isinstance(second_layer[second_layer_node], dict):
                            for child_node in second_layer[second_layer_node].keys():
                                if child_node in focus_nodes or self._has_focused_node(second_layer[second_layer_node], child_node, focus_nodes):
                                    has_focus = True
                                    break
                
                if not has_focus:
                    # 合并为一个新的节点
                    subgraph_nodes = self._get_subgraph(second_layer_node)["nodes"]
                    subgraph_links = self._get_subgraph(second_layer_node)["links"]
                    subgraph_node_ids = {node["id"] for node in subgraph_nodes}
                    if subgraph_nodes:
                        # 创建新的节点ID
                        self.max_node_id += 1
                        merged_node_id = f"Node{self.max_node_id}"
                        merged_node = {
                            "id": merged_node_id,
                            "description": f"Merged intent: {second_layer_node}"
                        }
                        simplified_nodes.append(merged_node)
                        
                        # 记录节点映射关系
                        for node_id in subgraph_node_ids:
                            node_mapping[node_id] = merged_node_id
                        
                        # 记录合并节点到原始节点及其子图的映射
                        self.merged_node_mapping[merged_node_id] = {
                            "intent": second_layer_node,
                            "nodes": [node["id"] for node in subgraph_nodes],
                            "links": subgraph_links
                        }
                else:
                    # 递归执行化简
                    for top_intent, second_layer in self.intent_tree.items():
                        if isinstance(second_layer, dict) and second_layer_node in second_layer:
                            self._simplify_recursive(second_layer, second_layer_node, focus_nodes, simplified_nodes, simplified_links, focused_node_ids, node_mapping)

        # 处理所有的链接
        all_links = []
        for link in self.task_graph["links"]:
            source, target = link["source"], link["target"]
            
            # 获取源和目标节点的映射
            mapped_source = node_mapping.get(source, source)
            mapped_target = node_mapping.get(target, target)
            
            # 只添加源和目标都在简化图中的链接
            simplified_node_ids = {node["id"] for node in simplified_nodes}
            if mapped_source in simplified_node_ids and mapped_target in simplified_node_ids:
                all_links.append({"source": mapped_source, "target": mapped_target, "type": link["type"]})
        
        # 添加所有有效的链接
        simplified_links.extend(all_links)

        # 构建简化后的图
        self.simplified_graph = {
            "nodes": list({node["id"]: node for node in simplified_nodes}.values()),  # 去重
            "links": list({f"{link['source']}->{link['target']}": link for link in simplified_links}.values())  # 去重
        }

    def _simplify_recursive(self, intent_tree, current_node, focus_nodes, simplified_nodes, simplified_links, focused_node_ids, node_mapping):
        """递归简化 Intent Tree"""
        if isinstance(intent_tree, dict):
            for node, children in intent_tree.items():
                if node == current_node and isinstance(children, dict):
                    for child_node in children.keys():
                        if child_node in focus_nodes:
                            subgraph = self._get_subgraph(child_node)
                            simplified_nodes.extend(subgraph["nodes"])
                            simplified_links.extend(subgraph["links"])
                            focused_node_ids.update([n["id"] for n in subgraph["nodes"]])
                        else:
                            if not self._has_focused_node(children, child_node, focus_nodes):
                                subgraph_nodes = self._get_subgraph(child_node)["nodes"]
                                subgraph_links = self._get_subgraph(child_node)["links"]
                                subgraph_node_ids = {node["id"] for node in subgraph_nodes}
                                if subgraph_nodes:
                                    # 创建新的节点ID
                                    self.max_node_id += 1
                                    merged_node_id = f"Node{self.max_node_id}"
                                    merged_node = {
                                        "id": merged_node_id,
                                        "description": f"Merged intent: {child_node}"
                                    }
                                    simplified_nodes.append(merged_node)
                                    
                                    # 记录节点映射关系
                                    for node_id in subgraph_node_ids:
                                        node_mapping[node_id] = merged_node_id
                                    
                                    # 记录合并节点到原始节点及其子图的映射
                                    self.merged_node_mapping[merged_node_id] = {
                                        "intent": child_node,
                                        "nodes": [node["id"] for node in subgraph_nodes],
                                        "links": subgraph_links
                                    }
                            else:
                                self._simplify_recursive(children, child_node, focus_nodes, simplified_nodes, simplified_links, focused_node_ids, node_mapping)

    def _has_focused_node(self, intent_tree, current_node, focus_nodes):
        """检查以当前节点为根的子树中是否包含被关注的节点"""
        if isinstance(intent_tree, dict):
            for node, children in intent_tree.items():
                if node == current_node:
                    if isinstance(children, dict):
                        for child_node in children.keys():
                            if child_node in focus_nodes:
                                return True
                            if self._has_focused_node(children, child_node, focus_nodes):
                                return True
        return False

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
        Get a subgraph for a specific node. This is useful for expanding merged nodes.
        
        Args:
            node_id (str): ID of the node to get a subgraph for
        
        Returns:
            dict: Subgraph for the specified node
        """
        # Check if simplifier is available
        if not hasattr(self, 'simplifier') or not self.simplifier:
            print("Warning: Simplifier not initialized. Call graph_zoom first.")
            return None
        
        # Get the subgraph for the specified node
        return self.simplifier.get_subgraph(node_id)

    def get_simplified_graph(self):
        """获取简化后的图"""
        return self.simplified_graph

def complete_mapping_with_internal_links(mapping, task_graph):
    """
    基于给定的 task_graph 为 mapping 中每个子意图补全其内部 links。
    :param mapping: 已含 nodes 列表的映射关系字典
    :param task_graph: 包含所有 nodes 和 links 的任务图
    :return: 补全内部 links 后的映射关系字典
    """
    for sub_intent, info in mapping.items():
        node_ids = set(info.get("nodes", []))
        internal_links = []
        for link in task_graph.get("links", []):
            if link["source"] in node_ids and link["target"] in node_ids:
                internal_links.append(link)
        info["links"] = internal_links
    return mapping

# 测试用例
if __name__ == "__main__":
    from demo_data import intent_tree, task_graph, mapping  # 假设测试数据在 demodata 文件中

    print("mapping before complete:")
    pprint.pprint(mapping)
    mapping = complete_mapping_with_internal_links(mapping, task_graph)
    print("\nmapping after complete:")
    pprint.pprint(mapping)

    # 初始化简化器
    simplifier = DataSimplifier(intent_tree, task_graph, mapping)

    # 指定被关注的节点
    focus_nodes = ["提取小标题"]  # 可以包含不同层的节点

    # 执行化简
    simplifier.simplify(focus_nodes)

    # 输出简化后的图
    simplified_graph = simplifier.get_simplified_graph()
    print("Simplified Graph:")
    pprint.pprint(simplified_graph)

    # 查询子图
    subgraph = simplifier.get_subgraph("Node15")  # 示例查询 Node5 的子图
    print("\nSubgraph for your input node:")
    pprint.pprint(subgraph)