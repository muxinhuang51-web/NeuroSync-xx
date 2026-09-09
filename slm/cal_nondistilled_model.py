import os
import torch
import time
import json
import sys
import evaluate
from pathlib import Path
from transformers import pipeline
import numpy as np

# Add lancet to path to import modules
sys.path.append(str(Path(__file__).parent.parent))
from dataset.LLM_api import get_llm_response, get_llm_response_spark_oneshot


# Set available GPUs
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Define local models to test
local_models = {
    "DeepSeek_R1_Distill_Llama_8B": "NousResearch/DeepHermes-3-Llama-3-8B-Preview",
    "DeepSeek_R1_Distill_Qwen_1.5B": "Qwen/Qwen2.5-1.5B",
    "DeepSeek_R1_Distill_Qwen_7B": "Qwen/Qwen2.5-7B",
}

def load_test_prompts(max_samples=2):
    """
    Load multiple test prompts for both English and Chinese.
    Returns a tuple of lists (eng_prompts, chn_prompts) for testing.
    
    Args:
        max_samples: Number of samples to include from each language
    """
    
    full_prompt_temp="""
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
    """
    full_prompt_temp_eng = """
        I need you to generate an intent tree, task graph, and mapping based on the user's input message. Their specific definitions are as follows:

        ## Intent Tree
        The intent tree is a hierarchical structure used to represent the goals a user wishes to achieve through a dialogue system and its subdivided tasks. The root node represents the overall intent, while child nodes represent the specific steps or tasks required to accomplish that intent.

        ### Construction Method
        1. **Summarize the overall user intent**: Analyze the user input to extract the overarching goal.
        2. **Abstract specific subtasks or requirements**: Abstract the specific subtasks or requirements from the user input and organize them into a tree structure.
        3. **Formulate the tree diagram**: Organize these intents and sub-intents hierarchically to form a tree diagram.

        Example:
        intent_tree = {{
            "Write a web crawler program to scrape content from a specified URL and save it locally": {{
                "Scrape text content and save": {{}},
                "Scrape image content and save": {{}}
            }}
        }}

        ## Task Graph
        A task graph is a directed graph structure that shows the flow of tasks during code execution and the dependencies between tasks. Nodes represent tasks, edges represent dependencies between tasks, including data flow direction and type.

        ### Construction Method
        1. **Analyze the code**: Extract all tasks that need to be executed from the code and generate brief descriptions for them.
        2. **Build the graph structure**: Use nodes to represent each task, use edges to indicate dependencies between tasks, and label the direction and type of data flow.

        Example:
        task_graph = {{
            "nodes": [
                {{"id": "Node1", "description": "Initiate HTTP request to get the content of the target webpage"}},
                {{"id": "Node2", "description": "Parse HTML document using BeautifulSoup"}},
                {{"id": "Node3", "description": "Extract text content and save it to a file"}},
                {{"id": "Node4", "description": "Find all image URLs in the HTML document"}},
                {{"id": "Node5", "description": "Download images and save them to the local folder"}},
                {{"id": "Node6", "description": "Create a local folder to save content (if not exist)"}}
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
        Mapping refers to the one-to-one correspondence between each node in the intent tree and the corresponding subgraph in the task graph. Ensure that each intent has a clear set of tasks to achieve it.

        ### Construction Method
        1. **Match subgraph nodes**: For each node in the intent tree, find the corresponding subgraph (only includes directly related parts) in the task graph.
        2. **Ensure one-to-one correspondence**: Each intent tree node should uniquely correspond to one subgraph in the task graph and vice versa.

        Example:
        mapping = {{
            "Write a web crawler program to scrape content from a specified URL and save it locally": {{
                "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6"]
            }},
            "Scrape text content and save": {{
                "nodes": ["Node1", "Node2", "Node3", "Node6"]
            }},
            "Scrape image content and save": {{
                "nodes": ["Node1", "Node2", "Node4", "Node5", "Node6"]
            }}
        }}

        # Please create the corresponding intent tree, task graph, and mapping based on the following User Prompt:
        {user_input}
    """

    input_prompt_eng = [
        "ok so i need to figure out the webpage address of this article i wanna save 😅 can u help me find it? its on wechat and i dont know how to get the link thingy. also can u check if its even possible to open it? like make sure its not blocked or anything 🙏",
        "hey can u help me find the webpage address for the article i wanna save? its on wechat but i cant figure out how to get the exact link 😫 also can u check if the article actually opens properly? thx!",
        "Hey, I need help grabbing a specific article from WeChat and saving it to my computer. Can you first figure out the link to the article? Also, make sure the article is actually accessible. This should be easy, right? 😅",
        "ok so i need to find the webpage for the article i want. can u help me figure out the link? its on wechat but i dont know how to get the exact url thingy. also can u make sure its a page i can actually open? sometimes they dont work 😩",
        "ok so i need to save a wechat article to my computer but first i gotta find it right? can u help me write something that lets me put in the link and checks if its working? like make sure i can open it 🤔",
    ]
    input_prompt_chn = [
        "嗯，我想先搞清楚怎么找到微信文章的链接，你能帮我吗？我试了几次都没成功 😫 顺便看看这个链接能不能打开，我怕它有问题。快点告诉我怎么做吧！",
        "我需要找到微信文章的链接，然后确认是不是我要的文章，能帮我写个代码吗？我觉得应该不难吧！希望快点搞定 😊",
        "我找到了一篇微信文章，链接是https://example.com/article，你能不能帮我确认下这个链接是不是有效的？如果能用的话，下一步咋保存它的内容啊？感觉好复杂哦 😅",
        "嗯，我想先找到微信文章的链接，但我不知道怎么搞，能帮帮我吗？我觉得应该先确定要爬取的文章链接，对吧？然后检查一下能不能打开这篇文章。听起来好像挺简单的，但我不太会写代码啊😅 你可以给我点提示或者直接写出来吗？",
        "嗯，我想先找到微信文章的链接，但是我不知道怎么确定哪个链接是对的？可以帮我想个办法吗？顺便检查一下这个链接能不能打开，急！🙏",
    ]

    # Ensure max_samples is within range
    max_samples = min(max_samples, len(input_prompt_eng), len(input_prompt_chn))
    max_samples = max(1, max_samples)  # Ensure at least 1 sample

    # Create English test prompts
    eng_prompts = []
    for i in range(max_samples):
        eng_prompts.append({
            "userinput": input_prompt_eng[i], 
            "prompt": full_prompt_temp_eng.format(user_input=input_prompt_eng[i])
        })
    
    # Create Chinese test prompts
    chn_prompts = []
    for i in range(max_samples):
        chn_prompts.append({
            "userinput": input_prompt_chn[i], 
            "prompt": full_prompt_temp.format(user_input=input_prompt_chn[i])
        })

    return eng_prompts, chn_prompts


