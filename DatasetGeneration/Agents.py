import sys
from pathlib import Path
import os
import json

# Add the parent directory to sys.path to import from dataset module
sys.path.append(str(Path(__file__).parent.parent))
from dataset.LLM_api import get_llm_response, get_llm_response_spark_oneshot, SparkChat, QwenChat
import time


class CodeGenerationAgents:
    """
    A class containing three different agents that participate in code generation:
    1. DeepseekR1 - Generates code responses based on user prompts
    2. ExecutionAnalyzer - Analyzes and describes code execution results
    3. NoviceUser - Simulates a novice user with vague programming knowledge
    """
    
    def __init__(self, intent_tree, dialog_save_dir="dialog_history", user_index=0):
        # Intent tree will be set by MultiAgentCodeGenSimulator
        self.intent_tree = intent_tree # str information about the task
        
        # Dialog save configuration
        self.dialog_save_dir = dialog_save_dir
        self.user_index = user_index
        
        # Ensure the dialog save directory exists
        os.makedirs(self.dialog_save_dir, exist_ok=True)
        
        # Initialize DeepseekR1 agent session
        self.r1_agent = SparkChat(
            system_prompt="You are an expert programmer. Provide detailed, efficient code solutions with clear explanations.",
            capture_reasoning=True,
            record_reasoning=False
        )
        
        # Initialize Novice User agent session
        self.novice_user_agent = QwenChat(
            system_prompt="""You are simulating a novice computer user with limited programming knowledge.
            Your task is to generate realistic prompts this user would give to an AI coding assistant.
            Respond as if you are the novice user, with appropriate language, emotions, and technical limitations.""",
            model="qwen-max-latest",
            temperature=0.95
        )

    def agent1_code_generator(self, user_prompt):
        """
        Agent 1: DeepseekR1 - Code Generation Assistant
        
        Generates code responses based on user prompts using the DeepseekR1 model.
        This agent specializes in converting vague requirements into concrete code solutions.
        """
        # Enhanced prompt for the code generator
        enhanced_prompt = f"""{user_prompt}"""

        # Get response from DeepseekR1
        result = self.r1_agent.send_message(enhanced_prompt)
        return result["response"]
    
    def agent2_execution_analyzer(self, code):
        """
        Agent 2: Execution Analyzer
        
        Analyzes code execution and returns a natural language description of expected results
        along with updated intent tree showing completed tasks.
        
        Args:
            code (str): The code to analyze
            intent_tree_str (str, optional): String representation of the intent tree.
                                            If None, uses self.intent_tree
        
        Returns:
            tuple: (updated_intent_tree_str, execution_result)
                   - updated_intent_tree_str: String representation of the updated intent tree
                   - execution_result: Description of the code execution results
        """
        # Use provided intent tree string or convert self.intent_tree to string
        intent_tree_to_use = self.intent_tree

        
        # System prompt for the execution analyzer
        system_prompt = """
        You are an expert code execution analyzer with deep knowledge of Python programming.
        Your task is to accurately simulate code execution and describe the outcomes as if the code 
        was actually run on a computer. You will also mark tasks in the intent tree as completed or not.
        
        Your response must be structured in two distinct parts:
        1. EXECUTION_RESULT: A detailed simulation of code execution
        2. UPDATED_INTENT_TREE: The original intent tree with task completion status marked
        
        Structure your response with clear section headers to facilitate parsing.
        """
        
        # Input prompt for the execution analyzer
        input_prompt = f"""
        Please analyze the following Python code and provide two outputs:

        1. EXECUTION_RESULT: Simulate the code execution with these details:
           - What the output would be
           - What files or data would be created or modified
           - Any errors that might occur and why
           - Other important information visible during execution

        2. UPDATED_INTENT_TREE: Take the intent tree below and mark each task as either 
           [COMPLETED] or [NOT COMPLETED] based on what the code would accomplish:

        ORIGINAL INTENT TREE:
        {intent_tree_to_use}

        CODE TO ANALYZE:
        ```python
        {code}
        ```

        FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
        
        ###EXECUTION_RESULT###
        [Your detailed execution simulation here]

        ###UPDATED_INTENT_TREE###
        [The intent tree with [COMPLETED] or [NOT COMPLETED] status added to each task]
        """
        
        # Get execution analysis
        raw_result = get_llm_response_spark_oneshot(system_prompt, input_prompt, capture_reasoning=True)
        
        # Parse the result to extract execution result and updated intent tree
        try:
            # Split by section headers
            parts = raw_result.split("###EXECUTION_RESULT###")
            if len(parts) < 2:
                # Try alternative format if the first split doesn't work
                parts = raw_result.split("EXECUTION_RESULT:")
            
            if len(parts) >= 2:
                second_part = parts[1]
                sections = second_part.split("###UPDATED_INTENT_TREE###")
                if len(sections) < 2:
                    sections = second_part.split("UPDATED_INTENT_TREE:")
                
                if len(sections) >= 2:
                    execution_result = sections[0].strip()
                    updated_intent_tree = sections[1].strip()
                    self.intent_tree = updated_intent_tree
                    return updated_intent_tree, execution_result
        
            # If we reach here, the parsing failed - try a different approach
            if "EXECUTION_RESULT" in raw_result and "UPDATED_INTENT_TREE" in raw_result:
                # Find the positions of the headers
                exec_pos = raw_result.find("EXECUTION_RESULT")
                tree_pos = raw_result.find("UPDATED_INTENT_TREE")
                
                if exec_pos < tree_pos:
                    # Normal order
                    execution_result = raw_result[exec_pos+len("EXECUTION_RESULT"):tree_pos].strip()
                    updated_intent_tree = raw_result[tree_pos+len("UPDATED_INTENT_TREE"):].strip()

                    # Remove any leading colons or hash symbols
                    execution_result = execution_result.lstrip(":#").strip()
                    updated_intent_tree = updated_intent_tree.lstrip(":#").strip()
                    self.intent_tree = updated_intent_tree
                    return updated_intent_tree, execution_result
                
        except Exception as e:
            print(f"Error parsing execution analyzer result: {e}")
        
        # Fallback: return the raw result for both outputs if parsing fails
        return raw_result, raw_result
    
    def agent3_novice_user(self, execution_result):
        """
        Agent 3: Novice User
        
        Simulates a novice programmer with limited technical knowledge who provides vague
        and sometimes inconsistent requirements.
        
        Args:
            intent_progress (str): String representation of the current intent tree progress
            execution_result (str): Description of the code execution result from Agent 2
            
        Returns:
            str: The novice user's next prompt based on the intent progress and execution results
        """
        
        intent_progress = self.intent_tree

        # System prompt for the novice user simulator
        system_prompt = """
        You are simulating a novice computer user who has very limited programming knowledge.
        Your task is to generate the next prompt this user would give to an AI coding assistant.

        IMPORTANT: Your response must ONLY contain the generated user prompt text, with no additional commentary, explanations, or formatting.
        """

        # Input prompt for the novice user simulator with reinforced role characteristics and rules
        input_prompt = f"""
        ROLE: You are simulating a NOVICE USER with limited programming knowledge. You must think and write like someone who doesn't understand programming concepts well.

        INTENT TREE PROGRESS:
        {intent_progress}

        PREVIOUS CODE EXECUTION RESULT:
        {execution_result if execution_result else "No previous code execution."}

        YOUR CHARACTERISTICS AS A NOVICE USER:
        - You use everyday language, not technical terms
        - You write short, often unclear messages
        - You get frustrated easily when things don't work
        - You jump between requirements without completing previous ones
        - You have unrealistic expectations about what's easy to code
        - You repeat yourself with slight changes when not satisfied
        - You use casual language, sometimes with typos or emojis
        - You show strong emotions (excitement or disappointment)
        - You talk to the AI as if it were a person with feelings

        YOUR NEXT PROMPT RULES:
        1. ONLY focus on 1-2 incomplete tasks from the intent tree and solve intent tree tasks in order.
        2. ALWAYS complete higher-level tasks before moving to lower ones
        3. You MAY jump between tasks at the same level
        4. If the code didn't meet your expectations, REPHRASE your request differently
        5. Keep your prompt SHORT and CONVERSATIONAL (like a real novice would)
        6. SOMETIMES include typos, casual expressions, or emotional reactions
        7. If your requests repeatedly fail, gradually become more formal and professional in your writing style. Reset to casual if the node is successful.

        GOAL: Generate a prompt that will lead the coding assistant to implement python code that completes tasks from the intent tree.

        OUTPUT FORMAT REQUIREMENTS:
        - Your response must ONLY contain the raw user prompt text
        - DO NOT include any additional commentary, explanations, or formatting
        - DO NOT include quotes, prefixes like "User:", headers, or footers
        - DO NOT explain your reasoning or thought process
        - JUST provide the exact text the novice user would type

        Now, generate ONLY the exact prompt this novice user would send to the coding assistant:
        PLEASE GENERATE THE PROMPT IN CHINESE!!!
        """

        # Get novice user's next prompt using the dialog-based QwenChat
        response = self.novice_user_agent.send_message(input_prompt)
        
        # Clean up the response to ensure we only get the user prompt
        cleaned_response = response["response"].strip()
        
        # Remove "User:" prefix if present
        if cleaned_response.lower().startswith("user:"):
            cleaned_response = cleaned_response[5:].strip()
        
        # Remove quotes if the entire message is enclosed in them
        if (cleaned_response.startswith('"') and cleaned_response.endswith('"')) or \
           (cleaned_response.startswith("'") and cleaned_response.endswith("'")):
            cleaned_response = cleaned_response[1:-1].strip()
            
        return cleaned_response

    def access_dialog_history(self, filename=None):
        """
        Access the dialog history of the r1_agent and save it to a JSON file.
        
        Args:
            filename (str, optional): Name of the file to save the dialog.
                                      If None, uses the user_index for naming.
            Always set None to save the dialog history.
                                      
        Returns:
            dict: The formatted dialog history.
        """
        # Get history from r1_agent
        history = self.r1_agent.get_history()
        
        # Format the dialog according to the required structure
        dialogue = []
        
        # Process messages in pairs (user and assistant)
        for i in range(0, len(history), 2):
            if i+1 < len(history):  # Make sure we have both user and assistant messages
                user_message = history[i]
                assistant_message = history[i+1]
                
                if user_message['role'] == 'user' and assistant_message['role'] == 'assistant':
                    dialogue_pair = {
                        "user_input": user_message['content'],
                        "llm_output": assistant_message['content']
                    }
                    dialogue.append(dialogue_pair)
        
        # Create the complete dialog structure
        dialog_data = {
            "user_index": self.user_index,
            "dialogue": dialogue
        }
        
        # If filename is not provided, use the user_index for naming
        if filename is None:
            filename = f"user_{self.user_index}.json"
        
        # Ensure the filename has .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Create the full file path
        file_path = os.path.join(self.dialog_save_dir, filename)
        
        # Save the dialog to the JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dialog_data, f, indent=4, ensure_ascii=False)
        
        # print(f"Dialog history saved to {file_path}")
        
        return dialog_data
    
