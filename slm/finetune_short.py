import os
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
import torch
from datetime import datetime
from transformers import DataCollatorForLanguageModeling
import numpy as np
from transformers import EvalPrediction
import evaluate  # Import the evaluate library instead of load_metric

# set model name
# "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B", "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
# "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"， "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
tag = "Qwen-7B"
model_name = f"deepseek-ai/DeepSeek-R1-Distill-{tag}"

# Set GPU environment
os.environ["CUDA_VISIBLE_DEVICES"] = "0,2"  # Use GPU 0 and 2

# Data preprocessing function
def preprocess_function(examples):
    """
    Data preprocessing function to convert the CNN/DailyMail dataset into a format acceptable by the model.
    
    Args:
        examples (dict): Dictionary containing 'article' and 'highlights' fields.
    
    Returns:
        dict: Preprocessed inputs and labels.
    """
    inputs = [doc for doc in examples["article"]]
    targets = [summary for summary in examples["highlights"]]
    
    # Print raw inputs and targets for the first example to debug
    if False and len(inputs) > 0:
        print("\n=== Raw Input and Target Data ===")
        print(f"Raw input[0] (article):\n{repr(inputs[0])}...")
        print(f"Raw target[0] (highlights):\n{repr(targets[0])}...")
    
    # Construct input format: only include article content
    model_inputs = tokenizer(
        inputs,
        max_length = 1700,  # Adjust according to the model's maximum length (DeepSeek model supports longer sequences)
        truncation=True,
        padding="max_length"
    )
    
    # Construct labels: only include summary content
    labels = tokenizer(
        text_target=targets,
        max_length=1700,  # Summary length is usually shorter, adjust as needed
        truncation=True,
        padding="max_length"
    )["input_ids"]
    
    # Add labels to model inputs
    model_inputs["labels"] = labels

    # Create a new dictionary with only the desired keys
    new_model_inputs = {
        "input_ids": model_inputs["input_ids"],
        "attention_mask": model_inputs["attention_mask"],
        "labels": model_inputs["labels"],
    }

    # Print model inputs for debugging
    if False:
        for key, value in new_model_inputs.items():
            print(f"\nField: {key}")
            print(f"Type: {type(value)}")
            print(f"Length: {len(value)}")
            if isinstance(value, list):
                print(f"First element type: {type(value[0])}")
                print(f"First element length: {len(value[0]) if isinstance(value[0], list) else 'N/A'}")
                
        # Add this code to decode the tokenized inputs and labels to see their actual text content
        if len(new_model_inputs["input_ids"]) > 0:
            print("\n=== Decoded Tokenized Data (First Example) ===")
            # Decode input_ids back to text to verify what the model will see
            decoded_input = tokenizer.decode(new_model_inputs["input_ids"][0], skip_special_tokens=True)
            print(f"Decoded input_ids[0]:\n{decoded_input}...")
            
            # Decode labels back to text (replacing -100 with pad token id first)
            labels_for_decoding = [id if id != -100 else tokenizer.pad_token_id for id in new_model_inputs["labels"][0]]
            decoded_labels = tokenizer.decode(labels_for_decoding, skip_special_tokens=True)
            print(f"Decoded labels[0]:\n{decoded_labels}...")

    return new_model_inputs

