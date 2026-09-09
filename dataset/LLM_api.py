import os
from openai import OpenAI

# model option: "qwen-max-latest" "qwen-plus-latest" or "qwen-turbo-latest"
def get_llm_response_whole(system_content, user_content, model = "qwen-max-latest"):
    api_key = "sk-ecb103e3471849b1b3de6cef5bde581f"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    messages = [
        {'role': 'system', 'content': system_content},
        {'role': 'user', 'content': user_content}
    ]
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    response_content = completion.choices[0].message.content
    return response_content

# model option: "qwen-max-latest" "qwen-plus-latest" or "qwen-turbo-latest"
def get_llm_response(system_content, user_content, model="qwen-max-latest", temperature=None, top_p=None):
    api_key = "sk-ecb103e3471849b1b3de6cef5bde581f"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    messages = [
        {'role': 'system', 'content': system_content},
        {'role': 'user', 'content': user_content}
    ]
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=temperature,  # Add temperature parameter
        top_p=top_p,  # Add top_p parameter
        stream_options={"include_usage": True}
    )
    
    response_content = ""
    for chunk in completion:
        # print(chunk)
        # print(chunk.choices[0].delta.content)
        if chunk.choices:
            response_content += chunk.choices[0].delta.content
    
    # print("Overall content: \n", response_content)
    return response_content



# Saprk API: "sk-gODBFSZL8uzFiyFF2bB0C798B35440D7Aa0127B964216b51"
# Spark Service ID: "xdeepseekr1"
def get_llm_response_spark_oneshot(system_content, user_content, capture_reasoning=False, result_only=True):
    api_key = "sk-gODBFSZL8uzFiyFF2bB0C798B35440D7Aa0127B964216b51"
    base_url = "http://maas-api.cn-huabei-1.xf-yun.com/v1"
    model = "xdeepseekr1"
    
    messages = [
        {'role': 'system', 'content': system_content},
        {'role': 'user', 'content': user_content}
    ]
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.7,
        max_tokens=4096,
        extra_headers={"lora_id": "0"},
        stream_options={"include_usage": True}
    )
    
    response_content = ""
    reasoning_content = ""
    
    for chunk in completion:
        # Capture reasoning process (thinking steps) if available and requested
        if (capture_reasoning and hasattr(chunk.choices[0].delta, 'reasoning_content') 
            and chunk.choices[0].delta.reasoning_content is not None):
            reasoning_content += chunk.choices[0].delta.reasoning_content
        
        # Capture the regular content
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
            response_content += chunk.choices[0].delta.content
    
    if capture_reasoning:
        if result_only:
            return response_content
        else:
            return {"response": response_content, "reasoning": reasoning_content}
    return response_content


