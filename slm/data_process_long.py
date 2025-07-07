import os
from datasets import load_dataset, Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
import torch
from datetime import datetime
from transformers import DataCollatorForLanguageModeling



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

# Configuration dictionary for model parameters
config = {
    "MAX_WORD_LENGTH": 1024,  # Adjust according to the model's maximum length
    "MAX_LENGTH": 1500,  # Maximum length of each padding
    "MAX_LENGTH_OUT": 128,  # Maximum length of each padding
    "STRIDE": 256  # Overlap between chunks
}

def pre_dataset_model(tag, dataset, eval_dataset, data_config):
    # Set model name
    model_name = f"deepseek-ai/DeepSeek-R1-Distill-{tag}"



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

    # Preprocess data
    print("Preprocessing data...")
    tokenized_dataset = dataset.map(preprocess_function, batched=True, num_proc=1)
    eval_tokenized_dataset = eval_dataset.map(preprocess_function, batched=True, num_proc=1)

    # Remove original fields (optional)
    tokenized_dataset = tokenized_dataset.remove_columns(["article", "highlights"])
    eval_tokenized_dataset = eval_tokenized_dataset.remove_columns(["article", "highlights"])

    # Set format to PyTorch tensors
    tokenized_dataset.set_format(type="torch")
    eval_tokenized_dataset.set_format(type="torch")