# Define custom loss function to only focus on result part (after "</think>")
def custom_loss(outputs, labels, num_items_in_batch=None):
    """
    Custom loss function to focus only on the result part (after "</think>").
    
    Args:
        outputs: Model outputs from the forward pass
        labels: The target labels that were popped from inputs
        num_items_in_batch: Optional number of items in the batch for loss normalization
        
    Returns:
        torch.Tensor: The calculated loss
    """
    # Get logits from outputs (could be a tuple or a dictionary)
    if isinstance(outputs, dict):
        logits = outputs.logits  # [batch_size, seq_len, vocab_size]
    else:
        logits = outputs[0]  # Assuming first element contains logits
    
    # Filter out -100 values from labels before decoding
    label_tokens = labels[0].clone()
    label_tokens = label_tokens[label_tokens != -100]
    pred_tokens = logits[0].argmax(dim=-1)
    
    print("====================label_tokens====================")
    print("\n\n\n=====>Labels: \n", tokenizer.decode(label_tokens, skip_special_tokens=True))
    print("====================pred_tokens====================")
    print("\n\n\n=====>Outputs: \n", tokenizer.decode(pred_tokens, skip_special_tokens=True))

    # Get token ID for "</think>"
    think_token_ids = tokenizer.encode("</think>", add_special_tokens=False)
    think_token_id = think_token_ids[-1]  # Get the last token ID for detection
    
    # Print necessary debugging information
    # print(f"Batch size: {logits.size(0)}, Sequence length: {logits.size(1)}")
    # print(f"Think token ID: {think_token_id}")
    
    # Initialize loss mask - default to False (don't calculate loss for any tokens)
    loss_mask = torch.zeros_like(labels, dtype=torch.bool)
    
    # For inference outputs that contain "</think>"
    for i in range(logits.size(0)):  # Iterate through each sample in batch
        # Get predicted tokens (for current inference)
        pred_tokens = torch.argmax(logits[i], dim=-1)
        
        # Find position of "</think>" in the predicted sequence
        think_positions = (pred_tokens == think_token_id).nonzero(as_tuple=True)[0]
        
        if len(think_positions) > 0:
            # Found "</think>" - only keep tokens after this
            start_idx = think_positions[0] + 1  # Start after the "</think>" token
            loss_mask[i, start_idx:] = True  # Mark result part for loss calculation
            # print(f"Sample {i}: '</think>' found at position {think_positions[0].item()}")
        else:
            # If "</think>" is not found, compute loss on everything
            # This is needed during training to help the model learn to generate "</think>"
            loss_mask[i, :] = True
            # print(f"Sample {i}: '</think>' not found, using full sequence")
    
    # Set loss for padding tokens (-100) to False
    loss_mask = loss_mask & (labels != -100)
    
    # Only keep logits and labels where loss_mask is True
    # Reshape for cross entropy loss calculation
    active_logits = logits.view(-1, logits.size(-1))  # [batch_size * seq_len, vocab_size]
    active_labels = labels.view(-1)  # [batch_size * seq_len]
    active_mask = loss_mask.view(-1)  # [batch_size * seq_len]
    
    # Filter by mask
    active_logits = active_logits[active_mask]  # [num_active_tokens, vocab_size]
    active_labels = active_labels[active_mask]  # [num_active_tokens]
    
    # Print active token count
    # print(f"Active tokens for loss calculation: {active_labels.size(0)}")
    
    # If no tokens are marked for loss calculation, return zero loss
    if active_labels.size(0) == 0:
        # print("No tokens available for loss calculation, returning zero loss")
        return torch.tensor(0.0, device=logits.device)
    
    # Calculate cross entropy loss
    loss_fct = torch.nn.CrossEntropyLoss()
    loss = loss_fct(active_logits, active_labels)
    # print(f"Calculated loss: {loss.item()}")

    # If needed, can use num_items_in_batch to adjust the loss
    # if num_items_in_batch is not None:
    #     loss = loss * (active_labels.size(0) / num_items_in_batch)
    #     # print(f"Adjusted loss: {loss.item()}")


    # Return loss only
    return loss

