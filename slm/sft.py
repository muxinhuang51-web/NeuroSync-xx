import os
import torch
import numpy as np
import evaluate
import time
import argparse
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datetime import datetime
from trl import SFTTrainer, SFTConfig
import gc

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Train a language model using SFT')

# Model settings
parser.add_argument('--model_tag', type=str, default="Qwen-7B", help='Model tag (e.g., Qwen-7B)')
parser.add_argument('--model_name', type=str, help='Full model name (overrides model_tag if provided)')
parser.add_argument('--seq_length', type=int, default=5000, help='Maximum sequence length')
parser.add_argument('--gpu_ids', type=str, default="0", help='Comma-separated GPU IDs to use')
parser.add_argument('--debug', type=bool, default=False, help='Run in debug mode with smaller dataset')
parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

# Training settings
parser.add_argument('--learning_rate', type=float, default=5e-5, help='Learning rate')
parser.add_argument('--train_batch_size', type=int, default=1, help='Per-device training batch size')
parser.add_argument('--eval_batch_size', type=int, default=1, help='Per-device evaluation batch size')
parser.add_argument('--gradient_accumulation', type=int, default=8, help='Gradient accumulation steps')
parser.add_argument('--epochs', type=int, default=1, help='Number of training epochs')
parser.add_argument('--weight_decay', type=float, default=0.01, help='Weight decay')
parser.add_argument('--output_dir', type=str, default="./results_sft", help='Output directory')
# Add these to your parser arguments
parser.add_argument('--eval_strategy', type=str, default="epoch", choices=["epoch", "steps", "no"], 
                    help='Evaluation strategy: epoch, steps, or no')
parser.add_argument('--save_strategy', type=str, default="epoch", choices=["epoch", "steps", "no"], 
                    help='Save strategy: epoch, steps, or no')
parser.add_argument('--eval_steps', type=int, default=300, 
                    help='Steps between evaluations if eval_strategy=steps')
parser.add_argument('--save_steps', type=int, default=1000, 
                    help='Steps between saves if save_strategy=steps')


# LoRA settings
parser.add_argument('--lora_r', type=int, default=8, help='LoRA rank')
parser.add_argument('--lora_alpha', type=int, default=32, help='LoRA alpha')
parser.add_argument('--lora_dropout', type=float, default=0.1, help='LoRA dropout')

# Dataset settings
parser.add_argument('--dataset_path', type=str, default='dialog_dataset.json', help='Path to dataset JSON')
parser.add_argument('--eval_split', type=float, default=0.1, help='Fraction of data for evaluation')

# Parse arguments
args = parser.parse_args()

# Global settings from arguments
VERBOSE = args.verbose
DEBUG_MODE = args.debug

# Set model name from either model_tag or model_name
tag = args.model_tag
LENGTH = args.seq_length
model_name = args.model_name if args.model_name else f"deepseek-ai/DeepSeek-R1-Distill-{tag}"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_ids

def vprint(*print_args, **kwargs):
    """vprint only when VERBOSE is True"""
    if VERBOSE:
        print(*print_args, **kwargs)

# Set training arguments
training_args = SFTConfig(
    output_dir=args.output_dir,
    evaluation_strategy=args.eval_strategy,  # Use arg instead of hardcoded "epoch"
    learning_rate=args.learning_rate,
    per_device_train_batch_size=args.train_batch_size,
    per_device_eval_batch_size=args.eval_batch_size,
    gradient_accumulation_steps=args.gradient_accumulation,
    num_train_epochs=args.epochs,
    weight_decay=args.weight_decay,
    save_strategy=args.save_strategy,  # Use arg instead of hardcoded "epoch"
    logging_dir=f"{args.output_dir}/logs",
    logging_steps=300,
    fp16=False,
    bf16=torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8,
    report_to="tensorboard",
    max_seq_length=LENGTH,
    packing=False,
    neftune_noise_alpha=5,
    gradient_checkpointing=True,
    optim="adamw_torch"
)

# Conditionally add eval_steps and save_steps only if needed
if args.eval_strategy == "steps":
    training_args.eval_steps = args.eval_steps
if args.save_strategy == "steps":
    training_args.save_steps = args.save_steps

