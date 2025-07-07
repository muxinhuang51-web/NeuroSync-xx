import os
import torch
import numpy as np
import evaluate
import time
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datetime import datetime
from trl import SFTTrainer, SFTConfig

# Global verbose setting
VERBOSE = False  # Set to True for detailed outputs, False for minimal output
DEBUG_MODE = True  # Set to True to run in debug mode, which uses a small subset of the dataset


# Set model name
tag = "Qwen-7B"
LENGTH = 6000
EVALBATCHSIZE = 5
model_name = f"deepseek-ai/DeepSeek-R1-Distill-{tag}"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use GPU 0 and 2d 2

def vprint(*args, **kwargs):
    """vprint only when VERBOSE is True"""
    if VERBOSE:
        print(*args, **kwargs)

# Set training arguments
training_args = SFTConfig(
    output_dir="./results_sft",
    evaluation_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,  # Increased to reduce memory pressure
    num_train_epochs=1,
    weight_decay=0.01,
    save_strategy="epoch",
    logging_dir="./logs_sft",
    logging_steps=300,
    fp16=False,  # Don't use fp16 with quantization
    bf16=torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8,  # Use bf16 on newer GPUs
    report_to="tensorboard",
    max_seq_length=LENGTH,  # More reasonable sequence length
    packing=False,
    neftune_noise_alpha=5,
    gradient_checkpointing=True,  # Enable gradient checkpointing
    optim="adamw_torch"  # More memory efficient optimizer
)


# Load dataset
print("Loading dataset...")
try:
    # Load your custom dataset from JSON file
    dataset = load_dataset('json', data_files='dialog_dataset.json')['train']
    
    # Split into train/eval (90%/10%)
    splits = dataset.train_test_split(test_size=0.1, seed=42)
    dataset = splits['train']  # 90% for training
    eval_dataset = splits['test']  # 10% for evaluation
    

    if DEBUG_MODE:
        dataset = dataset.select(range(5))
        eval_dataset = eval_dataset.select(range(20))
        vprint("=== Sample data ===")
        vprint(f"Keys: {eval_dataset[0].keys()}")
        vprint(f"Article: {eval_dataset[0]['article'][:100]}...")
        vprint(f"Highlights: {eval_dataset[0]['highlights'][:100]}...")
    
    print(f"Dataset loaded: {len(dataset)} training examples, {len(eval_dataset)} validation examples")

except Exception as e:
    print(f"Error loading dataset: {e}")
    exit(1)

# Load DeepSeek model and tokenizer
print("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Store EOS token for use in formatting
EOS_TOKEN = tokenizer.eos_token
print(f"EOS token: {repr(EOS_TOKEN)}")

# Modify format_instruction function to include EOS token! THIS IS MUST!
def format_instruction(example):
    """
    Format the example into an instruction format with think tags.
    
    The dataset field names are misleading:
    - 'article' actually contains the instruction/task
    - 'highlights' contains the expected result/response
    """
    instruction = example["article"]
    expected_response = example["highlights"]
    
    # Format with think tags pattern and add EOS token
    formatted_text = f"Task Description: {instruction}\n\n<think>Planning how to respond to this instruction...</think>\n\nTask Result: {expected_response}{EOS_TOKEN}"
    
    return {"text": formatted_text}

# Configure quantization
quantization_config = BitsAndBytesConfig(
    load_in_16bit=True,
    # load_in_4bit=True,
    # bnb_4bit_compute_dtype=torch.bfloat16,
    # bnb_4bit_use_double_quant=True,
    # bnb_4bit_quant_type="nf4"
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto" if torch.cuda.is_available() else "cpu",
    quantization_config=quantization_config
)

# Add special tokens if they don't exist
special_tokens = {"additional_special_tokens": ["<think>", "</think>"]}
num_added = tokenizer.add_special_tokens(special_tokens)
if num_added > 0:
    vprint(f"Added {num_added} special tokens to the tokenizer")
    model.resize_token_embeddings(len(tokenizer))

# Configure LoRA
print("Configuring LoRA...")
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    inference_mode=False,
    r=8,
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "v_proj"]
)