# Add this function before defining your Trainer
def compute_metrics(eval_pred, compute_result=False):
    """
    Compute metrics for model evaluation.
    When "</think>" is present, only evaluate the part after the delimiter.
    
    Args:
        eval_pred (EvalPrediction): Contains predictions and label_ids
        compute_result (bool): Whether to compute the final result (True for last batch)
            or just accumulate statistics (False for intermediate batches)
            
    Returns:
        dict: Dictionary containing the computed metrics
    """
    # print(f"\n=== compute_metrics called with compute_result={compute_result} ===")
    
    # Initialize metrics objects if first call or if computing final results
    if not hasattr(compute_metrics, "rouge_metric") or compute_result:
        # print("Initializing metrics objects")
        compute_metrics.rouge_metric = evaluate.load("rouge")
        compute_metrics.bleu_metric = evaluate.load("bleu")
        
    # Get predictions and labels
    predictions, labels = eval_pred.predictions, eval_pred.label_ids
    # print(f"Predictions shape: {predictions.shape}, Labels shape: {labels.shape}")
    
    # Move tensors to CPU if they're on GPU before converting to numpy
    if isinstance(predictions, torch.Tensor):
        print("Converting predictions from torch tensor to numpy")
        predictions = predictions.detach().cpu().numpy()
    if isinstance(labels, torch.Tensor):
        print("Converting labels from torch tensor to numpy")
        labels = labels.detach().cpu().numpy()
    
    # Extract the predictions (get the most likely token at each position)
    predictions = np.argmax(predictions, axis=-1)
    # print(f"After argmax, predictions shape: {predictions.shape}")
    
    # Replace padding token id (-100) with the tokenizer's pad token id
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    
    # Decode the predictions and labels back to text
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    
    # print(f"Batch size: {len(decoded_preds)} predictions, {len(decoded_labels)} labels")
    
    # Clean up the predictions and labels (remove extra whitespace)
    decoded_preds = [pred.strip() for pred in decoded_preds]
    decoded_labels = [label.strip() for label in decoded_labels]
    
    # Extract only the result part after "</think>" from predictions if present
    processed_preds = []
    think_delimiter_found = 0
    for pred in decoded_preds:
        parts = pred.split("</think>")
        if len(parts) > 1:
            # If "</think>" is found, take everything after it
            processed_preds.append(parts[1].strip())
            think_delimiter_found += 1
        else:
            # If "</think>" not found, use the whole prediction as-is
            processed_preds.append(pred)
    
    print(f"Found '</think>' delimiter in {think_delimiter_found}/{len(decoded_preds)} predictions")
    
    # For debugging: print a few examples of the processed predictions
    if len(processed_preds) > 0:
        print("\n=== Sample Predictions ===")
        for i in range(min(2, len(processed_preds))):
            # Print raw versions to better understand the issue
            print("====================Predictions====================")
            print(f"\nOriginal prediction {i} (raw): \n\n{repr(decoded_preds[i])}")
            print("====================Processed Predictions====================")
            print(f"\nProcessed prediction {i} (raw): \n\n{repr(processed_preds[i])}")
            print("====================Labels====================")
            print(f"\nReference {i} (raw): \n\n{repr(decoded_labels[i])}")
            
            # Clean the predictions by removing the repeated periods at the beginning
            cleaned_pred = processed_preds[i]
            # Remove leading pattern of period + newline sequences
            while cleaned_pred.startswith('.\n'):
                cleaned_pred = cleaned_pred[2:].lstrip()
            # Also remove just a sequence of periods at the start
            cleaned_pred = cleaned_pred.lstrip('.')
            
            print(f"Cleaned prediction {i}: {cleaned_pred[:50]}...")
    
    # Add this code right after creating processed_preds list and before computing metrics

    # Clean the processed predictions to remove leading periods and newlines
    cleaned_processed_preds = []
    for pred in processed_preds:
        cleaned = pred
        # Remove leading pattern of period + newline sequences
        while cleaned.startswith('.\n'):
            cleaned = cleaned[2:].lstrip()
        # Also remove just a sequence of periods at the start
        cleaned = cleaned.lstrip('.')
        cleaned_processed_preds.append(cleaned.strip())

    # Use cleaned_processed_preds instead of processed_preds for metrics
    if compute_result:
        print("\n=== Computing final metrics ===")
        # Calculate ROUGE scores
        rouge_results = compute_metrics.rouge_metric.compute(
            predictions=cleaned_processed_preds,
            references=decoded_labels,
            use_stemmer=True
        )
        
        # Calculate BLEU scores
        references_for_bleu = [[label] for label in decoded_labels]
        bleu_results = compute_metrics.bleu_metric.compute(
            predictions=cleaned_processed_preds,
            references=references_for_bleu
        )
        
        # Combine metrics
        results = {
            "rouge1": rouge_results["rouge1"],
            "rouge2": rouge_results["rouge2"],
            "rougeL": rouge_results["rougeL"],
            "bleu": bleu_results["bleu"]
        }
        
        print(f"Final metrics: {results}")
        # exit()
        return results
    
    # print(f"Skipping final metric computation (intermediate batch) and compute_result is {compute_result}")
    # exit()
    # For intermediate batches, return empty dict
    return {}