# Rest of your class and function definitions remain unchanged
class MemoryEfficientSFTTrainer(SFTTrainer):
    def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval"):
        """
        Memory-efficient evaluation that processes examples one by one
        """
        import gc  # Add garbage collection
        
        # Use eval_dataset if provided, otherwise use the trainer's eval dataset
        eval_dataset = eval_dataset if eval_dataset is not None else self.eval_dataset
        
        # Initialize metrics
        rouge_metric = evaluate.load("rouge")
        bleu_metric = evaluate.load("bleu")
        
        # Initialize metric accumulators
        rouge1_sum = rouge2_sum = rougeL_sum = bleu_sum = 0.0
        total_examples = 0
        
        # Get evaluation dataloader
        dataloader = self.get_eval_dataloader(eval_dataset)
        self.model.eval()
        
        print("\n\n==================================Computing metrics==================================")
        print(f"Processing {len(dataloader)} evaluation batches...")
        
        # For backward compatibility - use tokenizer if available, fall back to processor
        tokenizer = getattr(self, "tokenizer", None)
        if tokenizer is None:
            tokenizer = getattr(self, "processing_class", None)
            if tokenizer is None:
                raise ValueError("Neither tokenizer nor processing_class found in trainer")
        
        # Process each batch individually
        for step, batch in enumerate(dataloader):
            # Move batch to device
            batch = self._prepare_inputs(batch)
            
            # print(f"Batch {step}/{len(dataloader)}")
            
            # Forward pass without gradient calculation
            with torch.no_grad():
                outputs = self.model(**batch)
                
            # Get predictions
            preds = outputs.logits.argmax(dim=-1)
            labels = batch["labels"]
            
            # Replace -100 with pad token id
            labels = torch.where(labels != -100, labels, tokenizer.pad_token_id)
            
            # Process each example in the batch individually
            batch_size = preds.size(0)
            for i in range(batch_size):
                # Get individual prediction and label
                pred = preds[i:i+1].detach().clone()  # Detach and clone to free from compute graph
                label = labels[i:i+1].detach().clone()
                
                # Decode to text
                decoded_pred = tokenizer.batch_decode(pred, skip_special_tokens=True)[0]
                decoded_label = tokenizer.batch_decode(label, skip_special_tokens=True)[0]
                
                # Free GPU memory for these tensors
                del pred, label
                
                # Extract content after </think> tag
                if "</think>" in decoded_pred:
                    decoded_pred = decoded_pred.split("</think>")[1].strip()
                
                # Calculate metrics for this individual example
                rouge_result = rouge_metric.compute(
                    predictions=[decoded_pred],
                    references=[decoded_label],
                    use_stemmer=True
                )
                
                bleu_result = bleu_metric.compute(
                    predictions=[decoded_pred],
                    references=[[decoded_label]]
                )
                
                # Accumulate metrics
                rouge1_sum += rouge_result['rouge1']
                rouge2_sum += rouge_result['rouge2']
                rougeL_sum += rouge_result['rougeL']
                bleu_sum += bleu_result['bleu']
                total_examples += 1
                
                # print(f"  Example {total_examples}: ROUGE-1={rouge_result['rouge1']:.4f}, BLEU={bleu_result['bleu']:.4f}")
                
                # Free memory
                del decoded_pred, decoded_label, rouge_result, bleu_result
            
            # Free batch memory
            del outputs, preds, labels, batch
            torch.cuda.empty_cache()  # Explicitly free GPU memory
            gc.collect()  # Run garbage collection
            
            # if step % 5 == 0:
            #     print(f"Processed {step}/{len(dataloader)} batches, {total_examples} examples")
        
        # Calculate average metrics
        if total_examples > 0:
            avg_rouge1 = rouge1_sum / total_examples
            avg_rouge2 = rouge2_sum / total_examples
            avg_rougeL = rougeL_sum / total_examples
            avg_bleu = bleu_sum / total_examples
        else:
            avg_rouge1 = avg_rouge2 = avg_rougeL = avg_bleu = 0.0
        
        # Combine metrics
        results = {
            f"{metric_key_prefix}_rouge1": avg_rouge1,
            f"{metric_key_prefix}_rouge2": avg_rouge2,
            f"{metric_key_prefix}_rougeL": avg_rougeL,
            f"{metric_key_prefix}_bleu": avg_bleu
        }
        
        print(f"Evaluation completed on {total_examples} examples")
        print(f"Average ROUGE-1: {avg_rouge1:.4f}")
        print(f"Average ROUGE-2: {avg_rouge2:.4f}")
        print(f"Average ROUGE-L: {avg_rougeL:.4f}")
        print(f"Average BLEU: {avg_bleu:.4f}")
        
        # Log metrics
        self.log(results)
        
        # Free metric objects explicitly after use
        del rouge_metric, bleu_metric
        torch.cuda.empty_cache()  # Force CUDA memory cleanup
        
        return results

