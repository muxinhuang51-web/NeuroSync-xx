from transformers import pipeline
import os
import torch
import time
import json

# Set available GPUs
os.environ["CUDA_VISIBLE_DEVICES"] = "0, 2"

context_1 = """
请你为下边的内容生成摘要，请控制在40词左右，请你只返回给我生成的摘要，不要返回其他内容。

内容如下：{
Anker 2023年底公司人数4017人。假设领导分50%，领导占比10%，那么等于剩下3600（4017*90%）人分4亿（8*50%），人均11万，确实还是不错的。假设奖金占年度收入的30%，年百万收入，大概年终奖30万，494人破百万，那么就按每个人年终奖30万，这些人分了1.48亿，不过百万是基数，排个数按50万算，那么这些人分了2.47亿，剩下的5.53亿3523人分，大概每人分15.7万。不管那个算法，平均下来估计每个人年终奖过10万，对于一家在湖南的公司，这个奖金额度真的还是很牛逼的。
}

"""

context = """
Please generate a summary for the following content. Please limit it to about 40 words. Please only return the generated summary to me, and do not return other content.

The content is as follows: {
Anker will have 4017 employees at the end of 2023. Assuming that the leader gets 50% and the leader accounts for 10%, then the remaining 3600 (4017*90%) people will share 400 million (8*50%), with an average of 110,000 per person, which is indeed good. Assuming that the bonus accounts for 30% of the annual income, the annual income is one million, and the year-end bonus is about 300,000. 494 people broke the million, then according to the year-end bonus of 300,000 per person, these people will share 148 million, but the million is the base number, and the number of rows is calculated as 500,000, so these people will share 247 million, and the remaining 553 million will be shared by 3523 people, about 157,000 per person. Regardless of the algorithm, it is estimated that each person's year-end bonus will exceed 100,000 on average. For a company in Hunan, this bonus amount is really awesome.
}
"""

# set model name
# "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B", "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
# "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"， "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"

# Original model name 
# "Qwen/Qwen2.5-7B", "Qwen/Qwen2.5-1.5B", "NousResearch/DeepHermes-3-Llama-3-8B-Preview"

model = "Qwen/Qwen2.5-7B"
device_map = "auto" #if torch.cuda.is_available() else "cpu"

# Load pipeline
pipe = pipeline("text-generation", model=model, device_map=device_map)
print("Model loaded successfully.")
time.sleep(60)
print("Start to generate text...")
# Set generation parameters
# Configuration for generation parameters, including all common parameters
start = time.time()
print("Start to generate text...")
result = pipe(
    context,
    max_new_tokens=5000,        # Set maximum number of tokens to generate (excluding input)
    # min_length=10,              # Set minimum length of generated text
    # do_sample=True,             # Enable sampling to increase diversity
    # temperature=0.7,            # Control randomness of generation (lower = more deterministic, higher = more diverse)
    # top_k=50,                   # Sample from top-k highest probability tokens
    # top_p=0.9,                  # Nucleus sampling: sample from tokens comprising top-p cumulative probability
    # num_beams=4,                # Number of beams for beam search (higher values optimize results but increase computation)
    # early_stopping=True,        # Stop early when all beams are complete
    # repetition_penalty=1.2,     # Penalize repeated tokens to avoid repetitive content
    # length_penalty=1.5,         # Penalize text length (>1 encourages longer text, <1 encourages shorter text)
    # no_repeat_ngram_size=3,     # Prevent repeating n-gram sequences to avoid repetitive segments
    # pad_token_id=0,             # Specify padding token ID
    # eos_token_id=2,             # Specify end-of-sequence token ID
    # bad_words_ids=[[123], [456]],  # List of token IDs not to generate
    # return_full_text=False,     # Whether to return the full text (including input)
    # truncation=True             # Whether to truncate input text to fit model's maximum context length
)
print("Time cost: ", time.time()-start)

# Get the generated text result
generated_text = result[0]['generated_text']

# Remove the original input portion, keeping only the model-generated part
input_len = len(context)
model_output = generated_text[input_len:].strip()

# Find the thinking end marker
parts = model_output.split("</think>")

if len(parts) > 1:
    # If thinking markers are found
    thinking = parts[0].strip()
    summary = parts[1].strip()
else:
    # If no markers found, try other splitting methods
    # Assume the last paragraph might be the summary
    paragraphs = model_output.split("\n\n")
    if paragraphs and len(paragraphs) > 1:
        summary = paragraphs[-1].strip()
        thinking = "\n\n".join(paragraphs[:-1]).strip()
    else:
        # If no clear paragraphs, treat the entire output as summary
        summary = model_output
        thinking = ""

# Output original results and separated components
print("\n=== Original Output ===")
print(model_output)

print("\n=== Thinking Process ===")
print(thinking)

print("\n=== Final Summary ===")
print(summary)