# Load dataset
print("Loading dataset...")
try:
    # Load your custom dataset
    dataset = load_dataset('json', data_files='/home/wzhangeb/lancet/slm/dialog_dataset.json')['train']
    
    # Split into train/eval (95%/5%)
    splits = dataset.train_test_split(test_size=0.1, seed=42)
    full_dataset = splits['train']  # 95% for training
    full_eval_dataset = splits['test']  # 5% for evaluation
    
    DEBUG_MODE = True
    if DEBUG_MODE:
        dataset = full_dataset.select(range(5))
        eval_dataset = full_eval_dataset.select(range(1))
        print("=========================keys=========================")
        print(eval_dataset[0].keys())
        print("=========================artical=========================")
        print(eval_dataset[0]['article'])
        print("=========================highlights=========================")
        print(eval_dataset[0]['highlights'])
        print("=========================id=========================")
        print(eval_dataset[0]['id'])
    else:
        dataset = full_dataset
        eval_dataset = full_eval_dataset

except Exception as e:
    print(f"Error loading dataset: {e}")
    exit(1)

# Load DeepSeek model and tokenizer
print("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto" if torch.cuda.is_available() else "cpu",  # Automatically allocate to GPU
    torch_dtype=torch.bfloat16  # Use BF16 to reduce memory usage
)

# Define data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False  # Set to False since we're using CausalLM not MLM
)

# Configure LoRA
print("Configuring LoRA...")
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    inference_mode=False,
    r=8,  # LoRA rank
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "v_proj"]  # Adjust target modules according to the model architecture
)
model = get_peft_model(model, peft_config)

# Preprocess data
print("Preprocessing data...")
tokenized_dataset = dataset.map(preprocess_function, batched=True, num_proc=20)
eval_tokenized_dataset = eval_dataset.map(preprocess_function, batched=True, num_proc=20)

# Remove original fields (optional)
tokenized_dataset = tokenized_dataset.remove_columns(["article", "highlights", "id"])
eval_tokenized_dataset = eval_tokenized_dataset.remove_columns(["article", "highlights", "id"])

if False:
    print("Tokenized Dataset:")
    for key, value in tokenized_dataset[0].items():
        print(f"\nField: {key}")
        print(f"Type: {type(value)}")
        print(f"Length: {len(value)}")
        if isinstance(value, list):
            print(f"First element type: {type(value[0])}")
            print(f"First element length: {len(value[0]) if isinstance(value[0], list) else 'N/A'}")
            print(f"Example: {value[0]}")

    print("\nEval Tokenized Dataset:")
    sample_batch = [tokenized_dataset[i] for i in range(2)]  # Convert Dataset slice to list of dicts
    collated_batch = data_collator(sample_batch)
    print("Collated Batch:", collated_batch)
    print("Type of Collated Batch:", type(collated_batch))



# Set format to PyTorch tensors
tokenized_dataset.set_format(type="torch")
eval_tokenized_dataset.set_format(type="torch")

# Set training arguments
print("Setting training arguments...")
training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=1,  # Adjust batch size according to memory
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=1,  # Gradient accumulation steps
    num_train_epochs=1,
    weight_decay=0.01,
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=10,
    fp16=True if torch.cuda.is_available() else False,  # Enable FP16
    report_to="tensorboard",  # Use TensorBoard for logging
    batch_eval_metrics=True,  # Enable batch evaluation metrics
    include_for_metrics=["loss", "inputs"]  # Include these in metrics calculation
)


# Define Trainer with custom loss function and compute_metrics
print("Defining Trainer...")
trainer = Trainer(
    model=model,                            # The model to train
    args=training_args,                     # Training arguments (batch size, learning rate, etc.)
    data_collator=data_collator,            # Data collator for batching samples
    train_dataset=tokenized_dataset,        # Training dataset
    eval_dataset=eval_tokenized_dataset,    # Evaluation dataset
    tokenizer=tokenizer,                    # Tokenizer for text processing
    compute_loss_func=custom_loss,          # Custom loss function to focus only on result part
    compute_metrics=compute_metrics         # Added: GLUE metrics computation
)

# Start training
print("Starting training...")
trainer.train()

# Save model
print("Saving model...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
save_dir = f"./fine_tuned_model_{tag.replace('-', '_')}"
model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"Model fine-tuning completed and saved to {save_dir}.")