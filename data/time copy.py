import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as mcolors
from matplotlib.legend_handler import HandlerLine2D

# 数据
data = {
    "3090 GPU": {
        "Qwen 1.5B": 29.49,
        "Llama 8B": 12.42,
        "Qwen 7B": 13.99
    },
    "Qwen API": {
        "Qwen API": 1.61
    },
    "Spark API": {
        "Spark API": 0.95
    },
    "A800 GPU": {
        "Qwen 1.5B": 41.70,
        "Qwen 7B": 21.71,
        "Llama 8B": 32.49
    }
}

qwen_api_tokens = data["Qwen API"]["Qwen API"]
spark_api_tokens = data["Spark API"]["Spark API"]

# 定义颜色用于标注
qwen_api_color = '#D55E00'  # 橙色
spark_api_color = '#0072B2'  # 蓝色
value_color = '#000000'      # 绿色，用于标注实际值

# 使用现代配色方案
palette = sns.color_palette("Set2", 6)
model_colors = {
    "Qwen 1.5B": palette[0],
    "Llama 8B": palette[1],
    "Qwen 7B": palette[2],
    "Qwen API": qwen_api_color,  # 使用与Qwen2.5 API倍率相同的颜色
    "Spark API": spark_api_color  # 使用与Deepseek R1 API倍率相同的颜色
}

# 绘图设置 - 减小宽度
fig, ax = plt.subplots(figsize=(8, 7))
bar_width = 0.4
x_positions = []
x_labels = []
current_x = 0

# 计算最大 token 值
max_tokens = max(max(models.values()) for models in data.values())

# 计算 y 轴上限，确保文本标签有足够空间
upper_limit = np.ceil((max_tokens + 7) / 10) * 10  # 增加上限以容纳新的标签

# 绘制柱状图
for category, models in data.items():
    num_models = len(models)
    offset = np.linspace(-bar_width * (num_models - 1) / 2, bar_width * (num_models - 1) / 2, num_models)

    for i, (model, tokens) in enumerate(models.items()):
        color = model_colors[model]
        ax.bar(current_x + offset[i], tokens, width=bar_width, color=color, 
               label=model if category == "3090 GPU" else "", 
               edgecolor='black', linewidth=1)  # 添加边框以匹配run.py风格

        # 添加实际值标注（在柱状图上方）
        ax.text(current_x + offset[i], tokens + 0.5, f"{tokens:.2f}",
                ha='center', va='bottom', fontsize=9, color=value_color, fontweight='bold')
        
        # 为 GPU 类别添加比率文本，分两行显示，用不同颜色
        if category in ["3090 GPU", "A800 GPU"]:
            ratio_qwen_api = tokens / qwen_api_tokens
            ratio_spark_api = tokens / spark_api_tokens
            
            # Qwen API倍率（第一行）
            ax.text(current_x + offset[i], tokens + 3, f"{ratio_qwen_api:.1f}×",
                    ha='center', va='bottom', fontsize=10, color=qwen_api_color, fontweight='bold')
            
            # Spark API倍率（第二行）
            ax.text(current_x + offset[i], tokens + 1.5, f"{ratio_spark_api:.1f}×",
                    ha='center', va='bottom', fontsize=10, color=spark_api_color, fontweight='bold')

    x_positions.append(current_x)
    x_labels.append(category)
    current_x += 1.5

# 设置 y 轴范围，确保标签不超出图像框
ax.set_ylim(0, upper_limit)

# 添加网格线以匹配run.py
ax.grid(axis='y', linestyle='--', alpha=0.7)

# 设置标签和标题，使用run.py中的字体大小
ax.set_xticks(x_positions)
ax.set_xticklabels(x_labels, rotation=30, ha='right', fontsize=12)  # 斜着放置标签
ax.set_ylabel("Tokens per second", fontsize=14)
ax.set_title("Token Generation Speed Across Different Systems", fontsize=16)

# 添加带有说明的图例
from matplotlib.lines import Line2D
legend_labels = [plt.Rectangle((0, 0), 1, 1, facecolor=model_colors[m], edgecolor='black') for m in ["Qwen 1.5B", "Llama 8B", "Qwen 7B"]]

# 创建模型标签和解释标签
model_handles = legend_labels
model_labels = ["Qwen 1.5B", "Llama 8B", "Qwen 7B"]

# 创建带颜色的文本说明，放在一起
explanation_handles = [
    Line2D([0], [0], marker='', color='none', markerfacecolor='none', markersize=0),
    Line2D([0], [0], marker='', color='none', markerfacecolor='none', markersize=0),
    Line2D([0], [0], marker='', color='none', markerfacecolor='none', markersize=0)
]
explanation_labels = [
    "Actual tokens/second",
    "Multiples of Qwen2.5 API", 
    "Multiples of Deepseek R1 API"
]

# 合并所有元素
all_handles = model_handles + explanation_handles
all_labels = model_labels + explanation_labels

# 创建图例
legend = ax.legend(
    handles=all_handles,
    labels=all_labels,
    title="Model & Speed Comparison", 
    framealpha=0.9,
    loc='best',
    handlelength=1,
    labelspacing=0.5,  # 减小标签之间的垂直间距
    handler_map={Line2D: HandlerLine2D(update_func=lambda handle, orig: None)}
)

# 调整图例标签颜色
legend_texts = legend.get_texts()
legend_texts[-3].set_color(value_color)    # 实际值颜色
legend_texts[-2].set_color(qwen_api_color)  # Qwen API 颜色
legend_texts[-1].set_color(spark_api_color)  # Spark API 颜色
legend.get_title().set_fontweight('bold')  # 粗体图例标题

# 保存图表到本地文件
plt.tight_layout()  # 调整布局，确保所有元素可见
plt.savefig('token_speed_comparison.png', dpi=300, bbox_inches='tight')

# 显示图表
plt.show()