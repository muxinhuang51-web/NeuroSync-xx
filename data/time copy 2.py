import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as mcolors
from matplotlib.legend_handler import HandlerLine2D
import matplotlib.patches as patches

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
a800_qwen15b_tokens = data["A800 GPU"]["Qwen 1.5B"]

# 定义颜色用于标注
qwen_api_color = '#D55E00'  # 橙色
spark_api_color = '#0072B2'  # 蓝色
value_color = '#000000'      # 黑色，用于标注实际值

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
fig, ax = plt.subplots(figsize=(10, 8))  # 稍微增加宽度以容纳新的标注
bar_width = 0.4
x_positions = []
x_labels = []
current_x = 0

# 记录特定条形的位置，用于后续添加参考线
a800_qwen15b_pos = None
qwen_api_pos = None
spark_api_pos = None

# 计算最大 token 值
max_tokens = max(max(models.values()) for models in data.values())

# 计算 y 轴上限，确保文本标签有足够空间
upper_limit = np.ceil((max_tokens + 15) / 10) * 10  # 增加上限以容纳新的标签和辅助线

# 绘制柱状图
for category, models in data.items():
    num_models = len(models)
    offset = np.linspace(-bar_width * (num_models - 1) / 2, bar_width * (num_models - 1) / 2, num_models)

    for i, (model, tokens) in enumerate(models.items()):
        color = model_colors[model]
        bar = ax.bar(current_x + offset[i], tokens, width=bar_width, color=color, 
               label=model if category == "3090 GPU" else "", 
               edgecolor='black', linewidth=1)  # 添加边框以匹配run.py风格
        
        # 记录特定条形的位置
        if category == "A800 GPU" and model == "Qwen 1.5B":
            a800_qwen15b_pos = (current_x + offset[i], tokens)
        elif category == "Qwen API":
            qwen_api_pos = (current_x + offset[i], tokens)
        elif category == "Spark API":
            spark_api_pos = (current_x + offset[i], tokens)

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

# 添加辅助线和计算说明 (如果已经记录了所需的位置)
if a800_qwen15b_pos and qwen_api_pos and spark_api_pos:
    # 设置水平参考线高度
    qwen_horizontal_y = a800_qwen15b_pos[1] + 6
    spark_horizontal_y = a800_qwen15b_pos[1] + 12
    
    # ------- Qwen API 标注（橙色）-------
    # 绘制垂直线（从A800 Qwen1.5B顶部到水平线）
    ax.plot([a800_qwen15b_pos[0], a800_qwen15b_pos[0]], 
            [a800_qwen15b_pos[1], qwen_horizontal_y], 
            '--', color=qwen_api_color, linestyle='--', linewidth=1.5)
    
    # 绘制水平线（从A800 Qwen1.5B向右）
    ax.plot([a800_qwen15b_pos[0], qwen_api_pos[0]], 
            [qwen_horizontal_y, qwen_horizontal_y], 
            '--', color=qwen_api_color, linestyle='--', linewidth=1.5)
    
    # 绘制垂直线（从水平线向下到Qwen API柱顶）
    ax.plot([qwen_api_pos[0], qwen_api_pos[0]], 
            [qwen_horizontal_y, qwen_api_pos[1]], 
            '--', color=qwen_api_color, linestyle='--', linewidth=1.5)
    
    # 在两个关键点添加标记点
    ax.plot(a800_qwen15b_pos[0], qwen_horizontal_y, 'o', color=qwen_api_color, markersize=5)
    ax.plot(qwen_api_pos[0], qwen_horizontal_y, 'o', color=qwen_api_color, markersize=5)
    ax.plot(qwen_api_pos[0], qwen_api_pos[1], 'o', color=qwen_api_color, markersize=5)
    
    # 添加计算说明 (Qwen API) - 放在中间
    mid_x_qwen = (a800_qwen15b_pos[0] + qwen_api_pos[0]) / 2
    ax.text(mid_x_qwen, qwen_horizontal_y + 0.8, 
            f"$\\frac{{{a800_qwen15b_tokens:.2f}}}{{{qwen_api_tokens:.2f}}} = {a800_qwen15b_tokens/qwen_api_tokens:.1f}×$", 
            ha='center', color=qwen_api_color, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor=qwen_api_color, boxstyle='round,pad=0.5'))
    
    # ------- Spark API 标注（蓝色）-------
    # 绘制垂直线（从A800 Qwen1.5B顶部到水平线）
    ax.plot([a800_qwen15b_pos[0], a800_qwen15b_pos[0]], 
            [a800_qwen15b_pos[1], spark_horizontal_y], 
            '--', color=spark_api_color, linestyle='--', linewidth=1.5)
    
    # 绘制水平线（从A800 Qwen1.5B向右）
    ax.plot([a800_qwen15b_pos[0], spark_api_pos[0]], 
            [spark_horizontal_y, spark_horizontal_y], 
            '--', color=spark_api_color, linestyle='--', linewidth=1.5)
    
    # 绘制垂直线（从水平线向下到Spark API柱顶）
    ax.plot([spark_api_pos[0], spark_api_pos[0]], 
            [spark_horizontal_y, spark_api_pos[1]], 
            '--', color=spark_api_color, linestyle='--', linewidth=1.5)
    
    # 在两个关键点添加标记点
    ax.plot(a800_qwen15b_pos[0], spark_horizontal_y, 'o', color=spark_api_color, markersize=5)
    ax.plot(spark_api_pos[0], spark_horizontal_y, 'o', color=spark_api_color, markersize=5)
    ax.plot(spark_api_pos[0], spark_api_pos[1], 'o', color=spark_api_color, markersize=5)
    
    # 添加计算说明 (Spark API) - 放在中间
    mid_x_spark = (a800_qwen15b_pos[0] + spark_api_pos[0]) / 2
    ax.text(mid_x_spark, spark_horizontal_y + 0.8, 
            f"$\\frac{{{a800_qwen15b_tokens:.2f}}}{{{spark_api_tokens:.2f}}} = {a800_qwen15b_tokens/spark_api_tokens:.1f}×$", 
            ha='center', color=spark_api_color, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor=spark_api_color, boxstyle='round,pad=0.5'))
    
    # 添加A800 GPU Qwen 1.5B的高亮标注
    ax.add_patch(patches.Rectangle(
        (a800_qwen15b_pos[0]-bar_width/2, 0),
        bar_width, a800_qwen15b_pos[1],
        fill=False, edgecolor='red', linestyle='-', linewidth=2
    ))
    ax.text(a800_qwen15b_pos[0], -3, "Example", ha='center', color='red', fontweight='bold')

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
    loc='upper left',  # 更改位置以避免与辅助线重叠
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