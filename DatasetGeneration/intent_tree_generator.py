import sys
import os
import json
from pathlib import Path

# Add the parent directory to sys.path to import from dataset module
sys.path.append(str(Path(__file__).parent.parent))
from dataset.LLM_api import get_llm_response, get_llm_response_spark_oneshot, SparkChat

class IntentTreeGenerator:
    """
    Generates a structured intent tree for a given user task.
    Uses LLM to analyze tasks and create hierarchical subtasks with appropriate granularity.
    """
    
    def __init__(self, model="qwen-max-latest"):
        self.model = model
        self.system_prompt = """
        You are an expert in understanding how non-technical people think about tasks. Your job is to take a high-level task
        and break it down into a comprehensive hierarchy that reflects how someone WITHOUT programming knowledge would 
        conceptualize the steps. This tree should:

        1. Start with the main task as the root
        2. Break it down into 3-5 major subtasks as a non-technical person would see them
        3. Further decompose each subtask into more specific steps using everyday language
        4. Create a meaningful hierarchy with up to 3-4 levels of depth
        5. Represent a natural progression through the task from a user's perspective
        6. Focus on goals and outcomes, not implementation details
        7. Avoid technical programming concepts entirely

        Each node in the tree should represent a distinct goal or outcome that a non-technical person would understand.
        Use the language and mental models of someone who knows what they want but doesn't know how to code it.
        """
    
    def generate_diverse_main_task(self, main_task):
        prompt = f"""
        Please rewrite the following programming task in a different style while keeping the same core objective. 
        Only generate one alternative version.
        
        Original task: {main_task}
        
        Make sure the new version:
        1. Maintains the web scraping theme
        2. Changes specific details (like source, content type, or formatting)
        3. Uses different vocabulary and expression style
        4. Has similar technical complexity
        
        Respond with ONLY the rewritten task, no introduction or explanation.
        """
        
        system_prompt = "You are a technical writing expert who specializes in creating diverse programming task descriptions."
        response = get_llm_response(system_prompt, prompt, temperature=0.8)
        
        # Clean the response to ensure it's just the task
        response = response.strip()
        return response
    

    def generate_intent_tree(self, main_task, temperature=0.95, top_p=0.95):
        """
        Generate a hierarchical intent tree for the given main task.
        
        Args:
            main_task (str): The root task to decompose into a hierarchical tree
            
        Returns:
            dict: A nested dictionary representing the intent tree
        """
        
        prompt = f"""
        Please create a structured intent tree for the following task:
        The tree should have FEWER nodes at each level (2-3 subtasks per level), but can maintain a good depth.
        ATTENTION: This tree should represent the content related to the code.

        TASK: {main_task}

        The intent tree should be structured as a nested JSON object where:
        - Each key is a task or subtask description
        - Each value is either an empty dictionary {{}} for leaf nodes or another nested dictionary of subtasks

        IMPORTANT: Create the tree from the perspective of a NON-TECHNICAL person who doesn't understand programming concepts. 
        The tasks should:
        1. Focus on WHAT they want to achieve, not HOW to code it
        2. Use everyday language rather than technical terms
        3. Reflect how a non-programmer would think about breaking down the problem
        4. Include only 1-3 key subtasks at each level to keep the tree focused
        5. Express tasks as goals or outcomes that make sense to someone without coding knowledge

        Please generate some more detailed tasks, such as saving text, then please generate:
            saving all text in original order {{
                save title {{
                    mark main title {{}},
                    mark different levels of titles separately {{}}
                    }}, 
                save main text {{}}
                }}.
        Over all tree is shown below. This intent tree simulates the user's intent when writing code, so please only annotate the python code in the tree.
        For example, for "Create a personal website", a non-technical person might think:
            ```
            {{ 
            "Create a personal website": 
                {{ 
                    "Design the website": 
                        {{ 
                            "Choose the visual style": {{}}, 
                            "Plan the website structure": {{}} 
                        }}, 
                    "Add my content": 
                        {{ 
                            "Write about myself": {{}}, 
                            "Include my portfolio": 
                                {{ 
                                    "Select my best work": {{}},
                                    "Create descriptions for each item": {{}}
                                }} 
                        }}, 
                    "Publish the website": 
                        {{ 
                            "Get the website online": {{}}, 
                            "Make sure people can find it": {{}} 
                        }} 
                }} 
            }}
            ```

        Create a similar streamlined tree for the task I provided, with just 2-3 subtasks per branch.
        Make it reflect how a non-technical person would think about the task.
        Make sure the JSON is properly formatted with proper nesting.
        DO NOT include any explanations or additional text - just the raw JSON object.
        """

        # Get intent tree from LLM
        # Higher temperature and top_p values can lead to more creative and diverse responses
        response = get_llm_response(self.system_prompt, prompt, model=self.model, temperature=temperature, top_p=top_p)
        
        # Clean up the response to extract just the JSON
        cleaned_response = self._extract_json(response)
        
        try:
            intent_tree = json.loads(cleaned_response)
            return intent_tree
        except json.JSONDecodeError as e:
            # If parsing fails, try to fix common JSON formatting issues
            repaired_json = self._repair_json(cleaned_response)
            try:
                intent_tree = json.loads(repaired_json)
                return intent_tree
            except json.JSONDecodeError:
                # If still failing, get LLM to fix the JSON
                return self._get_llm_to_fix_json(response)
    
    def _extract_json(self, text):
        """Extract JSON from text that might contain other content"""
        # Look for JSON content between triple backticks
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        
        if json_match:
            return json_match.group(1).strip()
        
        # If no code blocks, try to find JSON by looking for opening/closing braces
        if text.strip().startswith('{') and text.strip().endswith('}'):
            return text.strip()
            
        # Look for first { and last }
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx+1]
            
        return text
    
    def _repair_json(self, json_str):
        """Attempt to repair common JSON formatting issues"""
        # Replace single quotes with double quotes
        json_str = json_str.replace("'", '"')
        
        # Ensure property names are in double quotes
        import re
        json_str = re.sub(r'(\w+)(:)', r'"\1"\2', json_str)
        
        # Remove trailing commas
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        
        return json_str
    
    def _get_llm_to_fix_json(self, broken_json):
        """Use LLM to fix broken JSON"""
        fix_prompt = f"""
        The following text should be a JSON object representing an intent tree, but it has formatting issues.
        Please fix the JSON formatting issues and return ONLY the corrected JSON object:

        {broken_json}

        Return ONLY the fixed JSON with no additional text or explanation.
        """
        
        fixed_json_str = get_llm_response(
            "You are a JSON repair specialist. Fix the provided JSON and return only the fixed JSON.",
            fix_prompt,
            model="qwen-turbo-latest"
        )
        
        # Extract and parse the fixed JSON
        cleaned_json = self._extract_json(fixed_json_str)
        try:
            return json.loads(cleaned_json)
        except json.JSONDecodeError:
            # If still failing, return a basic structure
            return {broken_json.strip(): {}}
    
    def save_intent_tree(self, intent_tree, filename="intent_tree.json"):
        """Save the generated intent tree to a JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(intent_tree, f, ensure_ascii=False, indent=2)
        print(f"Intent tree saved to {filename}")
    
    def visualize_intent_tree(self, intent_tree):
        """Print the intent tree in a readable format"""
        def _print_tree(node, indent=0):
            for task, subtasks in node.items():
                print("  " * indent + "- " + task)
                _print_tree(subtasks, indent + 1)
        
        print("\nIntent Tree Visualization:")
        print("=" * 50)
        _print_tree(intent_tree)
        print("=" * 50)


# Example usage
if __name__ == "__main__":
    generator = IntentTreeGenerator()
    
    # Example task
    # task = "写一个爬虫程序，爬取一个微信公众号文章的图片和文字并使用恰当的形式在一个文件中完整的返回图片和文字给我"
    task = "创建一个Python程序处理已有mp3音频，识别其中的语音内容并将其转换为文本格式输出，同时对识别出的关键词进行情感分析。"

    print(f"Generating intent tree for task: {task}")
    intent_tree = generator.generate_intent_tree(task, temperature=1, top_p=1)
    print("Current type of intent tree", type(intent_tree))
    # Visualize the generated tree
    # generator.visualize_intent_tree(intent_tree)
    
    # Print the tree as JSON
    print("\nIntent Tree JSON:")
    output_json = json.dumps(intent_tree, ensure_ascii=False, indent=2)
    print(type(output_json))
    
    

    # Example of using this tree in a multi-agent simulation
    print("\nThe generated intent tree can be used in the CodeGenerationAgents class like this:")
    print("```python")
    print("agents = CodeGenerationAgents()")
    print("agents.intent_tree = \n\n",  intent_tree)
    print("```")