# Prepare model for training - need this for k-bit training
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# Format dataset for instruction tuning
print("Formatting dataset for instruction tuning...")
sft_dataset = dataset.map(format_instruction, remove_columns=["article", "highlights", "id"])
sft_eval_dataset = eval_dataset.map(format_instruction, remove_columns=["article", "highlights", "id"])

# vprint a sample to verify formatting
print("=== Sample formatted example ===")
vprint(sft_dataset[0]['text'][:500] + "..." if len(sft_dataset) > 0 else "No examples available")



# Custom evaluation function to handle think tags
def compute_metrics(eval_preds):
    """Calculate metrics after extracting content after </think> tags"""
    print("\n\n==================================Computing metrics==================================")
    exit(1)
    predictions, labels = eval_preds
    if isinstance(predictions, torch.Tensor):
        predictions = predictions.detach().cpu().numpy()
    if isinstance(labels, torch.Tensor):
        labels = labels.detach().cpu().numpy()
    
    
    print(type(predictions))
    print(predictions.shape)

    # Get most likely predictions
    if predictions.ndim == 3:
        predictions = np.argmax(predictions, axis=-1)
    
    # Replace -100 with pad token id
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    
    # Decode to text
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    
    # Extract after </think> tags
    processed_preds = []
    for pred in decoded_preds:
        parts = pred.split("</think>")
        if len(parts) > 1:
            # If "</think>" is found, take text after it
            processed_preds.append(parts[1].strip())
        else:
            processed_preds.append(pred.strip())
    
    # Load metrics
    rouge_metric = evaluate.load("rouge")
    bleu_metric = evaluate.load("bleu")
    
    # Calculate ROUGE
    rouge_results = rouge_metric.compute(
        predictions=processed_preds,
        references=[label.strip() for label in decoded_labels],
        use_stemmer=True
    )
    
    # Calculate BLEU
    bleu_results = bleu_metric.compute(
        predictions=processed_preds,
        references=[[label.strip()] for label in decoded_labels]
    )
    
    # Combine metrics
    results = {
        "rouge1": rouge_results["rouge1"],
        "rouge2": rouge_results["rouge2"],
        "rougeL": rouge_results["rougeL"],
        "bleu": bleu_results["bleu"]
    }
    
    return results

# Initialize SFTTrainer
print("Initializing SFT Trainer...")
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=sft_dataset,
    eval_dataset=sft_eval_dataset,
    tokenizer=tokenizer,
    peft_config=peft_config,
    dataset_text_field="text",
    # max_seq_length=20,
    compute_metrics=compute_metrics,
)

# time.sleep(10000)

# Start training
print("Starting training...")
trainer.train()

# Save model
print("Saving model...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
save_dir = f"./sft_model_{tag.replace('-', '_')}_{timestamp}"
trainer.model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"Model fine-tuning completed and saved to {save_dir}.")

# Example of generating text with the fine-tuned model
print("\n=== Testing the fine-tuned model ===")
try:
    # Use one datapoint from eval dataset
    test_example = eval_dataset[0]
    print("Testing with evaluation example:")
    print(f"Article: {test_example['article'][:100]}..." if len(test_example['article']) > 100 else test_example['article'])
    print(f"Expected highlights: {test_example['highlights'][:100]}..." if len(test_example['highlights']) > 100 else test_example['highlights'])
    
    # Use the same format as in training
    instruction = test_example["article"]
    
    # Just use the prompt part without the expected response
    input_text = f"Task Description: {instruction}\n\n<think>"
    
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_length=LENGTH,
        temperature=0.7,
        num_return_sequences=1
    )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
    print(f"\nGenerated output:\n{generated_text}")
    
    # Extract part after </think> if present
    if "</think>" in generated_text:
        response = generated_text.split("</think>")[1].strip()
        print(f"\nExtracted response:\n{response}")
        
        # Compare with expected response
        print(f"\nExpected response:\n{test_example['highlights']}")
    
except Exception as e:
    print(f"Error during test generation: {e}")

print("\nFine-tuning process completed.")