class SparkChat:
    """
    A class to manage multi-turn conversations with the Spark LLM,
    simulating a web chat interface.
    """
    
    def __init__(self, system_prompt="You are a helpful assistant.", capture_reasoning=True, record_reasoning=False, result_only=True):
        """
        Initialize a new conversation session with Spark LLM.
        
        Args:
            system_prompt (str): The system prompt that defines assistant behavior
            capture_reasoning (bool): Whether to capture reasoning processes
            record_reasoning (bool): Whether to record reasoning processes in history
            result_only (bool): Whether to only return response content in the result
        """
        self.api_key = "sk-gODBFSZL8uzFiyFF2bB0C798B35440D7Aa0127B964216b51"
        self.base_url = "http://maas-api.cn-huabei-1.xf-yun.com/v1"
        self.model = "xdeepseekr1"
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": system_prompt}]
        self.history = []  # Store conversation history for display
        self.record_reasoning = record_reasoning  # Control whether to record reasoning in history
        self.capture_reasoning = capture_reasoning  # Control whether to capture reasoning in responses
        self.result_only = result_only  # Control whether to include reasoning in the returned result
        
    def send_message(self, user_message, capture_reasoning=None, result_only=None):
        """
        Send a user message to the LLM and get the response.
        
        Args:
            user_message (str): The user's input message
            capture_reasoning (bool): Whether to capture the model's reasoning process
            result_only (bool): Whether to only return response content
            
        Returns:
            dict: Contains LLM response and optionally reasoning
        """
        # Use instance defaults if parameters not provided
        capture_reasoning = self.capture_reasoning if capture_reasoning is None else capture_reasoning
        result_only = self.result_only if result_only is None else result_only
        
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})
        self.history.append({"role": "user", "content": user_message})
        
        # Create OpenAI client
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # Send conversation to LLM
        completion = client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            temperature=0.7,
            max_tokens=4096,
            extra_headers={"lora_id": "0"},
            stream_options={"include_usage": True}
        )
        
        # Process streaming response
        response_content = ""
        reasoning_content = ""
        
        for chunk in completion:
            # Capture reasoning if available and requested
            if (capture_reasoning and hasattr(chunk.choices[0].delta, 'reasoning_content') 
                and chunk.choices[0].delta.reasoning_content is not None):
                reasoning_content += chunk.choices[0].delta.reasoning_content
            
            # Capture regular content
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                response_content += chunk.choices[0].delta.content
        
        # Add assistant response to conversation history
        self.messages.append({"role": "assistant", "content": response_content})
        
        # Store response in history, with reasoning if configured
        history_entry = {"role": "assistant", "content": response_content}
        if self.record_reasoning and reasoning_content:
            history_entry["reasoning"] = reasoning_content
        self.history.append(history_entry)
        
        # Return response with optional reasoning based on result_only
        if capture_reasoning and reasoning_content and not result_only:
            return {
                "response": response_content,
                "reasoning": reasoning_content
            }
        else:
            return {"response": response_content}
    
    def get_history(self):
        """Get the conversation history."""
        return self.history
    
    def clear_history(self, keep_system_prompt=True):
        """
        Clear conversation history.
        
        Args:
            keep_system_prompt (bool): Whether to keep the system prompt
        """
        if keep_system_prompt:
            self.messages = [{"role": "system", "content": self.system_prompt}]
        else:
            self.messages = []
        self.history = []
    
    def update_system_prompt(self, new_system_prompt):
        """
        Update the system prompt.
        
        Args:
            new_system_prompt (str): The new system prompt
        """
        self.system_prompt = new_system_prompt
        # Replace existing system message or add a new one
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = new_system_prompt
        else:
            self.messages.insert(0, {"role": "system", "content": new_system_prompt})


class QwenChat:
    """
    A class to manage multi-turn conversations with the Qwen LLM,
    simulating a web chat interface.
    """
    
    def __init__(self, system_prompt="You are a helpful assistant.", model="qwen-max-latest", temperature=0.7):
        """
        Initialize a new conversation session with Qwen LLM.
        
        Args:
            system_prompt (str): The system prompt that defines assistant behavior
            model (str): The Qwen model to use ("qwen-max-latest", "qwen-plus-latest", or "qwen-turbo-latest")
            temperature (float): Control randomness in responses (0.0 to 1.0)
        """
        self.api_key = "sk-ecb103e3471849b1b3de6cef5bde581f"
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.messages = [{"role": "system", "content": system_prompt}]
        self.history = []  # Store conversation history for display
        
    def send_message(self, user_message, temperature=None):
        """
        Send a user message to the Qwen LLM and get the response.
        
        Args:
            user_message (str): The user's input message
            temperature (float): Optional override for response temperature
            
        Returns:
            dict: Contains LLM response
        """
        # Use instance default if temperature not provided
        temperature = self.temperature if temperature is None else temperature
        
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})
        self.history.append({"role": "user", "content": user_message})
        
        # Create OpenAI client
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # Send conversation to LLM
        completion = client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            temperature=temperature,
            stream_options={"include_usage": True}
        )
        
        # Process streaming response
        response_content = ""
        
        for chunk in completion:
            # Check if choices list exists and is not empty before accessing its elements
            if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                response_content += chunk.choices[0].delta.content
        
        # Add assistant response to conversation history
        self.messages.append({"role": "assistant", "content": response_content})
        self.history.append({"role": "assistant", "content": response_content})
        
        # Return response
        return {"response": response_content}
    
    def get_history(self):
        """Get the conversation history."""
        return self.history
    
    def clear_history(self, keep_system_prompt=True):
        """
        Clear conversation history.
        
        Args:
            keep_system_prompt (bool): Whether to keep the system prompt
        """
        if keep_system_prompt:
            self.messages = [{"role": "system", "content": self.system_prompt}]
        else:
            self.messages = []
        self.history = []
    
    def update_system_prompt(self, new_system_prompt):
        """
        Update the system prompt.
        
        Args:
            new_system_prompt (str): The new system prompt
        """
        self.system_prompt = new_system_prompt
        # Replace existing system message or add a new one
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = new_system_prompt
        else:
            self.messages.insert(0, {"role": "system", "content": new_system_prompt})
            
    def update_model(self, new_model):
        """
        Update the Qwen model being used.
        
        Args:
            new_model (str): The new model to use ("qwen-max-latest", "qwen-plus-latest", or "qwen-turbo-latest")
        """
        self.model = new_model