# API prompt templates
prompt_api_gen = """
    请你写一个代码实现下边的内容,
    用户输入: {user_input}
"""

prompt_api_exe = """
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

def test_local_model(model_name, model_path, prompt, max_tokens=3500):
    """Test local model and return response"""
    print(f"\nTesting {model_name}...")
    
    try:
        # Load the model
        device_map = "auto" if torch.cuda.is_available() else "cpu"
        pipe = pipeline("text-generation", model=model_path, device_map=device_map)
        
        # Generate text
        start_time = time.time()
        result = pipe(
            prompt,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
        end_time = time.time()
        
        # Get the generated text
        generated_text = result[0]['generated_text']
        
        # Strip input prompt to get only generated content
        output_text = generated_text[len(prompt):].strip()
        
        print(f"Generation completed in {end_time - start_time:.2f} seconds")
        torch.cuda.empty_cache()
        
        return output_text
        
    except Exception as e:
        print(f"Error testing {model_name}: {e}")
        torch.cuda.empty_cache()
        return f"ERROR: {str(e)}"

def test_api_qwen_two_step(prompt):
    """Test Qwen API with two-step process"""
    print("\nTesting Qwen API (two-step process)...")
    
    try:
        # Step 1: Generate code using userinput
        gen_prompt = prompt_api_gen.format(user_input=prompt['userinput'])
        code_response = get_llm_response("You are a helpful AI assistant.", gen_prompt)
        
        # Step 2: Execute processing
        exe_prompt = prompt_api_exe.format(
            first_round_prompt=prompt['userinput'],
            first_round_response=code_response
        )
        final_response = get_llm_response("You are a helpful AI assistant.", exe_prompt)
        
        print("API processing completed")
        return final_response, code_response
        
    except Exception as e:
        print(f"Error testing API: {e}")
        return f"ERROR: {str(e)}", ""

def extract_json_result(text):
    """Extract JSON result from the text between ```JSON_RESULT and ```"""
    start_marker = "```JSON_RESULT"
    end_marker = "```"
    
    if start_marker in text:
        # Extract content between markers
        start_idx = text.find(start_marker) + len(start_marker)
        end_idx = text.find(end_marker, start_idx)
        
        if end_idx != -1:
            json_str = text[start_idx:end_idx].strip()
            try:
                # Parse JSON
                return json.loads(json_str)
            except:
                print("Error parsing JSON result")
                return None
    
    # If no proper JSON was found
    print("No properly formatted JSON result found")
    return None

def calculate_metrics(reference, hypothesis):
    """Calculate ROUGE and BLEU metrics between reference and hypothesis"""
    # Load metrics
    rouge_metric = evaluate.load("rouge")
    bleu_metric = evaluate.load("bleu")
    
    # Calculate ROUGE
    rouge_results = rouge_metric.compute(
        predictions=[hypothesis],
        references=[reference],
        use_stemmer=True
    )
    
    # Calculate BLEU
    bleu_results = bleu_metric.compute(
        predictions=[hypothesis],
        references=[[reference]]
    )
    
    # Combine metrics
    results = {
        "rouge1": rouge_results["rouge1"],
        "rouge2": rouge_results["rouge2"],
        "rougeL": rouge_results["rougeL"],
        "bleu": bleu_results["bleu"]
    }
    
    return results

def main():
    # Load the first Chinese test prompt
    _, chn_prompts = load_test_prompts(max_samples=1)
    test_prompt = chn_prompts[0]
    
    print(f"Testing with Chinese prompt: {test_prompt['userinput']}")
    
    # Dictionary to store results
    results = {}
    reference_text = None
    
    # Test API first to get reference output
    print("\n======= Testing API (Reference) =======")
    api_output, code_response = test_api_qwen_two_step(test_prompt)
    api_json = extract_json_result(api_output)
    
    if api_json:
        reference_text = json.dumps(api_json, ensure_ascii=False)
        print("\nAPI reference response extracted successfully")
        
        # Store the structured API output
        results["API_Reference"] = {
            "output": api_output,
            "code_response": code_response,
            "structured_output": api_json,
            "metrics": {
                "rouge1": 1.0,  # Perfect match with itself
                "rouge2": 1.0,
                "rougeL": 1.0,
                "bleu": 1.0
            }
        }
    else:
        print("\nFailed to extract structured API output. Using raw output as reference.")
        reference_text = api_output
        
        results["API_Reference"] = {
            "output": api_output,
            "code_response": code_response,
            "structured_output": None,
            "metrics": {
                "rouge1": 1.0,
                "rouge2": 1.0,
                "rougeL": 1.0,
                "bleu": 1.0
            }
        }
    
    # Test local models
    for model_name, model_path in local_models.items():
        print(f"\n======= Testing {model_name} =======")
        model_output = test_local_model(model_name, model_path, test_prompt['prompt'])
        
        model_json = extract_json_result(model_output)
        
        # Calculate metrics against reference
        if model_json and api_json:
            # Compare structured JSON objects
            hypothesis_text = json.dumps(model_json, ensure_ascii=False)
            metrics = calculate_metrics(reference_text, hypothesis_text)
        else:
            # Compare raw text if JSON extraction failed
            metrics = calculate_metrics(reference_text, model_output)
        
        # Store results
        results[model_name] = {
            "output": model_output,
            "structured_output": model_json,
            "metrics": metrics
        }
        
        # Print metrics
        print(f"\nMetrics for {model_name} vs API Reference:")
        print(f"ROUGE-1: {metrics['rouge1']:.4f}")
        print(f"ROUGE-2: {metrics['rouge2']:.4f}")
        print(f"ROUGE-L: {metrics['rougeL']:.4f}")
        print(f"BLEU: {metrics['bleu']:.4f}")
    
    # Save results
    output_path = "/home/wzhangeb/lancet/slm/model_evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to {output_path}")
    
    # Print summary table
    print("\n======= Summary of Results =======")
    print("| Model | ROUGE-1 | ROUGE-2 | ROUGE-L | BLEU |")
    print("| ----- | ------- | ------- | ------- | ---- |")
    
    for model_name, model_data in results.items():
        metrics = model_data["metrics"]
        print(f"| {model_name} | {metrics['rouge1']:.4f} | {metrics['rouge2']:.4f} | {metrics['rougeL']:.4f} | {metrics['bleu']:.4f} |")

if __name__ == "__main__":
    main()