if __name__ == "__main__":
    
    # Test intent tree for web crawler task
    intent_tree = {
        '收集微信公众号文章的内容并整理成文件': {
            '获取文章的所有图片和文字': {
                '保存所有图片': {
                    '找到文章中的所有图片': {}, 
                    '将图片按顺序保存下来': {}
                }, 
                '保存所有文字在原文顺序中': {
                    '保存标题': {
                        '标记主标题': {}, 
                        '标记不同级别的小标题分别保存': {}
                    }, 
                    '保存正文内容': {}
                }
            }, 
            '将图片和文字整理成一个文件': {
                '选择合适的文件格式': {
                    '决定使用文档格式还是网页格式': {}
                }, 
                '确保图片和文字排列整齐': {
                    '按原文顺序插入图片和文字': {}, 
                    '调整排版使其易读': {}
                }
            }, 
            '检查并确认最终文件': {
                '查看文件是否完整': {
                    '确认所有图片都在': {}, 
                    '确认所有文字无遗漏': {}
                }, 
                '确保文件可以正常打开和阅读': {}
            }
        }
    }
    
    print("=== Testing CodeGenerationAgents ===")
    
    # Initialize the agents with a custom save directory and user index
    start_time = time.time()
    agents = CodeGenerationAgents(
        intent_tree=intent_tree,
        dialog_save_dir="webcrawler_dialogs",
        user_index=1
    )
    init_time = time.time() - start_time
    print(f"Agents initialized successfully. (Time: {init_time:.2f}s)")
    
    # Step 1: Get a user query from the novice user agent
    print("\n=== Step 1: Novice User Agent ===")
    start_time = time.time()
    user_query = agents.agent3_novice_user(None)
    user_query_time = time.time() - start_time
    print(f"User Query: {user_query}")
    print(f"Time taken: {user_query_time:.2f}s")
    
    # Step 2: Generate code response with the code generator agent
    print("\n=== Step 2: Code Generator Agent ===")
    start_time = time.time()
    code_response = agents.agent1_code_generator(user_query)
    code_gen_time = time.time() - start_time
    print("Code Generator Response:")
    print("------------------------")
    print(code_response[:300] + "..." if len(code_response) > 300 else code_response)
    print("------------------------")
    print(f"Time taken: {code_gen_time:.2f}s")
    
    # Step 3: Analyze the code execution with the execution analyzer
    print("\n=== Step 3: Execution Analyzer Agent ===")
    start_time = time.time()
    updated_intent, execution_result = agents.agent2_execution_analyzer(code_response)
    execution_time = time.time() - start_time
    print("Updated Intent Tree (excerpt):")
    print("--------------------------")
    print(updated_intent[:200] + "..." if len(updated_intent) > 200 else updated_intent)
    print("--------------------------")
    print("\nExecution Result (excerpt):")
    print("---------------------")
    print(execution_result[:200] + "..." if len(execution_result) > 200 else execution_result)
    print("---------------------")
    print(f"Time taken: {execution_time:.2f}s")





    # Step 1: Get a user query from the novice user agent
    print("\n=== Step 1: Novice User Agent ===")
    start_time = time.time()
    user_query = agents.agent3_novice_user(execution_result)
    user_query_time = time.time() - start_time
    print(f"User Query: {user_query}")
    print(f"Time taken: {user_query_time:.2f}s")
    
    # Step 2: Generate code response with the code generator agent
    print("\n=== Step 2: Code Generator Agent ===")
    start_time = time.time()
    code_response = agents.agent1_code_generator(user_query)
    code_gen_time = time.time() - start_time
    print("Code Generator Response:")
    print("------------------------")
    print(code_response[:300] + "..." if len(code_response) > 300 else code_response)
    print("------------------------")
    print(f"Time taken: {code_gen_time:.2f}s")
    
    # Step 3: Analyze the code execution with the execution analyzer
    print("\n=== Step 3: Execution Analyzer Agent ===")
    start_time = time.time()
    updated_intent, execution_result = agents.agent2_execution_analyzer(code_response)
    execution_time = time.time() - start_time
    print("Updated Intent Tree (excerpt):")
    print("--------------------------")
    print(updated_intent[:200] + "..." if len(updated_intent) > 200 else updated_intent)
    print("--------------------------")
    print("\nExecution Result (excerpt):")
    print("---------------------")
    print(execution_result[:200] + "..." if len(execution_result) > 200 else execution_result)
    print("---------------------")
    print(f"Time taken: {execution_time:.2f}s")
    
    # Step 4: Save the dialog history
    print("\n=== Step 4: Saving Dialog History ===")
    start_time = time.time()
    dialog_data = agents.access_dialog_history()
    save_time = time.time() - start_time
    
    # print saved dialog structure
    print("\nSaved Dialog Structure:")
    print(f"- User Index: {dialog_data['user_index']}")
    print(f"- Number of Dialog Turns: {len(dialog_data['dialogue'])}")
    print(f"- First Turn User Input (excerpt): {dialog_data['dialogue'][0]['user_input'][:100]}..." 
          if len(dialog_data['dialogue']) > 0 and len(dialog_data['dialogue'][0]['user_input']) > 100 
          else "- No dialog turns yet")
    
    print(f"\nDialog saved to: webcrawler_dialogs/user_1.json")
    print(f"Time taken: {save_time:.2f}s")
    
    # print total time summary
    print("\n=== Time Summary ===")
    print(f"Initialization time: {init_time:.2f}s")
    print(f"Novice User Agent time: {user_query_time:.2f}s")
    print(f"Code Generator Agent time: {code_gen_time:.2f}s")
    print(f"Execution Analyzer Agent time: {execution_time:.2f}s")
    print(f"Dialog Save time: {save_time:.2f}s")
    print(f"Total time: {init_time + user_query_time + code_gen_time + execution_time + save_time:.2f}s")
