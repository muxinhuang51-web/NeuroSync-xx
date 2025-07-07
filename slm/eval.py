from datasets import load_dataset
import evaluate
from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch, os
from tqdm import tqdm

# Set GPU environment
os.environ["CUDA_VISIBLE_DEVICES"] = "0,2"  # Use GPU 0 and 2
device_map = "auto" if torch.cuda.is_available() else "cpu"

# Load evaluation metrics
metric_bleu = evaluate.load("bleu")
metric_rouge = evaluate.load("rouge")

# Load the fine-tuned model
model_dir = "./fine_tuned_model_Qwen_1.5B"  # Update this path to your saved model directory
tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    device_map="auto" if torch.cuda.is_available() else "cpu",  # 自动分配到 GPU
    torch_dtype=torch.bfloat16  # 使用 BF16 减少内存占用
)
generator = pipeline("text2text-generation", model=model, tokenizer=tokenizer)

# Load evaluation dataset
eval_dataset = load_dataset("cnn_dailymail", "3.0.0", split="validation[:10]")

# Preprocess data
def preprocess_function(examples):
    inputs = [doc for doc in examples["article"]]
    targets = [summary for summary in examples["highlights"]]

    model_inputs = tokenizer(
        inputs,
        max_length=512,
        truncation=True,
        padding="max_length"
    )
    
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            targets,
            max_length=128,
            truncation=True,
            padding="max_length"
        )["input_ids"]
    
    model_inputs["labels"] = labels
    return model_inputs

tokenized_dataset = eval_dataset.map(preprocess_function, batched=True, num_proc=10)
tokenized_dataset.set_format(type="torch")

# Generate predictions
predictions = []
references = []

print("Generating predictions...")
for example in tqdm(tokenized_dataset, desc="Generating predictions"):
    input_text = tokenizer.decode(example["input_ids"], skip_special_tokens=True)
    prediction = generator(input_text, max_length=1024)[0]["generated_text"]
    print("prediction: ", prediction)
    reference = tokenizer.decode(example["labels"], skip_special_tokens=True)
    
    predictions.append(prediction)
    references.append(reference)

print("We have generated predictions for all examples.")

# Compute BLEU and ROUGE scores
print("Computing BLEU and ROUGE scores...")
bleu_score = metric_bleu.compute(predictions=predictions, references=references)
rouge_score = metric_rouge.compute(predictions=predictions, references=references)

print(f"BLEU Score: {bleu_score}")
print(f"ROUGE Score: {rouge_score}")