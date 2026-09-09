import os
import json
from .raw_data.data_loader import DataLoader
from .LLM_api import get_llm_response
from .graph_drawing import GraphDrawer
import glob
import datetime

class InteractionProcessor:
    def __init__(self, raw_data_folder, output_folder):
        self.data_loader = DataLoader(raw_data_folder)
        self.drawer = GraphDrawer(output_folder)
        self.output_folder = output_folder

    def process_interactions_fake(self, user_index):
        """
        Process interactions for testing purposes.
        Records current time to a text file.
        """
        
        # Create directory if it doesn't exist
        os.makedirs("/home/wzhangeb/lancet/DatasetGeneration/dialog_history/test_exe", exist_ok=True)
        
        # Get current time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to file
        filename = f"/home/wzhangeb/lancet/DatasetGeneration/dialog_history/interaction_{user_index}_{current_time.replace(':', '-').replace(' ', '_')}.txt"
        with open(filename, 'w') as f:
            f.write(f"Process started at: {current_time}")
    
    def process_interactions(self, user_index):
        # print(f"Processing interactions for user {user_index}...")

        # Process the first round
        # print("Processing first round...")
        first_round_prompt = self.data_loader.get_prompt_or_response(user_index, 0, mode='prompt')
        first_round_response = self.data_loader.get_prompt_or_response(user_index, 0, mode='response')
        first_round_result = self._process_first_round(first_round_prompt, first_round_response)
        # print("First round result: ", first_round_result)
        # Save and draw the first round results
        intent_tree, task_graph, mapping = self._save_results(first_round_result, 0)
        # print("First round processed and results saved.")
        # self._draw_results(intent_tree, task_graph, mapping, 0)

        # Process subsequent rounds
        round_number = 1
        previous_result = first_round_result
        while True:
            try:
                # print(f"Processing round {round_number}...")
                current_prompt = self.data_loader.get_prompt_or_response(user_index, round_number, mode='prompt')
                current_response = self.data_loader.get_prompt_or_response(user_index, round_number, mode='response')
                history_prompts = self.data_loader.get_all_prompts_to_round(user_index, round_number - 1)
                current_result = self._process_subsequent_rounds(previous_result, current_prompt, current_response, history_prompts)
                # print("Current round result: ", current_result)

                # Save the current round results
                intent_tree, task_graph, mapping = self._save_results(current_result, round_number)
                # print(f"Round {round_number} processed and results saved.")
                # Draw the current round results
                # self._draw_results(intent_tree, task_graph, mapping, round_number)
                
                # Update the previous result for the next iteration
                previous_result = current_result
                round_number += 1
                # break
            except IndexError:
                # print("No more rounds to process.")
                break

        # print("Processing completed.")

    def _process_first_round(self, first_round_prompt, first_round_response):
        prompt = f"""
        下边的材料是一个用户与LLM的第一轮对话信息，包含用户输入的prompt和LLM生成的response。这些内容中包含了代码和一些基本信息。我的目标是让您基于这些材料完成以下任务：

        ---
        ### 任务 1：构建意图树（Intent Tree）
        #### 输入：
        - 材料（1）：用户输入的prompt (`first_round_prompt`)。

        #### 要求：
        1. **概括总体意图**：分析用户输入，提取出用户的总体目标。
        2. **拆分子意图**：从用户输入中抽象出具体的子任务或要求，并将其组织成树形结构。
        - 示例：如果用户希望写一个爬虫程序，分别保存网页中的文字和图片，则总体意图为"写爬虫程序"，子意图包括"提取文字"和"提取图片"。
        3. **构建树形结构**：将总体意图和子意图按照层级关系组织成一棵树，父节点表示总体意图，子节点表示具体的子意图。
        - 如果某个子意图同时属于多个父意图，请将其作为公共子节点处理。
        - 这里生成的意图树和后边的mapping有关，详情参考任务3。
        4. **输出格式**：使用Python可读的嵌套字典格式表示意图树。

        #### 示例输出：
        intent_tree = {{
            "写一个爬虫程序，爬取指定URL的内容并保存到本地": {{
                "爬取文本内容并保存": {{}},
                "爬取图像内容并保存": {{}}
            }}
        }}


        ---
        ### 任务 2：构建任务图（Task Graph）
        #### 输入：
        - 材料（2）：LLM生成的代码 (first_round_response)。

        #### 要求：
        1. **识别任务**：从代码中提取出所有需要执行的任务，并为每个任务生成简短描述。
            - 示例：发起HTTP请求、解析HTML、提取文字、保存文件等。
            
        2. **构建图结构**：
            - 使用节点（Node）表示每个任务。
            - 使用边（Linkage）表示任务之间的依赖关系，并标记数据流动的方向和类型。

        3. **输出格式**：返回一个包含nodes和links的字典，其中：
            - nodes：任务列表，每个任务用id和description表示。
            - links：任务之间的关系列表，每个关系用source、target和type表示。

        #### 示例输出：
        task_graph = {{
            "nodes": [
                {{"id": "Node1", "description": "发起HTTP请求以获取目标网页的内容"}},
                {{"id": "Node2", "description": "使用BeautifulSoup解析HTML文档"}},
                {{"id": "Node3", "description": "提取文本内容并保存到文件中"}},
                {{"id": "Node4", "description": "在HTML文档中查找所有的图像URL"}},
                {{"id": "Node5", "description": "下载图像并保存到本地文件夹中"}},
                {{"id": "Node6", "description": "创建保存内容的本地文件夹（如果不存在）"}}
            ],
            "links": [
                {{"source": "Node1", "target": "Node2", "type": "parse"}},
                {{"source": "Node2", "target": "Node3", "type": "extractText"}},
                {{"source": "Node2", "target": "Node4", "type": "findImages"}},
                {{"source": "Node4", "target": "Node5", "type": "downloadImages"}},
                {{"source": "Node6", "target": "Node3", "type": "saveToFolder"}},
                {{"source": "Node6", "target": "Node5", "type": "saveToFolder"}}
            ]
        }}

        ---
        ### 任务 3：映射意图树与任务图
        #### 输入：
        - 任务 1 的意图树。
        - 任务 2 的任务图。

        #### 要求：
        1. **匹配子图节点**：针对意图树中的每个节点，在任务图中找到对应的子图（Sub Graph）并使用子图节点表示子图。
            - 子图应仅包含与该intent节点直接相关的部分，避免覆盖无关内容。
            - 如果任务图中存在与任务无关的公用部分，请勿将其纳入子图。
            - 请确保每个意图树节点都有对应的任务图子图。子图使用子图包含的节点表示。

        2. **确保一一对应**：每个意图树节点应唯一对应一个任务图子图对应，反之亦然。

        3. **输出格式**：以字典形式返回映射关系，其中：
            - 键：意图树中的节点名称。
            - 值：任务图中的子图，仅包含nodes。

        #### 示例输出如下，每个子图仅使用task node标识即可：
        mapping = {{
            "写一个爬虫程序，爬取指定URL的内容并保存到本地": {{
                "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6"]
            }},
            "爬取文本内容并保存": {{
                "nodes": ["Node1", "Node2", "Node3", "Node6"]
            }},
            "爬取图像内容并保存": {{
                "nodes": ["Node1", "Node2", "Node4", "Node5", "Node6"]
            }}
        }}

        ---
        ### 执行任务
        请基于以下材料完成上述三个任务并返回结果。返回时请严格按照以下格式：

        ```JSON_RESULT
        {{
            "intent_tree": {{
                // 你的intent_tree结果，使用完整的嵌套字典格式
            }},
            "task_graph": {{
                // 你的task_graph结果，包含nodes和links
            }},
            "mapping": {{
                // 你的mapping结果，每个intent节点名称对应的子图
            }}
        }}
        ```

        请注意：结果必须包裹在```JSON_RESULT和```之间，且格式必须是有效的JSON格式，不要添加任何注释。这对于后续系统自动解析极为重要。

        #### 材料（1） - 用户输入的prompt：
        {{{first_round_prompt}}}

        #### 材料（2） - 待总结的代码内容：
        {{{first_round_response}}}
        """
        
        result = get_llm_response("你是一个超强人工智能，擅长从代码和文本中总结提取结构化信息，尤其是擅长提取intent tree, task graph以及mapping", prompt)
        return result

    def _process_subsequent_rounds(self, previous_result, current_prompt, current_response, history_prompts):
        prompt = f"""
        ### 背景说明
        在之前的对话中，我们生成了以下内容：
        1. **Task Graph**：描述代码执行的任务及其关联关系，节点表示任务，链接表示任务间的依赖关系。
        2. **Intent Tree**：表示用户希望代码实现的意图层级结构，树的根节点表示总体意图，子节点表示具体子意图，支持多层级嵌套。由于你要生成mapping并保证每一个节点都和task graph对应，你需要思考怎么添加intent tree的node，是否node太过于细节。
        3. **Mapping**：为Intent Tree中的每个节点找到对应的Task Graph子图（Subgraph），确保两者一一对应。intent tree可能有多层节点，请你为每一层的每一个每一个节点都生成对应的sub graph，不用考虑长度，应有尽有。

        具体定义如下：
        - **Task Graph**：通过分析代码任务流生成，节点表示任务，链接表示任务间的数据流动或依赖关系。
        - **Intent Tree**：基于用户输入解析生成，树的深度代表意图的具体程度。
        - **Mapping**：建立Intent Tree与Task Graph之间的映射关系，确保每个Intent Tree节点有唯一的Task Graph子图。

        ---
        ### 任务1：更新Intent Tree

        #### A. 分析并修改Intent Tree
        根据用户的新输入，判断其对现有intent tree的影响，并执行以下操作：
        1. **已有意图补充**：细化或补充现有节点。
        2. **新增子意图**：添加全新的意图节点。
        3. **意群合并**：合并相似的子节点。
        4. **包含关系更新**：调整父子节点关系。
        5. **无影响判断**：若无影响，则保持原状。

        #### B. 构建规则
        - 在构建intent tree时，优先增加深度而非扩展宽度。
        - 确保每个节点都有对应的task graph子图。

        #### C. 返回格式
        使用嵌套字典格式返回更新后的Intent Tree，每一个子图仅使用node表示即可，其格式例如：
        {{
            "主意图": {{
                "子意图1": {{}},
                "子意图2": {{
                    "子子意图1": {{}},
                    "子子意图2": {{}}
                }}
            }}
        }}

        ---
        ### 任务2：更新Task Graph
        #### A. 分析代码任务流
        1. 从材料四（生成的代码）中提取所有任务，并为其生成简短描述。
        2. 将任务适中拆分，确保粒度与参考示例一致。

        #### B. 更新Task Graph
        1. 对比材料二中的现有task graph与当前代码任务流，调整节点和链接关系以匹配代码逻辑。
        2. 若用户指定了某些具体变量，需在task graph中标注其值。
        3. 确保task graph格式与材料二一致，仅对发生变化的部分进行修改。

        #### C. 返回格式
        使用JSON格式返回更新后的Task Graph，格式例如：
        {{
            "nodes": [
                {{"id": "Node1", "description": "任务1描述"}},
                {{"id": "Node2", "description": "任务2描述"}}
            ],
            "links": [
                {{"source": "Node1", "target": "Node2", "type": "数据流动类型"}}
            ]
        }}

        ---
        ### 任务3：更新Intent Tree 和 Task Graph 的映射关系
        #### A. 找到每个Intent Tree节点对应的Subgraph，请你确保每个intent tree的node都有对应的subgraph。
        1. 遍历intent tree中的每个节点，在task graph中找到与其相关的任务节点和链接。并返回任务节点来标识subgraph。
        2. 确保同一层级的subgraph不重叠，子层级的subgraph是父层级subgraph的子集。

        #### B. 检查并修正映射关系
        1. 确保intent tree中每个节点都有唯一的subgraph，且subgraph与intent node一一对应。
        2. 若发现某些节点的子节点过多或subgraph无法一一对应，则特别关注任务1中的意群合并操作，通过合并减少冗余。
        3. 保证修改完之后生成的mapping中， 每一个intent tree中的node都有一个subgraph对应。

        #### **注意！**
        - 在构建 Intent Tree 时，需为各级别节点生成对应的 Subgraph，务必保证每个节点的 Subgraph 完整无遗漏。因此，在生成过程中，请特别关注 Subgraph 的完整性验证。不要省略任何一个节点的mapping。
        - 每次更新 Intent Tree 时，应重点检查发生变化的部分，并为其生成精准的 Subgraph。若发现某些节点无法匹配到合适的 Subgraph，建议重新评估这些节点的必要性，考虑是否需要调整或优化 Intent Tree 的结构。
        - 此外，对于过于细化、不具备实际映射价值的 Intent Node，可以适当忽略，不必添加在intent tree中，避免增加不必要的复杂性, 如果要新增节点，请确保他有正确的mapping并被记录！

        #### C. 返回格式
        使用字典格式返回mapping信息：
        mapping = {{
            "main_intent(节点名称)": {{
                "nodes": ["Node1", "Node2"],  # 对应的task graph节点
            }},
            ...(其他全部的不同级别的不同节点对应的subgraph。注意是不同层的全部node！)
        }}

        ---
        ### 输入材料
        以下为执行任务所需的材料，请基于这些内容完成任务并返回结果：

        #### 材料（二）、现在的task graph、intent tree以及对应的subgraph 
        {{{previous_result}}}

        #### 材料（三）用户当前输入的prompt 
        {{{current_prompt}}}

        #### 材料（四）当前生成的代码 
        {{{current_response}}}

        #### 材料（五）历史prompt记录 
        {{{history_prompts}}}
        
        ---
        ### 返回格式
        请务必严格按照以下格式返回你的结果：
        
        ```JSON_RESULT
        {{
            "intent_tree": {{
                // 你的intent_tree结果，使用完整的嵌套字典格式
            }},
            "task_graph": {{
                // 你的task_graph结果，包含nodes和links
            }},
            "mapping": {{
                // 你的mapping结果，每个intent节点名称对应的子图
            }}
        }}
        ```
        
        请注意：结果必须包裹在```JSON_RESULT和```之间，且必须是有效的JSON格式，不要添加任何注释。这对于系统自动解析极为重要。
        """

        result = get_llm_response("你是一个超强人工智能，擅长从代码和文本中总结提取结构化信息，尤其是擅长提取intent tree, task graph以及mapping。", prompt)

        return result

    def _save_results(self, result, round_number):
        intent_tree, task_graph, mapping = self._extract_llm_results(result)
        
        # Save the results in a single JSON file
        results = {
            "raw": result,
            "intent_tree": intent_tree,
            "task_graph": task_graph,
            "mapping": mapping
        }
        with open(os.path.join(self.output_folder, f"results_round_{round_number}.json"), 'w') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        return intent_tree, task_graph, mapping

    def _extract_llm_results(self, result):
        # Look for the JSON_RESULT block in the response
        try:
            # Extract the content between ```JSON_RESULT and ```
            start_marker = "```JSON_RESULT"
            end_marker = "```"
            
            start_idx = result.find(start_marker)
            if start_idx == -1:
                # print("Warning: JSON_RESULT marker not found in response")
                # Fall back to API method if structured format not found
                return self._extract_llm_results_using_api(result)
                
            start_idx += len(start_marker)
            end_idx = result.find(end_marker, start_idx)
            
            if end_idx == -1:
                # print("Warning: Closing marker not found in response")
                # Fall back to API method if structured format not found
                return self._extract_llm_results_using_api(result)
                
            json_content = result[start_idx:end_idx].strip()
            parsed_data = json.loads(json_content)
            
            # Extract each component
            intent_tree = parsed_data.get("intent_tree", {})
            task_graph = parsed_data.get("task_graph", {})
            mapping = parsed_data.get("mapping", {})
            
            # Convert to string representation for consistency with expected return format
            return json.dumps(intent_tree, ensure_ascii=False), json.dumps(task_graph, ensure_ascii=False), json.dumps(mapping, ensure_ascii=False)
        
        except json.JSONDecodeError as e:
            # print(f"Error parsing JSON: {e}")
            # Fall back to API method if JSON parsing fails
            return self._extract_llm_results_using_api(result)
        except Exception as e:
            # print(f"Unexpected error during extraction: {e}")
            # Fall back to API method if any other error occurs
            return self._extract_llm_results_using_api(result)

    def _extract_llm_results_using_api(self, result):
        # Original implementation as fallback
        intent_tree = get_llm_response("提取里边intent tree对应的python代码，只返回dict（python可处理的）", result)
        task_graph = get_llm_response("提取task graph对应的python代码，只返回dict（python可处理的）", result)
        mapping = get_llm_response("提取mapping对应的python代码，只返回dict(python可处理的)", result)
        return intent_tree, task_graph, mapping

    def _draw_results(self, intent_tree, task_graph, mapping, round_number):
        # Draw the graphs
        self.drawer.draw_intent_tree(intent_tree, f"intent_tree_round_{round_number}.png")
        self.drawer.draw_task_graph(task_graph, f"task_graph_round_{round_number}.png")
        self.drawer.draw_mapping(intent_tree, task_graph, mapping, f"mapping_round_{round_number}.png")

    def _save_and_draw(self, result, round_number):
        intent_tree, task_graph, mapping = self._save_results(result, round_number)
        self._draw_results(intent_tree, task_graph, mapping, round_number)

def draw_task_graphs_from_json(output_folder, drawer):
    json_files = sorted(glob.glob(os.path.join(output_folder, "results_round_*.json")))
    
    for json_file in json_files:
        with open(json_file, 'r') as f:
            data = json.load(f)
            task_graph_str = data.get("task_graph", "")
            task_graph = eval(task_graph_str.strip("```python\n").strip("\n```"))
            drawer.draw_task_graph(task_graph, os.path.basename(json_file).replace(".json", ".png"))



# Example usage:
if __name__ == "__main__":
    raw_data_folder = "/home/wzhangeb/lancet/dataset/raw_data/web_crawler"
    output_folder = "/home/wzhangeb/lancet/dataset/interaction_output_01"
    if True:
        processor = InteractionProcessor(raw_data_folder, output_folder)
        processor.process_interactions(user_index=1)
    else:
        drawer = GraphDrawer(output_folder)
        draw_task_graphs_from_json(output_folder, drawer)