# Load dataset
print("Loading dataset...")
try:
    # Load your custom dataset from JSON file
    dataset = load_dataset('json', data_files=args.dataset_path)['train']
    
    # Split into train/eval (90%/10%)
    splits = dataset.train_test_split(test_size=args.eval_split, seed=42)
    dataset = splits['train']  # 90% for training
    eval_dataset = splits['test']  # 10% for evaluation
    

    if DEBUG_MODE:
        dataset = dataset.select(range(60))
        eval_dataset = eval_dataset.select(range(15))
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
    r=args.lora_r,
    lora_alpha=args.lora_alpha,
    lora_dropout=args.lora_dropout,
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
trainer = MemoryEfficientSFTTrainer(
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

# # Add baseline evaluation before training
# print("\n=== Running baseline evaluation before fine-tuning ===")
# baseline_results = trainer.evaluate()
# print("\n=== Baseline metrics ===")
# print(f"ROUGE-1: {baseline_results['eval_rouge1']:.4f}")
# print(f"ROUGE-2: {baseline_results['eval_rouge2']:.4f}")
# print(f"ROUGE-L: {baseline_results['eval_rougeL']:.4f}")
# print(f"BLEU: {baseline_results['eval_bleu']:.4f}")
# print("=" * 50)



# Start training
print("Starting training...")
trainer.train()

# Save model
print("Saving model...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
save_dir = f"./sft_model_{model_name.replace('-', '_')}_{timestamp}"
trainer.model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"Model fine-tuning completed and saved to {save_dir}.")

torch.cuda.empty_cache()
gc.collect()
print("CUDA memory cache cleared")


# Enhanced testing section with multiple examples and performance metrics
print("\n=== Testing the fine-tuned model ===")
try:
    # Set number of examples to test
    num_test_examples = min(0, len(eval_dataset))  # Test up to 5 examples or all if fewer
    print(f"We are using {num_test_examples} examples for testing.")
    # Initialize metrics tracking
    total_tokens = 0
    total_time = 0
    all_times = []
    all_token_counts = []
    
    for idx in range(num_test_examples):
        # Get test example
        test_example = eval_dataset[idx]
        print(f"\n--- Testing example {idx+1}/{num_test_examples} ---")
        print(f"Article: {test_example['article'][:100]}..." if len(test_example['article']) > 100 else test_example['article'])
        print(f"Expected highlights: {test_example['highlights'][:100]}..." if len(test_example['highlights']) > 100 else test_example['highlights'])
        
        # Use the same format as in training
        instruction = test_example["article"]
        
        # Just use the prompt part without the expected response
        input_text = f"Task Description: {instruction}\n\n<think>"
        
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        
        # Start timing
        start_time = time.time()
        
        outputs = model.generate(
            **inputs,
            max_length=LENGTH,
            temperature=0.7,
            num_return_sequences=1
        )
        
        # End timing
        end_time = time.time()
        inference_time = end_time - start_time
        
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # Calculate number of output tokens (excluding input tokens)
        output_tokens = len(outputs[0]) - len(inputs.input_ids[0])
        tokens_per_second = output_tokens / inference_time if inference_time > 0 else 0
        
        # Track metrics
        total_tokens += output_tokens
        total_time += inference_time
        all_times.append(inference_time)
        all_token_counts.append(output_tokens)
        
        print(f"\nGenerated output (showing first 200 chars):\n{generated_text[:200]}...")
        
        # Extract part after </think> if present
        if "</think>" in generated_text:
            response = generated_text.split("</think>")[1].strip()
            print(f"\nExtracted response (showing first 200 chars):\n{response[:200]}...")
        
        # Performance metrics for this example
        print(f"\nPerformance metrics for example {idx+1}:")
        print(f"- Generation time: {inference_time:.2f} seconds")
        print(f"- Output tokens: {output_tokens}")
        print(f"- Tokens per second: {tokens_per_second:.2f}")
    
    # Calculate average performance metrics
    avg_time = total_time / num_test_examples
    avg_tokens = total_tokens / num_test_examples
    avg_tokens_per_second = total_tokens / total_time if total_time > 0 else 0
    
    # Calculate standard deviation
    time_std = np.std(all_times) if len(all_times) > 1 else 0
    tokens_std = np.std(all_token_counts) if len(all_token_counts) > 1 else 0
    
    print("\n=== Overall Performance Summary ===")
    print(f"Total examples tested: {num_test_examples}")
    print(f"Average generation time: {avg_time:.2f} seconds (±{time_std:.2f})")
    print(f"Average output tokens: {avg_tokens:.2f} (±{tokens_std:.2f})")
    print(f"Average tokens per second: {avg_tokens_per_second:.2f}")

    torch.cuda.empty_cache()
    gc.collect()
    print("CUDA memory cache cleared")
    
except Exception as e:
    print(f"Error during test generation: {e}")
    import traceback
    traceback.print_exc()
    
    torch.cuda.empty_cache()
    gc.collect()
    print("CUDA memory cache cleared")

print("\nFine-tuning process completed.")


