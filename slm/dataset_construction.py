import os
import json
from datasets import Dataset, load_dataset
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

class DialogDatasetBuilder:
    """
    A class to build a dataset from dialog history and processed interactions.
    The resulting dataset will have 'article' and 'highlights' fields similar to CNN/DailyMail.
    """
    
    def __init__(
        self,
        dialog_history_dir: str = "/home/wzhangeb/lancet/slm/dialog_history_run",
        processed_interactions_dir: str = "/home/wzhangeb/lancet/slm/processed_interactions_eng_demo",
        output_file: str = "dialog_dataset.json"
    ):
        """
        Initialize the dataset builder.
        
        Args:
            dialog_history_dir: Directory containing user_x.json dialog history files
            processed_interactions_dir: Directory containing user_x folders with results_round_x.json files
            output_file: Path to save the resulting dataset
        """
        self.dialog_history_dir = dialog_history_dir
        self.processed_interactions_dir = processed_interactions_dir
        self.output_file = output_file
        
        # Templates for constructing inputs and outputs
        # Template for first round (no previous data)
        self.first_round_input_template = """
        我需要你基于用户输入的massage生成intent tree, task graph, mapping.他们具体的定义如下

        ## Intent Tree
        意图树是一种层次化的结构，用于表示用户通过对话系统希望达成的目标及其细分的任务。根节点代表总体意图，子节点代表为实现该总体意图所需的各个具体步骤或任务。

        ### 构建方法
        1. **概括用户的总体意图**：分析用户输入，提取出用户的总体目标。
        2. **抽象具体的子任务或要求**：从用户输入中抽象出具体的子任务或要求，并将其组织成树形结构。
        3. **形成树状图**：将这些意图和子意图按层级关系组织起来，形成一个树状图。

        示例
        intent_tree = {{
            "写一个爬虫程序，爬取指定URL的内容并保存到本地": {{
            "爬取文本内容并保存": {{}},
            "爬取图像内容并保存": {{}}
            }}
        }}

        ## Task Graph
        任务图是一种有向图结构，用来展示代码执行过程中的任务流及各任务间的依赖关系。节点代表任务，边代表任务之间的依赖关系，包括数据流向和类型。

        ### 构建方法
        1. **分析代码**：从代码中提取所有需要执行的任务，并为其生成简短描述。
        2. **构建图结构**：使用节点表示每个任务，使用边表示任务之间的依赖关系，并标注数据流动的方向和类型。

        示例：
        task_graph = {{
            "nodes": [
            {{"id": "Node1", "description": "发起HTTP请求以获取目标网页的内容"}},
            {{"id": "Node2", "description": "使用BeautifulSoup解析HTML文档"}},
            {{"id": "Node3", "description": "提取文本内容并保存到文件中"}},
            {{"id": "Node4", "description": "在HTML文档中查找所有的图像URL"}},
            {{"id": "Node5", "description": "下载图像并保存到本地文件夹中"}},
            {{"id": "Node6", "description": "创建保存内容的本地文件夹（如果不存在）"}}
            ],
            "links": [
            {{"source": "Node1", "target": "Node2", "type": "parse"}},
            {{"source": "Node2", "target": "Node3", "type": "extractText"}},
            {{"source": "Node2", "target": "Node4", "type": "findImages"}},
            {{"source": "Node4", "target": "Node5", "type": "downloadImages"}},
            {{"source": "Node6", "target": "Node3", "type": "saveToFolder"}},
            {{"source": "Node6", "target": "Node5", "type": "saveToFolder"}}
            ]
        }}

        ## Mapping
        映射是指意图树中的每个节点与任务图中相应子图之间的一对一对应关系。确保每个意图都有明确的任务集来实现它。

        ### 构建方法
        1. **匹配子图节点**：针对意图树中的每个节点，在任务图中找到对应的子图（仅包含直接相关的部分）。
        2. **确保一一对应**：每个意图树节点应唯一对应一个任务图子图，反之亦然。

        示例：
        mapping = {{
            "写一个爬虫程序，爬取指定URL的内容并保存到本地": {{
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6"]
            }},
            "爬取文本内容并保存": {{
            "nodes": ["Node1", "Node2", "Node3", "Node6"]
            }},
            "爬取图像内容并保存": {{
            "nodes": ["Node1", "Node2", "Node4", "Node5", "Node6"]
            }}
        }}

        # 请基于下边的User Prompt创建对应的intent tree, task graph, mapping:
        {user_input}"
        """

        
        # Template for subsequent rounds (includes previous data)
        self.subsequent_round_input_template = """
        我需要你基于用户输入的massage修改上一轮中的intent tree, task graph, mapping.他们具体的定义如下，修改后的结果保持和上一轮一样的格式

        ## Intent Tree（意图树）
        意图树是一种层次化的结构，用于表示用户通过对话系统希望达成的目标及其细分的任务。根节点代表总体意图，子节点代表为实现该总体意图所需的各个具体步骤或任务。

        ### 构建方法
        1. **概括用户的总体意图**：分析用户输入，提取出用户的总体目标。
        2. **抽象具体的子任务或要求**：从用户输入中抽象出具体的子任务或要求，并将其组织成树形结构。
        3. **形成树状图**：将这些意图和子意图按层级关系组织起来，形成一个树状图。

        ## Task Graph（任务图）
        任务图是一种有向图结构，用来展示代码执行过程中的任务流及各任务间的依赖关系。节点代表任务，边代表任务之间的依赖关系，包括数据流动的方向和类型。

        ### 构建方法
        1. **分析代码**：从代码中提取所有需要执行的任务，并为其生成简短描述。
        2. **构建图结构**：使用节点表示每个任务，使用边表示任务之间的依赖关系，并标注数据流动的方向和类型。

        ## Mapping（映射）
        映射是指意图树中的每个节点与任务图中相应子图之间的一对一对应关系。确保每个意图都有明确的任务集来实现它。

        ### 构建方法
        1. **匹配子图节点**：针对意图树中的每个节点，在任务图中找到对应的子图（仅包含直接相关的部分）。
        2. **确保一一对应**：每个意图树节点应唯一对应一个任务图子图，反之亦然。


        # 历史信息
        ### User message:
        {user_input}

        ### Previous intent tree:
        {prev_intent_tree}

        ### Previous task graph:
        {prev_task_graph}

        ### Previous mapping:
        {prev_mapping}
        
        """
        
        self.output_template = """
        ### Intent Tree:
        {intent_tree}

        ### Task Graph:
        {task_graph}

        ### Mapping:
        {mapping}
            """
    
    def load_dialog_history(self, user_index: int) -> dict:
        """Load dialog history for a specific user."""
        filepath = os.path.join(self.dialog_history_dir, f"user_{user_index}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dialog history file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_processed_interaction(self, user_index: int, round_index: int) -> Optional[dict]:
        """Load processed interaction for a specific user and round."""
        user_dir = os.path.join(self.processed_interactions_dir, f"user_{user_index}")
        filepath = os.path.join(user_dir, f"results_round_{round_index}.json")
        
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def build_dataset(self) -> Dataset:
        """Build the dataset from dialog history and processed interactions."""
        data = {
            "id": [],
            "article": [],
            "highlights": []
        }
        
        # List all user files in dialog_history_dir
        user_files = [f for f in os.listdir(self.dialog_history_dir) if f.startswith("user_") and f.endswith(".json")]
        
        for user_file in user_files:
            user_index = int(user_file.replace("user_", "").replace(".json", ""))
            

            dialog_history = self.load_dialog_history(user_index)
            num_rounds = len(dialog_history["dialogue"])
            
            for round_idx in range(num_rounds):  # Include round 0
                # Get current user input
                user_input = dialog_history["dialogue"][round_idx]["user_input"]
                
                # Get current round processed interaction data
                current_round_data = self.load_processed_interaction(user_index, round_idx)
                
                # Skip if missing current round data
                if not current_round_data:
                    continue
                
                # For the first round, use none or empty values for history
                if round_idx == 0:
                    # Construct input (article) for first round
                    article = self.first_round_input_template.format(
                        user_input=user_input
                    )
                    # print("\n\nFirst ROUDN\n", article)
                else:
                    # Get previous round processed interaction data
                    prev_round_data = self.load_processed_interaction(user_index, round_idx - 1)
                    
                    # Skip if missing previous round data
                    if not prev_round_data:
                        continue
                    
                    # Safely get previous data with proper string conversion
                    prev_intent_tree = json.dumps(prev_round_data.get("intent_tree", {}), ensure_ascii=False)
                    prev_task_graph = json.dumps(prev_round_data.get("task_graph", {}), ensure_ascii=False)
                    prev_mapping = json.dumps(prev_round_data.get("mapping", {}), ensure_ascii=False)
                    
                    # Construct input (article) for subsequent rounds
                    article = self.subsequent_round_input_template.format(
                        user_input=user_input,
                        prev_intent_tree=prev_intent_tree,
                        prev_task_graph=prev_task_graph,
                        prev_mapping=prev_mapping
                    )
                    # print("\n\nSECOND ROUDN\n", article)
                # Safely get current data with proper string conversion
                intent_tree = json.dumps(current_round_data.get("intent_tree", {}), ensure_ascii=False)
                task_graph = json.dumps(current_round_data.get("task_graph", {}), ensure_ascii=False)
                mapping = json.dumps(current_round_data.get("mapping", {}), ensure_ascii=False)
                
                # Construct output (highlights)
                highlights = self.output_template.format(
                    intent_tree=intent_tree,
                    task_graph=task_graph,
                    mapping=mapping
                )
                
                # print("\n\nLABEL\n: ", highlights)
                
                # Add to dataset
                data["id"].append(f"user_{user_index}_round_{round_idx}")
                data["article"].append(article)
                data["highlights"].append(highlights)
        # exit()    


        # Check if we have any data
        if len(data["id"]) == 0:
            print("Warning: No valid data was collected. Dataset will be empty.")
            # Create a minimal empty dataset to avoid errors
            data["id"].append("empty")
            data["article"].append("")
            data["highlights"].append("")
        
        # Create dataset
        df = pd.DataFrame(data)
        dataset = Dataset.from_pandas(df)
        
        # Save dataset to file
        dataset.to_json(self.output_file)
        
        print(f"Dataset created with {len(dataset)} samples and saved to {self.output_file}")
        return dataset

    def get_dataset_statistics(self) -> Dict[str, Any]:
        """Get statistics about the dataset."""
        if not os.path.exists(self.output_file):
            raise FileNotFoundError(f"Dataset file not found: {self.output_file}")
        
        dataset = Dataset.from_json(self.output_file)
        
        # Calculate statistics
        num_samples = len(dataset)
        
        if num_samples > 0:
            # Calculate article lengths
            article_lengths = [len(article.split()) for article in dataset["article"]]
            avg_article_len = sum(article_lengths) / num_samples
            min_article_len = min(article_lengths)
            max_article_len = max(article_lengths)
            
            # Calculate highlight lengths
            highlight_lengths = [len(highlight.split()) for highlight in dataset["highlights"]]
            avg_highlights_len = sum(highlight_lengths) / num_samples
            min_highlights_len = min(highlight_lengths)
            max_highlights_len = max(highlight_lengths)
        else:
            avg_article_len = min_article_len = max_article_len = 0
            avg_highlights_len = min_highlights_len = max_highlights_len = 0
        
        # Count samples per user
        user_counts = {}
        for id_str in dataset["id"]:
            user_id = id_str.split("_")[1]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        return {
            "num_samples": num_samples,
            "avg_article_len": avg_article_len,
            "min_article_len": min_article_len,
            "max_article_len": max_article_len,
            "avg_highlights_len": avg_highlights_len,
            "min_highlights_len": min_highlights_len,
            "max_highlights_len": max_highlights_len,
            "samples_per_user": user_counts,
            "num_users": len(user_counts)
        }

    def get_shortest_sample(self, by_field='article'):
        """Get the shortest sample in the dataset based on word count of a specific field.
        
        Args:
            by_field: Field to determine shortest ('article' or 'highlights')
            
        Returns:
            Dictionary containing the shortest sample
        """
        if not os.path.exists(self.output_file):
            raise FileNotFoundError(f"Dataset file not found: {self.output_file}")
        
        dataset = Dataset.from_json(self.output_file)
        
        if len(dataset) == 0:
            return {"id": "", "article": "", "highlights": ""}
        
        # Find the index of the shortest sample
        lengths = [len(sample[by_field].split()) for sample in dataset]
        shortest_idx = lengths.index(min(lengths))
        
        # Get the shortest sample
        shortest = dataset[shortest_idx]
        return {
            "id": shortest["id"],
            "article": shortest["article"],
            "highlights": shortest["highlights"],
            "article_length": len(shortest["article"].split()),
            "highlights_length": len(shortest["highlights"].split())
        }

    def get_longest_sample(self, by_field='article'):
        """Get the longest sample in the dataset based on word count of a specific field.
        
        Args:
            by_field: Field to determine longest ('article' or 'highlights')
            
        Returns:
            Dictionary containing the longest sample
        """
        if not os.path.exists(self.output_file):
            raise FileNotFoundError(f"Dataset file not found: {self.output_file}")
        
        dataset = Dataset.from_json(self.output_file)
        
        if len(dataset) == 0:
            return {"id": "", "article": "", "highlights": ""}
        
        # Find the index of the longest sample
        lengths = [len(sample[by_field].split()) for sample in dataset]
        longest_idx = lengths.index(max(lengths))
        
        # Get the longest sample
        longest = dataset[longest_idx]
        return {
            "id": longest["id"],
            "article": longest["article"],
            "highlights": longest["highlights"],
            "article_length": len(longest["article"].split()),
            "highlights_length": len(longest["highlights"].split())
        }

    def get_dataset_distributions(self) -> Dict[str, Any]:
        """Get distributions of various attributes in the dataset.
        
        Returns:
            Dictionary containing distributions for different metrics
        """
        if not os.path.exists(self.output_file):
            raise FileNotFoundError(f"Dataset file not found: {self.output_file}")
        
        dataset = Dataset.from_json(self.output_file)
        
        if len(dataset) == 0:
            return {"error": "Empty dataset"}
        
        distributions = {}
        
        # Distribution of samples per user
        user_counts = {}
        for id_str in dataset["id"]:
            if id_str == "empty":
                continue
            user_id = id_str.split("_")[1]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        distributions["samples_per_user"] = user_counts
        
        # Distribution of rounds per user
        round_counts = {}
        for id_str in dataset["id"]:
            if id_str == "empty" or "_round_" not in id_str:
                continue
            
            user_id = id_str.split("_")[1]
            round_num = int(id_str.split("_round_")[1])
            
            if user_id not in round_counts:
                round_counts[user_id] = []
            round_counts[user_id].append(round_num)
        
        # Convert to max round per user
        max_rounds = {user: max(rounds) + 1 for user, rounds in round_counts.items()}
        distributions["max_rounds_per_user"] = max_rounds
        
        # Distribution of article lengths in different bins
        article_lengths = [len(article.split()) for article in dataset["article"]]
        highlight_lengths = [len(highlight.split()) for highlight in dataset["highlights"]]
        
        # Create bins for article lengths
        bins = [0, 200, 400, 600, 800, 1200, float('inf')]
        article_length_dist = {f"{bins[i]}-{bins[i+1]}": 0 for i in range(len(bins)-1)}
        
        for length in article_lengths:
            for i in range(len(bins)-1):
                if bins[i] <= length < bins[i+1]:
                    article_length_dist[f"{bins[i]}-{bins[i+1]}"] += 1
                    break
        
        distributions["article_length_distribution"] = article_length_dist
        
        # Create bins for highlight lengths
        highlight_bins = [0, 200, 400, 600, 800, 1200, float('inf')]
        highlight_length_dist = {f"{highlight_bins[i]}-{highlight_bins[i+1]}": 0 for i in range(len(highlight_bins)-1)}
        
        for length in highlight_lengths:
            for i in range(len(highlight_bins)-1):
                if highlight_bins[i] <= length < highlight_bins[i+1]:
                    highlight_length_dist[f"{highlight_bins[i]}-{highlight_bins[i+1]}"] += 1
                    break
        
        distributions["highlight_length_distribution"] = highlight_length_dist
        
        return distributions

if __name__ == "__main__":
    # Create dataset builder
    builder = DialogDatasetBuilder(
        dialog_history_dir="/home/wzhangeb/lancet/DatasetGeneration/dialog_history_run",
        processed_interactions_dir="/home/wzhangeb/lancet/DatasetGeneration/processed_interactions_eng_1",
        output_file="dialog_dataset_cal_web.json"
    )
    
    # Build dataset
    dataset = builder.build_dataset()
    
    # Print statistics
    stats = builder.get_dataset_statistics()
    print("\nDataset Statistics:")
    print(f"Total samples: {stats['num_samples']}")
    print(f"Input length (words): min={stats['min_article_len']}, avg={stats['avg_article_len']:.2f}, max={stats['max_article_len']}")
    print(f"Output length (words): min={stats['min_highlights_len']}, avg={stats['avg_highlights_len']:.2f}, max={stats['max_highlights_len']}")
    print(f"Number of users: {stats['num_users']}")
    
    # Print a sample
    if len(dataset) > 0:
        print("\nSample data:")
        sample = dataset[0]
        print(f"ID: {sample['id']}")
        print(f"Input (first 200 chars): {sample['article'][:200]}...")
        print(f"Output (first 200 chars): {sample['highlights'][:200]}...")
    
    print("\nDataset is ready for fine-tuning with format compatible with CNN/DailyMail.")

    # Load your custom dataset
    dataset = load_dataset('json', data_files='dialog_dataset.json')
    
    # Split into train/validation/test (e.g., 80%/10%/10%)
    splits = dataset['train'].train_test_split(test_size=0.2, seed=42)
    train_dataset = splits['train']
    test_val = splits['test'].train_test_split(test_size=0.5, seed=42)
    val_dataset = test_val['train']
    test_dataset = test_val['test']

    # Example usage in your __main__ section:
    # After building the dataset
    dataset = builder.build_dataset()

    # # Get and print the shortest sample by article length
    # shortest_article = builder.get_shortest_sample(by_field='article')
    # print("\nShortest sample by article length:")
    # print(f"ID: {shortest_article['id']}")
    # print(f"Article length (words): {shortest_article['article_length']}")
    # print(f"Article: {shortest_article['article']}")

    # # Get and print the shortest sample by highlights length
    # shortest_highlights = builder.get_shortest_sample(by_field='highlights')
    # print("\nShortest sample by highlights length:")
    # print(f"ID: {shortest_highlights['id']}")
    # print(f"Highlights length (words): {shortest_highlights['highlights_length']}")
    # print(f"Highlights: {shortest_highlights['highlights']}")

    # Add this to your __main__ section
    distribution_stats = builder.get_dataset_distributions()

    print("\nDistribution Statistics:")
    print("\nSamples per User:")
    for user, count in distribution_stats["samples_per_user"].items():
        print(f"User {user}: {count} samples")

    print("\nMax Rounds per User:")
    for user, max_round in distribution_stats["max_rounds_per_user"].items():
        print(f"User {user}: {max_round} rounds")

    print("\nArticle Length Distribution:")
    for length_range, count in distribution_stats["article_length_distribution"].items():
        print(f"{length_range} words: {count} samples")

    print("\nHighlight Length Distribution:")
    for length_range, count in distribution_stats["highlight_length_distribution"].items():
        print(f"{length_range} words: {count} samples")

    # Add to the __main__ section
    # Get and print the longest sample by article length
    longest_article = builder.get_longest_sample(by_field='article')
    print("\nLongest sample by article length:")
    print(f"ID: {longest_article['id']}")
    print(f"Article length (words): {longest_article['article_length']}")
    print(f"Article (first 100 words): {' '.join(longest_article['article'].split()[:1200])}...")

    # Get and print the longest sample by highlights length
    longest_highlights = builder.get_longest_sample(by_field='highlights')
    print("\nLongest sample by highlights length:")
    print(f"ID: {longest_highlights['id']}")
    print(f"Highlights length (words): {longest_highlights['highlights_length']}")
    print(f"Highlights (first 100 words): {' '.join(longest_highlights['highlights'].split()[:1200])}...")

    # Add to the __main__ section
    # Get and print the longest sample by article length
    longest_article = builder.get_shortest_sample(by_field='article')
    print("\nLongest sample by article length:")
    print(f"ID: {longest_article['id']}")
    print(f"Article length (words): {longest_article['article_length']}")
    print(f"Article (first 100 words): {' '.join(longest_article['article'].split()[:1200])}...")

    # Get and print the longest sample by highlights length
    longest_highlights = builder.get_shortest_sample(by_field='highlights')
    print("\nLongest sample by highlights length:")
    print(f"ID: {longest_highlights['id']}")
    print(f"Highlights length (words): {longest_highlights['highlights_length']}")
    print(f"Highlights (first 100 words): {' '.join(longest_highlights['highlights'].split()[:1200])}...")