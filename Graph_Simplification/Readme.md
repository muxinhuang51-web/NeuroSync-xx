### Prompt
基于下边的算法描述修改代码

算法描述 输入： 在之前的对话中，我们生成了以下内容：

Task Graph：描述代码执行的任务及其关联关系，节点表示任务，链接表示任务间的依赖关系。 Intent Tree：表示用户希望代码实现的意图层级结构，树的根节点表示总体意图，子节点表示具体子意图，支持多层级嵌套。由于你要生成mapping并保证每一个节点都和task graph对应，你需要思考怎么添加intent tree的node，是否node太过于细节。 Mapping：为Intent Tree中的每个节点找到对应的Task Graph子图（Subgraph），确保两者一一对应。intent tree可能有多层节点，请你为每一层的每一个每一个节点都生成对应的sub graph，不用考虑长度，应有尽有。 具体定义如下：

Task Graph：通过分析代码任务流生成，节点表示任务，链接表示任务间的数据流动或依赖关系。 Intent Tree：基于用户输入解析生成，树的深度代表意图的具体程度。 Mapping：建立Intent Tree与Task Graph之间的映射关系，确保每个Intent Tree节点有唯一的Task Graph子图。最初的mapping只有node没有links，你可以先调用complete_mapping_with_internal_links补全links 额外的输入：

Nodes：指定被关注的intent tree中的节点列表，这些节点在化简过程中保持不变。这些nodes可能是不同层的 输出： Simplified Graph：简化后的任务图，保留了被关注部分的完整子图，并将未被关注的部分分层合并为新的节点。 Subgraph 查询功能：提供一个方法，能够查询任意节点对应的子图。 算法步骤： 确定基准层：

在每次调用过程中，都将给定的 Intent Tree 的第二层节点作为化简的基准层。Root是第一层，Root的子节点是第二层 提取所有第二层节点：

遍历 Intent Tree，提取所有的第二层节点名称。 执行化简：

遍历每个第二层节点： 如果当前节点是被关注的节点（即在 Nodes 列表中），保持其对应的子图不变。 如果当前节点不是被关注的节点，并且以该节点为root的sub intent tree中没有被关注的node，则将其对应的子图合并为一个新的节点，新节点的名称使用该 Intent Tree 节点名。 如果节点未被提及但下层有被关注节点，递归执行这里提供的化简方式，直到全部都被化简完毕 生成简化后的图：

将所有保留的子图和合并的新节点重新组合成一个新的 Task Graph。 提供子图查询功能：

对于任意节点，通过 Mapping 找到其对应的子图并返回。 你可以根据需求扩充函数或删除函数。修改我现在给你的代码

# Graph Simplification Algorithm for Task Graphs Based on Intent Focus

## 1. Introduction

This document describes a system for simplifying complex task graphs by preserving sections of interest and merging less relevant portions. The algorithm uses an intent tree to guide the simplification process, allowing users to specify which intentions should remain detailed while others are consolidated.

## 2. Formal Problem Definition

### 2.1 Input Structures

- **Intent Tree** ($T$): A hierarchical tree structure representing user intentions
  - $T = (V_T, E_T)$ with nodes representing intentions and edges representing parent-child relationships
  - Each level represents increasingly specific intentions

- **Task Graph** ($G$): A directed graph representing computational tasks
  - $G = (V_G, E_G)$ with nodes representing tasks and edges representing dependencies
  - Each edge has a type attribute indicating the nature of the dependency

- **Mapping** ($M$): Associates intent nodes to subgraphs of the Task Graph
  - $M: V_T \rightarrow \mathcal{P}(V_G) \times \mathcal{P}(E_G)$
  - For each intent node, identifies the corresponding tasks and relationships

- **Focus Nodes** ($F$): A subset of Intent Tree nodes designated for preservation
  - $F \subseteq V_T$

### 2.2 Output

