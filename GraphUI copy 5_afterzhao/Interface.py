import json,re,sys
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel, PeftConfig  # Add this import
import torch
import time
import pprint

sys.path.append('/home/wzhangeb')
# Import the LLM API
from lancet.dataset.LLM_api import get_llm_response, get_llm_response_spark_oneshot
from lancet.Graph_Simplification.rest import complete_mapping_with_internal_links, DataSimplifier
print("All imports are successful")
class Storage:
    def __init__(self):
        self.graph = None
        self.sim_graph = None
        self.intent_tree = None
        self.mapping = None
        self.test = False
        self.baseline = False
        self.old_intent_tree = None
        
        # Model initialization
        self.model_path ="/home/wzhangeb/lancet/slm/results_sft_deepseek_Llama-8B_gpu0/checkpoint-90"
        # self.model_path = "/home/wzhangeb/lancet/slm/audio/results_sft_deepseek_Llama-8B_gpu0/checkpoint-250"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print("Loading model and tokenizer from", self.model_path)
        try:
            # Load the tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            # Load the configuration to get the base model name
            config = PeftConfig.from_pretrained(self.model_path)
            
            # Load the base model with quantization
            print("Loading model with quantization")
            self.model = AutoModelForCausalLM.from_pretrained(
                config.base_model_name_or_path,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True
            )
            
            # Load the fine-tuned LoRA weights
            self.model = PeftModel.from_pretrained(self.model, self.model_path)
            
            # Initialize pipeline
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            print(f"Model and pipeline loaded successfully on {self.device}")
        except Exception as e:
            print(f"\n\nError loading model: {str(e)}")
            self.model = None
            self.tokenizer = None
            self.pipe = None
        
        # data processing
        self.first_round_input_template = """
        我需要你基于用户输入的massage生成intent tree, task graph, mapping.他们具体的定义如下
        
        ## Intent Tree
        意图树是一种层次化的结构，用于表示用户通过对话系统希望达成的目标及其细分的任务。根节点代表总体意图，子节点代表为实现该总体意图所需的各个具体步骤或任务。

        ### 构建方法
        1. **概括用户的总体意图**：分析用户输入，提取出用户的总体目标。
        2. **抽象具体的子任务或要求**：从用户输入中抽象出具体的子任务或要求，并将其组织成树形结构。
        3. **形成树状图**：将这些意图和子意图按层级关系组织起来，形成一个树状图。

        示例
        intent_tree = {{
            "写一个爬虫程序，爬取指定URL的内容并保存到本地": {{
            "爬取文本内容并保存": {{}},
            "爬取图像内容并保存": {{}}
            }}
        }}

        ## Task Graph
        任务图是一种有向图结构，用来展示代码执行过程中的任务流及各任务间的依赖关系。节点代表任务，边代表任务之间的依赖关系，包括数据流向和类型。

        ### 构建方法
        1. **分析代码**：从代码中提取所有需要执行的任务，并为其生成简短描述。
        2. **构建图结构**：使用节点表示每个任务，使用边表示任务之间的依赖关系，并标注数据流动的方向和类型。

        示例：
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

        ## Mapping
        映射是指意图树中的每个节点与任务图中相应子图之间的一对一对应关系。确保每个意图都有明确的任务集来实现它。

        ### 构建方法
        1. **匹配子图节点**：针对意图树中的每个节点，在任务图中找到对应的子图（仅包含直接相关的部分）。
        2. **确保一一对应**：每个意图树节点应唯一对应一个任务图子图，反之亦然。

        示例：
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

        # 请基于下边的User Prompt创建对应的intent tree, task graph, mapping:
        {user_input}"

        
        ## 输出格式如下，按该格式输出一遍即可: 
        ### Intent Tree:
        ```json
        intent_tree
        ```
        ### Task Graph:
        ```json
        task_graph
        ```
        ### Mapping:
        ```json
        mapping
        ```

        # 注意！
        ## 请按照格式要求生成对应的intent tree, task graph, mapping。不用输出其他内容（例如检查和逻辑等），请注意```json```标识的完整性
        ## 这是第一轮，请保持输出的内容尽可能简洁, node数量不要太多。但要保证格式和我给出的示例一致。
        """

        
        # Template for subsequent rounds (includes previous data)
        self.subsequent_round_input_template = """
        我需要你基于用户输入的massage修改上一轮中的intent tree, task graph, mapping.他们具体的定义如下，修改后的结果保持和上一轮一样的格式

        ## Intent Tree（意图树）
        意图树是一种层次化的结构，用于表示用户通过对话系统希望达成的目标及其细分的任务。根节点代表总体意图，子节点代表为实现该总体意图所需的各个具体步骤或任务。

        ### 构建方法
        1. **概括用户的总体意图**：分析用户输入，提取出用户的总体目标。
        2. **抽象具体的子任务或要求**：从用户输入中抽象出具体的子任务或要求，并将其组织成树形结构。
        3. **形成树状图**：将这些意图和子意图按层级关系组织起来，形成一个树状图。

        ## Task Graph（任务图）
        任务图是一种有向图结构，用来展示代码执行过程中的任务流及各任务间的依赖关系。节点代表任务，边代表任务之间的依赖关系，包括数据流动的方向和类型。

        ### 构建方法
        1. **分析代码**：从代码中提取所有需要执行的任务，并为其生成简短描述。
        2. **构建图结构**：使用节点表示每个任务，使用边表示任务之间的依赖关系，并标注数据流动的方向和类型。

        ## Mapping（映射）
        映射是指意图树中的每个节点与任务图中相应子图之间的一对一对应关系。确保每个意图都有明确的任务集来实现它。

        ### 构建方法
        1. **匹配子图节点**：针对意图树中的每个节点，在任务图中找到对应的子图（仅包含直接相关的部分）。
        2. **确保一一对应**：每个意图树节点应唯一对应一个任务图子图，反之亦然。

        # 历史信息
        ### User message:
        {user_input}

        ### Previous intent tree:
        {prev_intent_tree}

        ### Previous task graph:
        {prev_task_graph}

        ### Previous mapping:
        {prev_mapping}
        
        # 注意！请按照格式要求生成对应的intent tree, task graph, mapping。不用输出其他内容（例如检查和逻辑等）。
        # 输出格式如下，按该格式输出一遍即可: 
        ### Intent Tree:
        ```json
        intent_tree
        ```
        ### Task Graph:
        ```json
        task_graph
        ```
        ### Mapping:
        ```json
        mapping
        ```
        
        # 更新时请注意
        ### 变化要求
        1. 请你更新intent tree时候仅更新和用户输入有关的内容，不需要新增其他逻辑，比如突然增加音频或视频处理部分。之后再用户明确说明需要增加某部分内容时，才可以增加这部分内容。graph变化不要太大。
        2. 上一次的task graph是经过用户修改的，当intent tree和graph冲突时，请以task graph为准，如task_graph中没有音频处理部分，但intent tree中有，那么请删除intent tree中的音频处理部分。
        3. 同时更新mapping，确保intent tree中的每个节点都有对应的task graph中的一个或多个节点。
        ### 请注意```json```标识的完整性，仅按格式输出指定内容
        """

        print("The storage is loaded")
    
    def call_model(self, graph, prompt, intent_tree, mapping):
        """
        Call the language model with user prompt, optionally including graph data
        
        Args:
            graph (dict): Graph data with nodes and links, or None if no graph is available
            prompt (str): User prompt/instruction
            
        Returns:
            dict: Model output and response
        """
        if not self.model or not self.tokenizer:
            return {"status": "error", "message": "Model not loaded"}
        
        if self.baseline:
            return
        try:
            # Format the input based on whether a graph is provided or not
            if graph:
                print("Graph is provided")
                # With graph: include graph representation in the input
                input_text = self.subsequent_round_input_template.format(
                    user_input=prompt,
                    prev_intent_tree=intent_tree,
                    prev_task_graph=graph,
                    prev_mapping=mapping
                    )
            else:
                print("Graph is not provided")
                # Without graph: only include the user prompt
                input_text = self.first_round_input_template.format(user_input=prompt)          
            
            # Tokenize input and explicitly move to device
            inputs = self.tokenizer(input_text, return_tensors="pt").to(self.device)
            print("Input text tokenized")

            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=2800,  # Adjust as needed
                    temperature=0.95,
                    num_return_sequences=1
                )
            print("Response generated")

            # Decode generated text
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
            
            # Extract response after </think> tag if present
            if "</think>" in generated_text:
                response = generated_text.split("</think>")[1].strip()
            else:
                response = generated_text.replace(input_text, "").strip()
            
            print("Response extracted\n\n", response)
            return {
                "status": "success", 
                "full_output": generated_text,
                "response": response,
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def updata_trible(self, prompt):
        self.old_intent_tree = self.intent_tree
        print("Updating intent_tree, task_graph, and mapping based on user prompt")
        print("Prompt:", prompt)
        print("Current intent_tree:", self.intent_tree)
        print("Current task_graph:", self.graph)
        print("Current mapping:", self.mapping)

        try:
            # Add retry mechanism for extracting JSON data
            max_attempts = 3
            attempt = 0
            success = False
            
            while not success and attempt < max_attempts:
                attempt += 1
                model_result = self.call_model(
                    graph=self.graph,
                    prompt=prompt,
                    intent_tree=self.intent_tree,
                    mapping=self.mapping
                )
                print("We called the model")

                response_text = model_result.get("response", "")
                try:
                    # TODO: Extract JSON data from the response text modify it.
                    # Define simplified regex patterns for the fixed format
                    intent_tree_pattern = r'### Intent Tree:\s*```json\s*(\{.*?\})\s*```'
                    task_graph_pattern = r'### Task Graph:\s*```json\s*(\{.*?\})\s*```'
                    mapping_pattern = r'### Mapping:\s*```json\s*(\{.*?\})\s*```'
                    
                    # Extract JSON from the response text using the new patterns
                    intent_tree_match = re.search(intent_tree_pattern, response_text, re.DOTALL)
                    task_graph_match = re.search(task_graph_pattern, response_text, re.DOTALL)
                    mapping_match = re.search(mapping_pattern, response_text, re.DOTALL)
                    
                    # Check if all components were found
                    if not all([intent_tree_match, task_graph_match, mapping_match]):
                        raise ValueError("Could not extract all required components from model response")
                        
                    # Extract the JSON strings
                    intent_tree_json = intent_tree_match.group(1)
                    task_graph_json = task_graph_match.group(1)
                    mapping_json = mapping_match.group(1)
                    
                    print(f"Attempt {attempt}/{max_attempts}: Extracted JSON data from response")
                    print("Intent Tree:", intent_tree_json)
                    print("Task Graph:", task_graph_json)
                    print("Mapping:", mapping_json)

                    # Parse the JSON data
                    self.intent_tree = json.loads(intent_tree_json)
                    self.graph = json.loads(task_graph_json)
                    self.mapping = json.loads(mapping_json)
                    
                    print(f"Attempt {attempt}/{max_attempts}: Structured data successfully extracted and updated.")
                    success = True
                except Exception as e:
                    print(f"Attempt {attempt}/{max_attempts} failed: {e}")
                    if attempt < max_attempts:
                        print(f"Retrying in 1 second...")
                        time.sleep(1)  # Wait before retrying
            
            if success:
                print("Structured data (intent_tree, task_graph, mapping) successfully extracted and updated.")
            else:
                print(f"Failed to extract and parse JSON after {max_attempts} attempts.")
        except Exception as e:
            print(f"Error in retry mechanism: {e}")
        

    def call_print(self):
        self.test+=1
        print("Interface.py loaded and tese is called", self.test)
    
    def graph_zoom(self, focus_nodes):
        """
        Zoom in on a specific set of nodes in the graph using DataSimplifier
        
        Args:
            focus_nodes (list): List of node IDs to focus on
        
        Returns:
            dict: Subgraph containing only the specified nodes and their connections
        """
        # Check if required components are available
        if not self.graph or not self.intent_tree or not self.mapping:
            print("Warning: Missing required components for graph simplification")
            return None
        
        # First, complete the mapping with internal links

        enhanced_mapping = complete_mapping_with_internal_links(self.mapping, self.graph)
        
        # Update the mapping with the enhanced version
        self.mapping = enhanced_mapping
        
        # Initialize the simplifier with our data
        simplifier = DataSimplifier(self.intent_tree, self.graph, self.mapping)
        
        # Perform the simplification based on the focus nodes
        simplifier.simplify(focus_nodes)
        
        # Get and return the simplified graph
        simplified_graph = simplifier.get_simplified_graph()
        
        # Update the sim_graph in the storage instance
        self.sim_graph = simplified_graph
        
        # Store the simplifier for future subgraph queries
        self.simplifier = simplifier
        
        return simplified_graph
    
    def graph_convert(self, frontend_graph):
        """
        将前端图形格式转换为后端格式
        
        Args:
            frontend_graph: 前端格式的图形数据 (包含 nodes 和 edges/links)
            
        Returns:
            dict: 后端格式的图形数据 (包含 nodes 和 links)
        """
        if not frontend_graph:
            return None
            
        backend_graph = {
            "nodes": [],
            "links": []
        }
        
        # 转换节点
        if "nodes" in frontend_graph:
            for node in frontend_graph["nodes"]:
                backend_node = {
                    "id": node["id"],
                    "description": node.get("label") or node.get("description", "")
                }
                backend_graph["nodes"].append(backend_node)
        
        # 转换边 (edges -> links)
        if "edges" in frontend_graph:
            for edge in frontend_graph["edges"]:
                # 处理source和target可能是对象的情况
                source = edge["source"]["id"] if isinstance(edge["source"], dict) else edge["source"]
                target = edge["target"]["id"] if isinstance(edge["target"], dict) else edge["target"]
                
                backend_link = {
                    "source": source,
                    "target": target,
                    "type": edge.get("label", "")
                }
                backend_graph["links"].append(backend_link)
        # 如果没有edges但有links，直接使用links
        elif "links" in frontend_graph:
            for link in frontend_graph["links"]:
                # 处理source和target可能是对象的情况
                source = link["source"]["id"] if isinstance(link["source"], dict) else link["source"]
                target = link["target"]["id"] if isinstance(link["target"], dict) else link["target"]
                
                backend_link = {
                    "source": source,
                    "target": target,
                    "type": link.get("type", "")
                }
                backend_graph["links"].append(backend_link)
        
        # 打印转换后的图结构
        print(f"Converted graph: {len(backend_graph['nodes'])} nodes, {len(backend_graph['links'])} links")
        
        return backend_graph
    
    def generate_graph(self, prompt):
        if self.test:
            self.graph = {
                "nodes": [
                    {"id": "Node1", "description": "发起HTTP请求以获取目标网页的内容"},
                    {"id": "Node2", "description": "使用BeautifulSoup解析HTML"},
                    {"id": "Node3", "description": "提取微信公众号文章中的正文内容"},
                    {"id": "Node4", "description": "保存包含图片文件名的Markdown内容到 content.md"},
                    {"id": "Node5", "description": "查找微信公众号文章中的所有图像"}
                ],
                "links": [
                    {"source": "Node1", "target": "Node2", "type": "parse"},
                    {"source": "Node2", "target": "Node3", "type": "extractText"},
                    {"source": "Node3", "target": "Node4", "type": "add"},
                    {"source": "Node2", "target": "Node5", "type": "findImages"}
                ]
            }
            self.sim_graph= {
                "nodes": [
                    {"id": "Node1", "description": "发起HTTP请求以获取目标网页的内容"},
                    {"id": "Node2", "description": "使用BeautifulSoup解析HTML"},
                    {"id": "Node6", "description": "合并的节点"},
                ],
                "links": [
                    {"source": "Node1", "target": "Node2", "type": "parse"},
                    {"source": "Node2", "target": "Node6", "type": "extractText"},
                ]
            }
        else:
            self.updata_trible(prompt=prompt)
            print("storage_instance.old_intent_tree: ", storage_instance.old_intent_tree)
            if storage_instance.old_intent_tree==None:
                self.sim_graph = self.graph
            else:
                node_list = self.diff_intent_tree()
                print("intent tree")
                pprint.pprint(storage_instance.intent_tree)
                print("mapping")
                pprint.pprint(storage_instance.mapping)
                print("graph")
                pprint.pprint(storage_instance.graph)
                print("Node list:", node_list)
                self.sim_graph = self.graph_zoom(focus_nodes=node_list)
                print("Simplified graph:")
                pprint.pprint(self.sim_graph)

    def diff_intent_tree(self):
        """
        Compare the new intent_tree with the old_intent_tree and return node names
        that exist in the new tree but weren't in the old tree, or have changed.
        
        Returns:
            list: A list of node names from the new intent tree that need focus
        """
        def extract_keys(d):
            """提取字典中所有层级的键名"""
            keys = set()
            for k, v in d.items():
                keys.add(k)
                if isinstance(v, dict):
                    keys.update(extract_keys(v))
            return keys

        
        # 提取所有键
        keys_old = list(extract_keys(storage_instance.old_intent_tree)) if storage_instance.old_intent_tree else []
        keys_new = list(extract_keys(storage_instance.intent_tree))

        # 找出new中独有的键
        unique_to_new = [item for item in keys_new if item not in keys_old]
            
        if len(unique_to_new) != 0:    
            return list(unique_to_new)
        else:
            return list(storage_instance.intent_tree.keys())
        
# Create a global instance of Storage
storage_instance = Storage()

def save_chat_history(user_message, ai_response):
    try:
        history_entry = {
            "userMessage": user_message,
            "aiResponse": ai_response
        }
        return {"status": "success", "message": "历史记录保存成功", "data": history_entry}
    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")
        return {"status": "error", "message": str(e)}
    
def GraphCallFunction(old_graph, user_prompt):
    try:
        print(f"\n\nGraphCallFunction:\n {old_graph}\n,\n {user_prompt}\n")
        
        # 先生成新图
        storage_instance.graph = storage_instance.graph_convert(old_graph)
        storage_instance.generate_graph(user_prompt)
        new_graph = storage_instance.graph
        sim_graph = storage_instance.sim_graph
        
        # Get changed nodes from diff_intent_tree
        changed_nodes = storage_instance.diff_intent_tree()
        
        return {
            "status": "success", 
            "graph": new_graph, 
            "sim_graph": sim_graph,
            "intent_tree": storage_instance.intent_tree,
            "changed_nodes": changed_nodes
        }
            
    except Exception as e:
        print(f"GraphCallFunction error: {str(e)}")
        return {"status": "error", "message": str(e)}

def call_LLM(chat_history, new_graph):
    """
    处理聊天历史和图形数据，生成AI回复
    
    Args:
        chat_history: 聊天历史记录
        new_graph: 当前图形数据
        
    Returns:
        dict: 包含AI回复的结果
    """
    try:
        print(f"call_LLM: received chat_history and new_graph")
        
        # 检查图形格式是否有效
        if not new_graph:
            print("Warning: No graph data received in call_LLM")
            new_graph = storage_instance.graph  # 使用存储的图形数据作为备份
            if not new_graph:
                return {"status": "error", "message": "No valid graph available"}
        else:
            # 使用graph_convert确保图形格式统一
            new_graph = storage_instance.graph_convert(new_graph)
        
        print(f"new_graph: {new_graph}")

        # 获取当前轮用户输入（最后一条用户消息）
        current_user_input = None
        for message in reversed(chat_history):
            if message.get('sender') == 'user':
                current_user_input = message.get('text')
                break
        
        if not current_user_input:
            return {"status": "error", "message": "No user input found in chat history"}
            
        print(f"current_user_input: {current_user_input}")
        
        # 格式化整个聊天历史作为上下文
        history_text = "历史对话:\n"
        for message in chat_history:
            role = "用户" if message.get('sender') == 'user' else "助手"
            history_text += f"{role}: {message.get('text', '')}\n"
        
        # 构建系统提示词
        system_prompt = """You are a useful AI"""
        
        # 构建用户提示词，包含历史和当前要求
        user_prompt = f"{history_text}\n\n"
        user_prompt += f"用户当前输入: {current_user_input}\n\n"
        if storage_instance.baseline:
            pass
        else:
            user_prompt += f"任务图:\n{json.dumps(new_graph, indent=2, ensure_ascii=False)}\n\n"
            user_prompt += "你需要基于上述任务图中描述的任务执行逻辑和子任务完成和用户需求，生成完整的代码实现。请确保代码可以实际运行并满足用户需求。同时请你给出代码执行的结果"
        
        # 调用Spark API进行单次调用
        print("Calling LLM to generate code...")
        print(f"system_prompt: {system_prompt}")
        print(f"user_prompt: {user_prompt}")
        if False:
            response = """根据任务图要求，我提供以下可运行的Python代码实现微信公众号文章抓取和内容保存功能
```python 
# 打开指定的文本文件
with open('example.txt', 'r', encoding='utf-8') as file:
    # 读取文件的所有行
    lines = file.readlines()

# 遍历每一行，并添加行号后打印
for index, line in enumerate(lines, start=1):
    # 打印带有行号的文本
    print(f"{index}: {line.strip()}")

# 提示用户脚本执行完毕
print("文件处理完成！")
```
关键实现说明： 1. **网络请求优化**： - 使用真实浏览器的User-Agent头 - 自动处理编码问题 - 支持data-src和src两种图片属性 2. **图片处理**： - 自动创建images目录 - 使用MD5哈希生成唯一文件名 - 同时支持微信特有的data-src属性 - 错误处理下载失败的图片 3. **内容提取**： - 精准定位微信正文区域（class="rich_media_content"） - 自动转换HTML图片为本地路径 - 保留Markdown兼容格式 4. **输出结果**： - 生成标准Markdown文件 - 保持标题层级结构 - 本地图片相对路径存储 使用方法： 1. 安装依赖：`pip install requests beautifulsoup4` 2. 替换代码中的article_url为实际文章地址 3. 运行脚本即可生成： - content.md（包含格式化内容） - images/目录（存储所有图片） 注意事项： - 需要真实微信公众号文章URL - 部分网站可能需要添加cookie信息 - 图片下载失败会自动跳过并提示 - 确保有网络连接和写入权限 这个实现严格遵循任务图的流程设计，每个节点对应代码中的具体段落，并通过链接关系保持处理顺序，完整实现了从网页抓取到本地保存的全流程。"""
        else:
            response = get_llm_response_spark_oneshot(system_prompt, user_prompt)
        
        print(f"LLM generated response successfully")
        
        return {"status": "success", "response": response}
    
    except Exception as e:
        print(f"call_LLM error: {str(e)}")
        return {"status": "error", "message": str(e)}

def graph_update(modified_sim_graph, new_graph):
    """
    基于修改后的简化图更新完整图
    
    Args:
        modified_sim_graph: 修改后的简化图
        new_graph: 原始新图
        
    Returns:
        dict: 包含更新后的图形
    """
    try:
        print(f"graph_update: received modified_sim_graph and new_graph")
        
        # 检查输入是否有效
        if not modified_sim_graph or not new_graph:
            print("Warning: Missing modified_sim_graph or new_graph")
            if new_graph:
                return {"status": "success", "graph": new_graph}
            else:
                return {"status": "error", "message": "Missing required graph data"}
        
        print("We enter the graph_update")

        # 转换格式
        backend_modified_sim_graph = storage_instance.graph_convert(modified_sim_graph)
        backend_new_graph = storage_instance.graph_convert(new_graph)
        
        # 完全以传入的new_graph作为storage_instance.graph，不进行合并
        storage_instance.graph = backend_new_graph
        
        # 更新storage_instance中的简化图
        storage_instance.sim_graph = backend_modified_sim_graph
        
        # 打印返回的图形以便调试
        print(f"Updated storage with new graph: {len(backend_new_graph.get('nodes', []))} nodes and {len(backend_new_graph.get('links', []))} links")
        
        # 确保返回新图
        return {"status": "success", "graph": storage_instance.graph}
    except Exception as e:
        print(f"graph_update error: {str(e)}")
        return {"status": "error", "message": str(e)}

def save_chat_history(user_message, ai_response):
    try:
        history_entry = {
            "userMessage": user_message,
            "aiResponse": ai_response
        }
        return {"status": "success", "message": "历史记录保存成功", "data": history_entry}
    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def graph_extension(node_id):
    """
    Expand a merged node in the simplified graph to show its full subgraph
    
    Args:
        node_id (str): ID of the merged node to expand
        
    Returns:
        dict: Subgraph containing all nodes and links for the intent represented by the merged node
    """
    # try:
    print(f"graph_extension: expanding node {node_id}")
    print(storage_instance.mapping)
    print(storage_instance.graph)
    # 1. Get enhanced mapping with internal links
    enhanced_mapping = complete_mapping_with_internal_links(storage_instance.mapping, storage_instance.graph)
    
    print("Enhanced mapping:")
    print(enhanced_mapping)

    print("We have finished the vis")

    # 2. Extract the intent name from the node description
    intent_name = None
    for node in storage_instance.sim_graph.get("nodes", []):
        if node["id"] == node_id:
            description = node.get("description", "")
            if "Merged nodes from intent:" in description:
                intent_name = description.split("Merged nodes from intent:")[1].strip()
            break

    print(f"Extracted intent name: {intent_name}")
    
    if not intent_name:
        print(f"Warning: Could not extract intent name from node {node_id}")
        return {"status": "error", "message": f"Could not extract intent name from node {node_id}"}
    
    # 3. Use the enhanced mapping to get the subgraph for this intent
    if intent_name not in enhanced_mapping:
        print(f"Warning: Intent '{intent_name}' not found in mapping")
        return {"status": "error", "message": f"Intent '{intent_name}' not found in mapping"}
    
    
    subgraph = enhanced_mapping[intent_name]
    print(f"Subgraph for intent '{intent_name}':{subgraph}")

    def change_subgraph_format_intograph_format_with_labels(thesubgraph, thegraph):
        """
        Convert the subgraph format to the graph format with labels
        
        Args:
            subgraph: Subgraph data in simplified format
            graph: Full graph data with nodes and links
        
        Returns:
            dict: Subgraph data in full graph format with labels
        """
        # Initialize the new subgraph
        new_subgraph = {"nodes": [], "links": []}
        
        # Extract the node IDs from the subgraph
        node_ids = thesubgraph.get("nodes", [])
        
        # Extract the nodes and links from the full graph
        full_nodes = thegraph.get("nodes", [])
        full_links = thegraph.get("links", [])
        
        # Create a mapping of node IDs to node descriptions
        node_mapping = {node["id"]: node["description"] for node in full_nodes}
        
        # Add nodes to the new subgraph
        for node_id in node_ids:
            if node_id in node_mapping:
                new_subgraph["nodes"].append({
                    "id": node_id,
                    "description": node_mapping[node_id]
                })
        
        # Add links to the new subgraph
        for link in full_links:
            if link["source"] in node_ids and link["target"] in node_ids:
                new_subgraph["links"].append(link)
        
        return new_subgraph
    
    # Convert the subgraph format to the graph format with labels
    subgraph = change_subgraph_format_intograph_format_with_labels(subgraph, storage_instance.graph)
    print(subgraph)
    # print(f"Expanded node {node_id} to subgraph with {len(subgraph.nodes)} nodes and {len(links)} links")
    return {"status": "success", "subgraph": subgraph}
        
    # except Exception as e:
    #     print(f"graph_extension error: {str(e)}")
    #     return {"status": "error", "message": str(e)}

def modify(user_input, new_graph):
    """
    Process user input to modify the graph, intent tree, and mapping using an LLM
    
    Args:
        user_input: Text entered by the user
        new_graph: Current graph to modify
        
    Returns:
        dict: Status, modified graph and simplified graph
    """
    try:
        print(f"modify: received user_input: {user_input}")
        
        # Save the current intent_tree to old_intent_tree
        storage_instance.old_intent_tree = storage_instance.intent_tree
        
        # Convert graph to backend format if needed
        backend_graph = storage_instance.graph_convert(new_graph) if new_graph else None
        
        # Prepare a system prompt for the LLM that requests all three components
        system_prompt = """
        你是一个擅长处理graph或tree型结构的ai，可以基于我的需求非常好的完成intent tree， task graph以及mapping的更新
        """
        
        
        # Prepare the user prompt with all components
        user_prompt = f"""
        我需要你基于用户输入的message修改当前的intent tree, task graph, mapping。它们的具体定义如下，修改后的结果保持和当前的一样的格式。
        # 任务：请基于用户输入的内容，更新intent tree, task graph, mapping，保证更新完的task graph可以完成用户指定的内容。
        ## 用户的修改需求:
        {user_input}

        ## 传入内容的定义如下：
        ### Intent Tree（意图树）
        意图树是一种层次化的结构，用于表示用户通过对话系统希望达成的目标及其细分的任务。根节点代表总体意图，子节点代表为实现该总体意图所需的各个具体步骤或任务。

        ### Task Graph（任务图）
        任务图是一种有向图结构，用来展示代码执行过程中的任务流及各任务间的依赖关系。节点代表任务，边代表任务之间的依赖关系，包括数据流动的方向和类型。

        ### Mapping（映射）
        映射是指意图树中的每个节点与任务图中相应子图之间的一对一对应关系。确保每个意图都有明确的任务集来实现它。

        ## 更新时请注意以下事项：
        1. 请你更新intent tree时仅更新和用户输入有关的内容，不需要新增其他逻辑，比如突然增加音频或视频处理部分。之后再用户明确说明需要增加某部分内容时，才可以增加这部分内容。同时graph变化不要太大。
        2. 上一次的task graph是经过用户修改的，当intent tree和graph冲突时，请以task graph为准，如task_graph中没有音频处理部分，但intent tree中有，那么请删除intent tree中的音频处理部分。
        3. 同时更新mapping，确保intent tree中的每个节点都有对应的task graph中的一个或多个节点。

        ### 非必要不对intent tree中无关node进行修改。只对用户意图明确涉及的node进行修改。任务的巨大变化可以对taskgraph进行大幅度变化
        ### 请不要出现两个node互相指向的情况，这样会破坏直观性

        # 历史信息

        ### Previous intent tree:
        {storage_instance.intent_tree}

        ### Previous task graph:
        {backend_graph}

        ### Previous mapping:
        {storage_instance.mapping}
        
        # 输出格式如下，按该格式输出一遍即可: 
        ### Intent Tree:
        ```json
        intent_tree
        ```
        ### Task Graph:
        ```json
        task_graph
        ```
        ### Mapping:
        ```json
        mapping
        ```

        """

        try:
            # Add retry mechanism for extracting JSON data
            max_attempts = 3
            attempt = 0
            success = False
            
            while not success and attempt < max_attempts:
                # Call the LLM API with one-shot approach
                print("Calling LLM to modify graph, intent tree, and mapping...")
                llm_response = get_llm_response(system_prompt, user_prompt,model="qwen-plus-latest")
                print("Received response from LLM")
                attempt += 1
                # try:
                #     # Extract the three components from the response using regex patterns
                #     intent_tree_pattern = r'### Intent Tree:\s*```json\s*(\{.*?\})\s*```'
                #     task_graph_pattern = r'### Task Graph:\s*```json\s*(\{.*?\})\s*```'
                #     mapping_pattern = r'### Mapping:\s*```json\s*(\{.*?\})\s*```'
                    
                #     intent_tree_match = re.search(intent_tree_pattern, llm_response, re.DOTALL)
                #     task_graph_match = re.search(task_graph_pattern, llm_response, re.DOTALL)
                #     mapping_match = re.search(mapping_pattern, llm_response, re.DOTALL)

                #     if not all([intent_tree_match, task_graph_match, mapping_match]):
                #         raise ValueError("Could not extract all required components from LLM response")

                #     # Parse the JSON data from each component
                #     intent_tree_json = intent_tree_match.group(1)
                #     task_graph_json = task_graph_match.group(1)
                #     mapping_json = mapping_match.group(1)

                #     print(f"Attempt {attempt}/{max_attempts}: Extracted JSON data from response")
                    
                #     # Update storage instance with the new data
                #     storage_instance.intent_tree = json.loads(intent_tree_json)
                #     storage_instance.graph = json.loads(task_graph_json)
                #     storage_instance.mapping = json.loads(mapping_json)
                    
                #     print(f"Attempt {attempt}/{max_attempts}: Structured data successfully parsed and updated.")
                #     success = True
                #     print("new intent_tree is: ", storage_instance.intent_tree)
                    
                # except Exception as e:
                #     print(f"Attempt {attempt}/{max_attempts} failed: {e}")
                #     if attempt < max_attempts:
                #         print(f"Retrying in 1 second...")
                #         time.sleep(1)  # Wait before retrying
            
                # Extract the three components from the response using regex patterns

                def extract_json_section(text, section_header):
                    # Find all occurrences of the section header
                    header_matches = list(re.finditer(f"{section_header}:\\s*```json\\s*", text, re.DOTALL))
                    if not header_matches:
                        return None
                    
                    # Use only the first occurrence
                    start_match = header_matches[0]
                    start_idx = start_match.end()
                    json_text = text[start_idx:]
                    
                    # Count braces to find complete JSON object
                    brace_count = 0
                    end_idx = 0
                    in_string = False
                    escape_char = False
                    
                    for i, char in enumerate(json_text):
                        if char == '"' and not escape_char:
                            in_string = not in_string
                        elif not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        escape_char = (char == '\\' and not escape_char)
                    
                    return json_text[:end_idx] if end_idx > 0 else None

                # Extract each section using the new function
                intent_tree_json = extract_json_section(llm_response, "### Intent Tree")
                task_graph_json = extract_json_section(llm_response, "### Task Graph")
                mapping_json = extract_json_section(llm_response, "### Mapping")



                # Parse the JSON data if all sections were found
                if all([intent_tree_json, task_graph_json, mapping_json]):
                    intent_tree = json.loads(intent_tree_json)
                    graph = json.loads(task_graph_json)
                    mapping = json.loads(mapping_json)
                    
                    print("\nnew intent_tree is: ")
                    pprint.pprint(intent_tree)
                    print("\nnew graph is: ")
                    pprint.pprint(graph)
                    print("\nnew mapping is: ")
                    pprint.pprint(mapping)
                    
                    # Update storage instance with the new data
                    storage_instance.intent_tree = json.loads(intent_tree_json)
                    storage_instance.graph = json.loads(task_graph_json)
                    storage_instance.mapping = json.loads(mapping_json)
                    
                    print(f"Attempt {attempt}/{max_attempts}: Structured data successfully parsed and updated.")
                    success = True
                else:
                    missing = []
                    if not intent_tree_json: missing.append("Intent Tree")
                    if not task_graph_json: missing.append("Task Graph")
                    if not mapping_json: missing.append("Mapping")
                    print(f"Could not extract the following components: {', '.join(missing)}")

            if not success:
                print(f"Failed to extract and parse JSON after {max_attempts} attempts.")
                return {"status": "error", "message": f"Failed to extract and parse JSON after {max_attempts} attempts."}
            
            # Continue with the rest of the function only if successful
            # Generate a simplified graph based on differences with the old intent tree
            print("old intent tree: \n", storage_instance.old_intent_tree)
            print("new intent tree: \n", storage_instance.intent_tree)
            node_list = storage_instance.diff_intent_tree()
            print("Identified changed nodes:", node_list)
            sim_graph = storage_instance.graph_zoom(focus_nodes=node_list)
            
            # Store the simplified graph in storage_instance
            storage_instance.sim_graph = sim_graph
            
            print(f"Successfully modified all components. Graph now has {len(storage_instance.graph['nodes'])} nodes")
            print(f"Simplified graph has {len(sim_graph['nodes'])} nodes")
            
            # Return both graphs for UI update
            return {
                "status": "success", 
                "graph": storage_instance.graph,
                "sim_graph": sim_graph
            }
        
        except Exception as e:
            print(f"Error in retry mechanism: {str(e)}")
            return {"status": "error", "message": f"Error in retry mechanism: {str(e)}"}
    
    except Exception as e:
        print(f"modify error: {str(e)}")
        return {"status": "error", "message": str(e)}