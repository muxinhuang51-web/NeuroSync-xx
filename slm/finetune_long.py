import os
from datasets import load_dataset, Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
import torch
from datetime import datetime
from transformers import DataCollatorForLanguageModeling

# Set model name
tag = "Qwen-1.5B"
model_name = f"deepseek-ai/DeepSeek-R1-Distill-{tag}"

# Set GPU environment
os.environ["CUDA_VISIBLE_DEVICES"] = "0,2"  # Use GPU 0 and 2

# Maximum sequence length supported by the model
MAX_WORD_LENGTH = 1024  # Adjust according to the model's maximum length
MAX_LENGTH = 1500  # Maximum length of each padding
MAX_LENGTH_OUT = 128  # Maximum length of each padding
STRIDE = 256  # Overlap between chunks

def chunk_data(dataset):
    """
    Chunks the articles into smaller pieces before tokenization.

    Args:
        dataset (datasets.Dataset): The input dataset containing 'article' and 'highlights' fields.

    Returns:
        datasets.Dataset: Processed dataset with chunked articles and repeated summaries.
    """
    all_articles = []
    all_summaries = []

    for idx in range(len(dataset)):
        article = dataset[idx]['article']
        summary = dataset[idx]['highlights']

        # Split article into chunks
        articles = [article[i:i+MAX_LENGTH] for i in range(0, len(article), MAX_LENGTH - STRIDE)]
        summaries = [summary] * len(articles)

        all_articles.extend(articles)
        all_summaries.extend(summaries)

    return Dataset.from_dict({"article": all_articles, "highlights": all_summaries})


def preprocess_function(examples):
    """
    Data preprocessing function to convert the CNN/DailyMail dataset into a format acceptable by the model.
    
    Args:
        examples (dict): Dictionary containing 'article' and 'highlights' fields.
    
    Returns:
        dict: Preprocessed inputs and labels.
    """
    inputs = [f"Please Generate an abstract for the following artical:\n\n{doc}" for doc in examples["article"]]
    targets = [summary for summary in examples["highlights"]]

    # Construct input format: only include article content
    model_inputs = tokenizer(
        inputs,
        max_length=512,  # Adjust according to the model's maximum length (DeepSeek model supports longer sequences)
        truncation=True,
        padding="max_length"
    )
    
    # Construct labels: only include summary content
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            targets,
            max_length=128,  # Summary length is usually shorter, adjust as needed
            truncation=True,
            padding="max_length"
        )["input_ids"]
    
    # Add labels to model inputs
    model_inputs["labels"] = labels

    # Print model inputs for debugging
    if True:
        for key, value in model_inputs.items():
            print(f"\nField: {key}")
            print(f"Type: {type(value)}")
            print(f"Length: {len(value)}")
            if isinstance(value, list):
                print(f"First element type: {type(value[0])}")
                print(f"First element length: {len(value[0]) if isinstance(value[0], list) else 'N/A'}")
                print(f"Example: {value[0]}")

    return model_inputs

# Load dataset
print("Loading dataset...")
try:
    dataset = load_dataset("cnn_dailymail", "3.0.0", split="train[:100]")  # Training set
    eval_dataset = load_dataset("cnn_dailymail", "3.0.0", split="validation[:10]")  # Validation set
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

# Chunk the dataset
print("Chunking dataset...")
dataset = chunk_data(dataset)
eval_dataset = chunk_data(dataset)

print("Preprocessing data...")
dataset = dataset.map(preprocess_function, batched=True, num_proc=1)
eval_dataset = eval_dataset.map(preprocess_function, batched=True, num_proc=1)


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
tokenized_dataset = dataset.map(preprocess_function, batched=True, num_proc=10)
eval_tokenized_dataset = eval_dataset.map(preprocess_function, batched=True, num_proc=10)

# Remove original fields (optional)
tokenized_dataset = tokenized_dataset.remove_columns(["article", "highlights"])
eval_tokenized_dataset = eval_tokenized_dataset.remove_columns(["article", "highlights"])

# Set format to PyTorch tensors
tokenized_dataset.set_format(type="torch")
eval_tokenized_dataset.set_format(type="torch")

# Set training arguments
print("Setting training arguments...")
training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=8,  # Adjust batch size according to memory
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=4,  # Gradient accumulation steps
    num_train_epochs=3,
    weight_decay=0.01,
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=10,
    fp16=True if torch.cuda.is_available() else False,  # Enable FP16
    report_to="tensorboard"  # Use TensorBoard for logging
)

# Define data collector
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False  # CausalLM does not use masked language modeling
)

# Define Trainer
print("Defining Trainer...")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    eval_dataset=eval_tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator
)

# Start training
print("Starting training...")
trainer.train()

# Save model
print("Saving model...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
save_dir = f"./fine_tuned_model_{tag.replace('-', '_')}_long"
model.save_pretrained(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"Model fine-tuning completed and saved to {save_dir}.")