# Example usage
if __name__ == "__main__":
    # system_content = 'You are a helpful assistant.'
    # user_content = 'Who are you？'

    # # Test Qwen model
    # response = get_llm_response(system_content, user_content)
    # print("we start to test the get_llm_response function - Qwen")
    # print(response)
    
    # # Test Deepseek R1 model with reasoning
    # print("\n\n")
    # print("we start to test the get_llm_response_spark_oneshot function - Spark one round")
    # spark_response = get_llm_response_spark_oneshot(system_content, user_content, capture_reasoning=True)
    # if isinstance(spark_response, dict):
    #     print("\nSpark Response:")
    #     print("Response:", spark_response["response"])
    #     print("\nReasoning Process:", spark_response["reasoning"])
    # else:
    #     print("\nSpark Response:", spark_response)
    
    
    # Create a new chat session. Test multi-turn deepseek R1 conversation.
    print("\n\n")
    print("we start to test the SparkChat class")
    chat = SparkChat(system_prompt="You are a knowledgeable mathematics tutor.")
    
    # First message
    response1 = chat.send_message("你好", capture_reasoning=True,result_only=False)
    print("First")
    print("Assistant:", response1["response"])
    print(response1["reasoning"])
    if "reasoning" in response1:
        print("\nReasoning:", response1["reasoning"])
    print("\n" + "-"*50 + "\n")
    
    # Second message (continuing the conversation)
    response2 = chat.send_message("我喜欢你", capture_reasoning=True,result_only=False)
    print("Second")
    print("Assistant:", response2["response"])
    print(response2["reasoning"])
    print("\n" + "-"*50 + "\n")
    
    # Third message (referencing previous context)
    response3 = chat.send_message("你为什么这么聪明", capture_reasoning=True,result_only=False)
    print("Third")
    print("Assistant:", response3["response"])
    print(response3["reasoning"])
    print("\n" + "-"*50 + "\n")
    
    # Print full conversation history
    print("CONVERSATION HISTORY:")
    for i, message in enumerate(chat.get_history()):
        print(f"[{i+1}] {message['role'].upper()}: {message['content'][:50]}...")

    # # Test QwenChat class
    # print("\n\n")
    # print("we start to test the QwenChat class")
    # qwen_chat = QwenChat(system_prompt="You are a friendly Chinese language teacher.")

    # # First message
    # qwen_response1 = qwen_chat.send_message("你好，我想学中文")
    # print("First")
    # print("Assistant:", qwen_response1["response"])
    # print("\n" + "-"*50 + "\n")

    # # Second message (continuing the conversation)
    # qwen_response2 = qwen_chat.send_message("怎样才能快速提高我的中文水平?")
    # print("Second")
    # print("Assistant:", qwen_response2["response"])
    # print("\n" + "-"*50 + "\n")

    # # Print full conversation history
    # print("QWEN CONVERSATION HISTORY:")
    # for i, message in enumerate(qwen_chat.get_history()):
    #     print(f"[{i+1}] {message['role'].upper()}: {message['content'][:50]}...")
    # prompt = """
    # Please rewrite the following programming task in a different style while keeping the same core objective. 
    # Only generate one alternative version.
    
    # Original task: "写一个爬虫程序，爬取指定URL的微信文章内容并保存到本地"
    
    # Make sure the new version:
    # 1. Maintains the web scraping theme
    # 2. Changes specific details (like source, content type, or formatting)
    # 3. Uses different vocabulary and expression style
    # 4. Has similar technical complexity
    
    # Respond with ONLY the rewritten task, no introduction or explanation.
    # """
    
    # system_prompt = "You are a technical writing expert who specializes in creating diverse programming task descriptions."
    # for i in range(10):
    #     response = get_llm_response(system_prompt, prompt, temperature=1, top_p=1)
    
    #     # Clean the response to ensure it's just the task
    #     response = response.strip()
    #     print(response)