- **Simplified Graph** ($G'$): A condensed version of the task graph
  - $G' = (V', E')$ where typically $|V'| < |V_G|$
  - Preserves subgraphs corresponding to focus nodes
  - Merges non-focus subgraphs into representative nodes

- **Subgraph Query Function**: Retrieves original subgraph details for any node in $G'$

## 3. Algorithm Description

### 3.1 High-Level Approach

The simplification process:
1. Identifies the second layer of the Intent Tree as the base for simplification
2. Preserves subgraphs corresponding to focus nodes and their children
3. Merges subgraphs not containing focus nodes into single representative nodes
4. Reconstructs the connections between preserved and merged nodes

### 3.2 Pseudocode

```
ALGORITHM GraphSimplify(IntentTree T, TaskGraph G, Mapping M, FocusNodes F)

// Initialize data structures
simplified_nodes ← ∅
simplified_links ← ∅
focused_node_ids ← ∅
node_mapping ← ∅  // Maps original node IDs to merged node IDs

// Determine base layer for simplification (second layer)
second_layer_nodes ← GetSecondLayerNodes(T)

// Process each second layer node
FOR EACH node IN second_layer_nodes:
    IF node ∈ F THEN
        // Preserve the entire subgraph for focus nodes
        subgraph ← GetSubgraph(M, G, node)
        simplified_nodes.append(subgraph.nodes)
        simplified_links.append(subgraph.links)
        focused_node_ids.add(IDs of subgraph.nodes)
    ELSE
        // Check if subtree contains any focus nodes
        has_focus ← HasFocusedNodeInSubtree(T, node, F)
        
        IF NOT has_focus THEN
            // Merge subgraph into a single representative node
            subgraph ← GetSubgraph(M, G, node)
            IF subgraph.nodes ≠ ∅ THEN
                merged_node ← CreateMergedNode(node, subgraph)
                simplified_nodes.append(merged_node)
                
                // Record mapping from original nodes to merged node
                FOR EACH original_node IN subgraph.nodes:
                    node_mapping[original_node.id] ← merged_node.id
                
                // Store information for subgraph querying
                merged_node_mapping[merged_node.id] ← {
                    intent: node,
                    nodes: [IDs of subgraph.nodes],
                    links: subgraph.links
                }
            END IF
        ELSE
            // Recursively simplify subtree with focus nodes
            RecursiveSimplify(T, node, F, simplified_nodes, simplified_links, 
                             focused_node_ids, node_mapping)
        END IF
    END IF
END FOR

// Process links between nodes in simplified graph
FOR EACH link IN G.links:
    mapped_source ← node_mapping.get(link.source, link.source)
    mapped_target ← node_mapping.get(link.target, link.target)
    
    IF mapped_source AND mapped_target both in simplified_nodes THEN
        simplified_links.append({
            source: mapped_source,
            target: mapped_target,
            type: link.type
        })
    END IF
END FOR

// Deduplicate nodes and links
simplified_graph ← {
    nodes: Deduplicate(simplified_nodes),
    links: Deduplicate(simplified_links)
}

RETURN simplified_graph
```

### 3.3 Recursive Simplification

```
FUNCTION RecursiveSimplify(T, current_node, F, simplified_nodes, simplified_links, 
                           focused_node_ids, node_mapping)
    
    FOR EACH (node, children) IN T WHERE node = current_node:
        IF children is a dictionary THEN
            FOR EACH child_node IN children.keys():
                IF child_node ∈ F THEN
                    // Preserve subgraph for focused child node
                    subgraph ← GetSubgraph(M, G, child_node)
                    simplified_nodes.append(subgraph.nodes)
                    simplified_links.append(subgraph.links)
                    focused_node_ids.add(IDs of subgraph.nodes)
                ELSE
                    IF NOT HasFocusedNodeInSubtree(children, child_node, F) THEN
                        // Merge subgraph into single representative node
                        subgraph ← GetSubgraph(M, G, child_node)
                        IF subgraph.nodes ≠ ∅ THEN
                            merged_node ← CreateMergedNode(child_node, subgraph)
                            simplified_nodes.append(merged_node)
                            
                            // Record mapping
                            FOR EACH original_node IN subgraph.nodes:
                                node_mapping[original_node.id] ← merged_node.id
                            
                            // Store information for subgraph querying
                            merged_node_mapping[merged_node.id] ← {
                                intent: child_node,
                                nodes: [IDs of subgraph.nodes],
                                links: subgraph.links
                            }
                        END IF
                    ELSE
                        // Continue recursion for this branch
                        RecursiveSimplify(children, child_node, F, simplified_nodes, 
                                          simplified_links, focused_node_ids, node_mapping)
                    END IF
                END IF
            END FOR
        END IF
    END FOR
```

### 3.4 Helper Functions

```
FUNCTION HasFocusedNodeInSubtree(T, current_node, F)
    FOR EACH (node, children) IN T WHERE node = current_node:
        IF children is a dictionary THEN
            FOR EACH child IN children.keys():
                IF child ∈ F OR HasFocusedNodeInSubtree(children, child, F) THEN
                    RETURN TRUE
                END IF
            END FOR
        END IF
    END FOR
    RETURN FALSE

FUNCTION GetSubgraph(M, G, intent_node)
    IF intent_node ∉ M THEN
        RETURN {nodes: ∅, links: ∅}
    END IF
    
    node_ids ← M[intent_node].nodes
    
    subgraph ← {
        nodes: [node FOR node IN G.nodes WHERE node.id ∈ node_ids],
        links: [link FOR link IN G.links 
                WHERE link.source ∈ node_ids AND link.target ∈ node_ids]
    }
    
    RETURN subgraph

FUNCTION QuerySubgraph(node_id, merged_node_mapping, M, G)
    // Check if node is a merged node
    IF node_id ∈ merged_node_mapping THEN
        merged_info ← merged_node_mapping[node_id]
        RETURN {
            nodes: [node FOR node IN G.nodes WHERE node.id ∈ merged_info.nodes],
            links: merged_info.links
        }
    END IF
    
    // Check if node is an original node
    FOR EACH (intent_node, data) IN M:
        IF node_id ∈ data.nodes THEN
            RETURN GetSubgraph(M, G, intent_node)
        END IF
    END FOR
    
    RETURN {nodes: ∅, links: ∅}
```

## 4. Complexity Analysis

### 4.1 Time Complexity

- **Overall Algorithm**: $O(|V_T| \cdot |V_G| + |E_G|)$
  - Intent Tree traversal: $O(|V_T|)$
  - Subgraph extraction: $O(|V_T| \cdot |V_G|)$ - worst case examining all nodes for each intent
  - Link processing: $O(|E_G|)$

### 4.2 Space Complexity

- **Overall Space**: $O(|V_G| + |E_G|)$
  - Simplified graph storage: $O(|V_G| + |E_G|)$ - worst case if no simplification
  - Mapping structures: $O(|V_G|)$ for node mappings
  - Subgraph cache: $O(|V_T| \cdot (|V_G| + |E_G|))$ in worst case

## 5. Implementation Considerations

- **Cache Management**: Subgraph calculations are cached to avoid redundant computation
- **Node ID Management**: Incremental IDs are assigned to merged nodes, continuing from the highest existing ID
- **Link Preservation**: Special attention is paid to preserving relationships between both preserved and merged nodes
- **Query Interface**: The system provides an efficient interface to access original details of any node

## 6. Conclusion

This graph simplification algorithm enables effective visualization and analysis of complex task graphs by intelligently preserving areas of interest while consolidating less relevant sections. The approach maintains the ability to drill down into any section as needed, providing both high-level overview and detailed inspection capabilities.

# Graph Simplification Algorithm for Intent-Task Hierarchies

## Abstract

This paper presents a novel algorithm for simplifying task graphs based on hierarchical intent structures. The algorithm selectively preserves regions of interest while consolidating peripheral components, enabling efficient analysis and visualization of complex computational workflows. By maintaining a bidirectional mapping between simplified and original graph components, the algorithm supports on-demand reconstruction of detailed subgraphs. This approach provides an effective solution to the challenge of maintaining both high-level perspective and detailed insights in large-scale task graphs.

## 1. Introduction

Task graphs represent computational workflows with nodes denoting discrete operations and edges indicating dependencies or data flows between operations. While comprehensive for execution purposes, these graphs often become unwieldy for human comprehension as system complexity increases. Simultaneously, intent hierarchies capture the nested structure of user objectives that motivate these computational tasks.

Our algorithm addresses the need to simplify complex task graphs while preserving regions of particular interest to the analyst. By leveraging the hierarchical nature of intent structures, we develop a transformation that:
1. Preserves subgraphs corresponding to focused intents
2. Consolidates non-focused regions into representative nodes
3. Maintains the ability to recover detailed information on demand

## 2. Formal Problem Definition

### 2.1 Input Structures

Let us define the key structures used by our algorithm:

1. **Intent Tree (T)**: A hierarchical structure where:
   - $T = (V_T, E_T)$ represents a tree with vertices $V_T$ (intent nodes) and edges $E_T$ (parent-child relationships)
   - The root node represents the highest-level intent
   - Lower levels represent progressively more specific subintents
   - Each node $v \in V_T$ is labeled with a descriptive intent statement

2. **Task Graph (G)**: A directed graph where:
   - $G = (V_G, E_G)$ with $V_G$ representing task nodes and $E_G$ representing dependency edges
   - Each edge $e \in E_G$ may have a type attribute indicating the nature of dependency

3. **Mapping (M)**: A correspondence between intent nodes and task subgraphs:
   - $M: V_T \rightarrow 2^{V_G} \times 2^{E_G}$ 
   - For each intent node $v \in V_T$, $M(v) = (V_v, E_v)$ where $V_v \subseteq V_G$ and $E_v \subseteq E_G$
   - The mapping ensures that each intent is associated with the task nodes that implement it

4. **Focus Set (F)**: A designated subset of intent nodes:
   - $F \subseteq V_T$ represents intents of particular interest

### 2.2 Output Structures

1. **Simplified Graph (G')**: A condensed representation of the original task graph:
   - $G' = (V', E')$ where typically $|V'| \ll |V_G|$
   - Contains two types of nodes: (a) preserved original nodes associated with focused intents, and (b) merged nodes representing consolidated non-focused subgraphs

2. **Merged Node Mapping (M')**: A record associating merged nodes to their constituent components:
   - $M': V'_{merged} \rightarrow V_T \times 2^{V_G} \times 2^{E_G}$
   - For each merged node $v' \in V'_{merged}$, $M'(v') = (i, V_i, E_i)$ where $i \in V_T$ is the corresponding intent, and $(V_i, E_i)$ is the subgraph it represents

3. **Subgraph Query Function (Q)**: An operation retrieving original detail for any node:
   - $Q: V' \rightarrow 2^{V_G} \times 2^{E_G}$
   - Enables "zooming in" on any part of the simplified graph to reveal its constituent components

## 3. Algorithm Description

### 3.1 Overview

The algorithm operates in four main phases:
1. **Initialization**: Prepare data structures and identify the simplification baseline
2. **Node Processing**: Traverse the intent tree to identify nodes for preservation or consolidation
3. **Edge Processing**: Reconfigure edges to maintain connectivity in the simplified graph
4. **Finalization**: Deduplicate nodes and edges to ensure graph consistency

### 3.2 Detailed Algorithm

#### 3.2.1 Initialization Phase

```
FUNCTION Initialize(T, G, M)
    S ← {nodes: ∅, links: ∅}                // Simplified graph structure
    F_ids ← ∅                               // Task IDs in focus areas
    N_map ← ∅                               // Original to merged node mapping
    M_map ← ∅                               // Merged node information map
    max_id ← GetMaximumNodeId(G)            // For generating unique IDs
    
    RETURN (S, F_ids, N_map, M_map, max_id)
```

#### 3.2.2 Node Processing Phase

```
FUNCTION Simplify(T, G, M, F)
    (S, F_ids, N_map, M_map, max_id) ← Initialize(T, G, M)
    
    // Extract second layer nodes as simplification baseline
    baseline_nodes ← ExtractSecondLayerNodes(T)
    
    FOR EACH node ∈ baseline_nodes
        IF node ∈ F THEN
            // Preserve focused intents completely
            subgraph ← GetSubgraph(M, G, node)
            S.nodes ← S.nodes ∪ subgraph.nodes
            S.links ← S.links ∪ subgraph.links
            F_ids ← F_ids ∪ ExtractNodeIds(subgraph.nodes)
        ELSE
            // Check if subtree contains any focused nodes
            has_focus ← ContainsAnyFocusedNode(T, node, F)
            
            IF NOT has_focus THEN
                // Consolidate the entire subgraph
                MergeSubgraph(node, M, G, S, N_map, M_map, max_id)
            ELSE
                // Recursive simplification needed
                ProcessSubtreeWithFocus(T, node, F, S, F_ids, N_map, M_map, max_id, G, M)
            END IF
        END IF
    END FOR
    
    // Process links between simplified nodes
    ProcessLinks(G, S, N_map)
    
    // Deduplicate nodes and links
    DeduplicateGraph(S)
    
    RETURN S
```

#### 3.2.3 Subgraph Processing

```
FUNCTION MergeSubgraph(intent_node, M, G, S, N_map, M_map, max_id)
    subgraph ← GetSubgraph(M, G, intent_node)
    
    IF subgraph.nodes ≠ ∅ THEN
        // Create merged representative node
        max_id ← max_id + 1
        merged_id ← "Node" + max_id
        merged_node ← {
            id: merged_id,
            description: "Merged nodes from intent: " + intent_node
        }
        S.nodes ← S.nodes ∪ {merged_node}
        
        // Update mappings for future reference
        FOR EACH n ∈ subgraph.nodes
            N_map[n.id] ← merged_id
        END FOR
        
        M_map[merged_id] ← {
            intent: intent_node,
            nodes: [n.id FOR EACH n ∈ subgraph.nodes],
            links: subgraph.links
        }
    END IF
```

```
FUNCTION ProcessSubtreeWithFocus(T, current_node, F, S, F_ids, N_map, M_map, max_id, G, M)
    FOR EACH (node, children) ∈ T WHERE node = current_node AND IS_DICT(children)
        FOR EACH child_node ∈ KEYS(children)
            IF child_node ∈ F THEN
                // Preserve this focused intent
                subgraph ← GetSubgraph(M, G, child_node)
                S.nodes ← S.nodes ∪ subgraph.nodes
                S.links ← S.links ∪ subgraph.links
                F_ids ← F_ids ∪ ExtractNodeIds(subgraph.nodes)
            ELSE
                // Check if this subtree contains focus nodes
                has_focus ← ContainsAnyFocusedNode(children, child_node, F)
                
                IF NOT has_focus THEN
                    MergeSubgraph(child_node, M, G, S, N_map, M_map, max_id)
                ELSE
                    ProcessSubtreeWithFocus(children, child_node, F, S, F_ids, N_map, M_map, max_id, G, M)
                END IF
            END IF
        END FOR
    END FOR
```

#### 3.2.4 Edge Processing

```
FUNCTION ProcessLinks(G, S, N_map)
    all_links ← ∅
    simplified_node_ids ← {n.id | n ∈ S.nodes}
    
    FOR EACH link ∈ G.links
        // Map original endpoints to their simplified counterparts
        src ← N_map.GET(link.source, link.source)
        tgt ← N_map.GET(link.target, link.target)
        
        // Only keep links between nodes that exist in simplified graph
        IF src ∈ simplified_node_ids AND tgt ∈ simplified_node_ids THEN
            all_links ← all_links ∪ {source: src, target: tgt, type: link.type}
        END IF
    END FOR
    
    S.links ← S.links ∪ all_links
```

#### 3.2.5 Helper Functions

```
FUNCTION ContainsAnyFocusedNode(T, current_node, F)
    FOR EACH (node, children) ∈ T WHERE node = current_node
        IF IS_DICT(children) THEN
            FOR EACH child ∈ KEYS(children)
                IF child ∈ F OR ContainsAnyFocusedNode(children, child, F) THEN
                    RETURN TRUE
                END IF
            END FOR
        END IF
    END FOR
    RETURN FALSE
```

```
FUNCTION GetSubgraph(M, G, intent_node)
    IF intent_node ∉ M THEN
        RETURN {nodes: ∅, links: ∅}
    END IF
    
    node_ids ← M[intent_node].nodes
    
    subgraph ← {
        nodes: [n | n ∈ G.nodes, n.id ∈ node_ids],
        links: [l | l ∈ G.links, l.source ∈ node_ids AND l.target ∈ node_ids]
    }
    
    RETURN subgraph
```

### 3.3 Query Mechanism

```
FUNCTION QuerySubgraph(node_id, M_map, M, G)
    // Case 1: Node is a merged representative
    IF node_id ∈ M_map THEN
        merged_info ← M_map[node_id]
        RETURN {
            nodes: [n | n ∈ G.nodes, n.id ∈ merged_info.nodes],
            links: merged_info.links
        }
    END IF
    
    // Case 2: Node is an original task node
    FOR EACH (intent_node, data) ∈ M
        IF node_id ∈ data.nodes THEN
            RETURN GetSubgraph(M, G, intent_node)
        END IF
    END FOR
    
    // Case 3: Node not found
    RETURN {nodes: ∅, links: ∅}
```

## 4. Complexity Analysis

### 4.1 Time Complexity

- **Initialization**: $O(|V_G|)$ for finding maximum node ID
- **Node Processing**: 
  - Intent tree traversal: $O(|V_T|)$ 
  - Subgraph extraction: $O(|V_T| \cdot (|V_G| + |E_G|))$
- **Edge Processing**: $O(|E_G|)$ for link reassignment
- **Overall**: $O(|V_T| \cdot (|V_G| + |E_G|))$

### 4.2 Space Complexity

- **Simplified Graph**: $O(|V_G| + |E_G|)$ in worst case
- **Mapping Structures**: $O(|V_G|)$ for node mapping
- **Merged Node Records**: $O(|V_T| \cdot (|V_G| + |E_G|))$ in worst case
- **Overall**: $O(|V_T| \cdot (|V_G| + |E_G|))$

## 5. Implementation Features

The algorithm implementation includes several practical features:

1. **Caching Mechanism**: Subgraph extraction results are cached to avoid redundant computation when the same intent node is referenced multiple times.

2. **Node ID Generation**: New merged nodes receive sequential IDs following the convention of the original task graph, ensuring consistent identification.

3. **Link Deduplication**: A hash-based approach prevents duplicate links in the simplified graph.

4. **Hierarchical Intent Analysis**: The recursive design processes nested intent structures of arbitrary depth.

## 6. Conclusion

The graph simplification algorithm presented here provides an effective approach to managing complex task graphs through intelligent consolidation based on hierarchical intent structures. By preserving regions of interest while merging peripheral components, the algorithm enables focused analysis while maintaining access to comprehensive details when needed. This balance between simplification and information preservation makes it particularly suitable for complex computational workflows where maintaining both high-level perspective and detailed insights is essential.


### 算法描述

#### 输入：
- **Intent Tree**：表示用户意图的层级结构，其中根节点代表总体意图，子节点表示具体的子意图。
- **Task Graph**：描述任务流及其依赖关系的图结构，节点表示任务，边表示任务间的依赖或数据流动。
- **Mapping**：建立 `Intent Tree` 与 `Task Graph` 之间的映射关系，确保每个 `Intent Tree` 节点都能找到对应的 `Task Graph` 子图。
- **Nodes**：指定被关注的节点列表，这些节点在化简过程中保持不变。

#### 输出：
- **Simplified Graph**：简化后的任务图，保留了被关注部分的完整子图，并将未被关注的部分合并为新的节点。
- **Subgraph 查询功能**：提供一个方法，能够查询任意节点对应的子图。

---

#### 算法步骤：

1. **确定基准层**：
   - 将 `Intent Tree` 的第二层节点作为化简的基准层。

2. **提取所有第二层节点**：
   - 遍历 `Intent Tree`，提取所有的第二层节点名称。

3. **执行化简**：
   - 遍历每个第二层节点：
     - 如果当前节点是被关注的节点（即在 `Nodes` 列表中），保持其对应的子图不变。
     - 如果当前节点不是被关注的节点，将其对应的子图合并为一个新的节点，新节点的名称使用该 `Intent Tree` 节点名。
     - 如果当前层未提及但下层有被关注节点的情况，递归执行化简。

4. **生成简化后的图**：
   - 将所有保留的子图和合并的新节点重新组合成一个新的 `Task Graph`。

5. **提供子图查询功能**：
   - 对于任意节点，通过 `Mapping` 找到其对应的子图并返回。

---

#### 辅助函数描述：

- **GetSecondLevelNodes(intent_tree)**:
  提取 `Intent Tree` 的第二层节点。

- **GetSubgraph(intent_node, task_graph, mapping, subgraph_cache)**:
  获取某个 `Intent Tree` 节点对应的子图。

- **AddSubgraphToSimplifiedGraph(subgraph, simplified_nodes, simplified_links)**:
  将子图添加到简化图中。

- **CreateMergedNode(merged_node_id)**:
  创建一个合并节点。

- **AddExternalLinksForMergedNode(merged_node_id, task_graph, mapping, simplified_links)**:
  为合并节点添加外部连接。

- **RemoveDuplicates(items)**:
  去重节点或边。


### Algorithm Description

#### Input:
- **Intent Tree**: A hierarchical structure representing user intents.
- **Task Graph**: A graph structure describing the task flow and dependencies, where nodes represent tasks and edges represent dependencies between tasks.
- **Mapping**: A mapping relationship between the `Intent Tree` and the `Task Graph`, ensuring that each node in the `Intent Tree` corresponds to a subgraph in the `Task Graph`.
- **Nodes**: A list of specified nodes to focus on, which remain unchanged during simplification.

#### Output:
- **Simplified Graph**: The simplified task graph, preserving the complete subgraphs of focused parts and merging the unfocused parts into new nodes.
- **Subgraph Query Function**: A method to query the subgraph corresponding to any given node.

---

#### Algorithm Steps:

1. **Determine the Base Layer**:
   - Use the second layer nodes of the `Intent Tree` as the base layer for simplification.

2. **Extract All Second-Level Nodes**:
   - Traverse the `Intent Tree` and extract all second-level node names.

3. **Perform Simplification**:
   - Iterate through each second-level node:
     - If the current node is a focused node (i.e., in the `Nodes` list), keep its corresponding subgraph unchanged.
     - If the current node is not a focused node, merge its corresponding subgraph into a new node, using the `Intent Tree` node name as the new node's name.
     - If the current layer does not mention but the lower layer contains focused nodes, recursively perform simplification.

4. **Generate the Simplified Graph**:
   - Reassemble all preserved subgraphs and merged new nodes into a new `Task Graph`.

5. **Provide Subgraph Query Functionality**:
   - For any given node, find and return its corresponding subgraph via the `Mapping`.

---

#### Helper Function Descriptions:

- **GetSecondLevelNodes(intent_tree)**:
  Extracts the second-level nodes from the `Intent Tree`.

- **GetSubgraph(intent_node, task_graph, mapping, subgraph_cache)**:
  Retrieves the subgraph corresponding to a specific `Intent Tree` node.

- **AddSubgraphToSimplifiedGraph(subgraph, simplified_nodes, simplified_links)**:
  Adds the subgraph to the simplified graph.

- **CreateMergedNode(merged_node_id)**:
  Creates a merged node.

- **AddExternalLinksForMergedNode(merged_node_id, task_graph, mapping, simplified_links)**:
  Adds external links for the merged node.

- **RemoveDuplicates(items)**:
  Removes duplicate nodes or edges.