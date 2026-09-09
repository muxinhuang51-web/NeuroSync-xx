import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel, PeftConfig

# Path to your saved model (replace with your actual path)
model_path = "/home/wzhangeb/lancet/slm/web_result/sft_model_deepseek_ai/DeepSeek_R1_Distill_Llama_8B_20250307_020652"

# 1. Load the configuration to get the base model name
config = PeftConfig.from_pretrained(model_path)

# 2. Load the base model with quantization
model = AutoModelForCausalLM.from_pretrained(
    config.base_model_name_or_path,
    device_map="auto",
    torch_dtype=torch.float16,  # or torch.bfloat16 if supported
)

# 3. Load the fine-tuned LoRA weights
model = PeftModel.from_pretrained(model, model_path)

# 4. Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_path)

# Function to generate a response
def generate_response(instruction, max_length=5000):
    # Format the input as in your training data
    input_text = f"Task Description: {instruction}\n\n<think>"
    
    # Tokenize and generate
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    
    outputs = model.generate(
        **inputs,
        max_length=max_length,
        temperature=0.7,
        num_return_sequences=1,
    )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    # Extract the actual response after the thinking
    if "</think>" in generated_text:
        response = generated_text.split("</think>")[1].strip()
        return response
    
    return generated_text

# Example usage
instruction = "Summarize the key features of Python programming language."
response = generate_response(instruction)
print(response)