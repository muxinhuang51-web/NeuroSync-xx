# NeuroSync (lancet)

一套围绕 **意图树（Intent Tree）× 任务图（Task Graph）** 的代码生成交互研究系统。它把用户与大模型的代码生成对话，解析成「任务图 + 意图层级树 + 两者的映射」，并支持按用户关注点对图做递归化简，最终通过一个可视化前端进行交互。仓库同时包含配套的**合成数据生成**、**小模型蒸馏微调**与**用户实验（NASA-TLX / SUS）**分析代码。

> 本仓库为科研代码，内部代号 `lancet`（见部分 import 路径与硬编码的 `/home/wzhangeb/lancet/` 路径）。

---

## ⚠️ 安全提醒（务必先看）

`dataset/LLM_api.py` 中**硬编码了两个真实 API Key** 并已随本仓库推送到公开 GitHub：

- 阿里云 DashScope（qwen） key — 第 6、27 行
- 讯飞星火 MaaS（xdeepseekr1） key — 第 60、63、124 行

这两个 key 应视为**已泄露**，请到对应控制台**吊销并重新签发**，改用环境变量读取。改代码或重写 git 历史都无法撤回已公开的 key。

---

## 目录结构

| 目录 | 作用 |
| --- | --- |
| `dataset/` | 从原始对话构建「任务图 / 意图树 / 映射」，产出 `processed_interactions/`（70 个样本） |
| `DatasetGeneration/` | 基于多智能体辩论（debate）的**合成对话数据生成**，产出中/英/语音三个语料变体 |
| `Graph_Simplification/` | 图化简算法本体（按关注节点递归合并子图），**唯一有详细文档的模块** |
| `GraphUI/` 及其副本 | 交互前端：Flask 后端 + 原生 JS 图可视化（标题 `AI Graph Chat`） |
| `slm/` | 小模型 SFT / LoRA 微调、蒸馏、评测与推理 pipeline（DeepSeek-Llama-8B 等） |
| `data/` | 用户实验分析：NASA-TLX、SUS 问卷，配套图表与 xlsx |
| `task_test/` | 音频转写 / 微信等零散探索脚本（实验性） |

> ⚠️ `GraphUI` 当前存在约 16 份手工复制（`GraphUI copy N`、`..._beforezhao`/`_afterzhao` 等），以目录名充当版本管理。`GraphUI/` 与 `GraphUI_release/` 仅在 `Interface.py`、`graphUtils.js`、`main.js`、`index.html`、`styles.css` 上有差异，`server.py` 完全相同。建议后续合并为单份 + 配置开关。

---

## 核心概念

- **Task Graph**：描述代码执行的任务及依赖，节点为任务，边为数据流/依赖关系。
- **Intent Tree**：用户意图的层级树，根节点为总体意图，越深越具体。
- **Mapping**：为 Intent Tree 每个节点匹配 Task Graph 的一个子图，一一对应。
- **Graph Simplification**：给定「关注节点」列表，以意图树第二层为基准层递归化简——保留被关注分支的完整子图，将不含关注节点的分支合并为单个节点。详见 [`Graph_Simplification/Readme.md`](Graph_Simplification/Readme.md)。

---

## 快速开始

### 1. 环境依赖

仓库暂无 `requirements.txt`。主要依赖：

```bash
pip install flask flask-cors markdown markupsafe openai \
            torch transformers peft trl datasets evaluate \
            numpy scipy pandas networkx matplotlib seaborn \
            nltk tqdm requests beautifulsoup4 \
            SpeechRecognition pydub
```

### 2. 配置 API Key（吊销旧 key 后）

将 `dataset/LLM_api.py` 中的硬编码 key 改为环境变量：

```bash
export DASHSCOPE_API_KEY="你的新key"
export SPARK_API_KEY="你的新key"
```

### 3. 启动交互前端

```bash
cd GraphUI
python server.py      # Flask，默认端口 8001
# 浏览器打开 http://localhost:8001
```

> `server.py` 硬编码了 `CUDA_VISIBLE_DEVICES=2`，无对应 GPU 时请修改。

---

## 各模块用法

### 数据集构建（真实对话 → 图）

```bash
cd dataset
python graph_build.py    # raw_data/ → processed_interactions/
```

### 合成数据生成（多智能体辩论）

```bash
cd DatasetGeneration
python run_generation.py --total 300 --parallel 5   # 生成对话
python run_execuation.py --input <dialog_dir> --output <processed_dir>
# 或直接 bash run.sh
```
入口逻辑见 [`debate_based_generation.py`](DatasetGeneration/debate_based_generation.py) 的 `MultiAgentCodeGenSimulator`。

### 小模型微调与评测

```bash
cd slm
bash run_sft.sh          # LoRA SFT（默认 seq_len=4800, epochs=20 等）
python eval.py           # 评测
python pipeline.py       # 推理 pipeline
```

### 用户实验分析

```bash
cd data
python nasatlx.py        # NASA-TLX 分析
python sus.py            # SUS 问卷分析
```

---

## 已知问题 / 待清理

- 硬编码 API key（见上）。
- GraphUI 多份手工副本，需合并。
- 多处硬编码绝对路径 `/home/wzhangeb/lancet/...`，换机器需改。
- 提交了 `__pycache__/`、`*.out`、`*.log` 及 `GraphUI.zip` / `data.zip` 等产物，建议加入 `.gitignore`。
- 缺 `requirements.txt` / 环境锁定文件。
- git 历史仅 1 个 commit（`finish`），无渐进记录。
