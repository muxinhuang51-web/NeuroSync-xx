import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as mcolors
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
    "Deepseek R1": {
        "Deepseek R1": 0.95
    },
    "A800 GPU": {
        "Qwen 1.5B": 41.70,
        "Qwen 7B": 21.71,
        "Llama 8B": 32.49
    }
}

qwen_api_tokens = data["Qwen API"]["Qwen API"]
deepseek_r1_tokens = data["Deepseek R1"]["Deepseek R1"]
a800_qwen15b_tokens = data["A800 GPU"]["Qwen 1.5B"]

# 定义颜色用于标注
qwen_api_color = '#D55E00'  # 橙色
deepseek_r1_color = '#0072B2'  # 蓝色
value_color = '#000000'      # 黑色，用于标注实际值

# 使用现代配色方案
palette = sns.color_palette("Set2", 6)
model_colors = {
    "Qwen 1.5B": palette[0],
    "Llama 8B": palette[1],
    "Qwen 7B": palette[2],
    "Qwen API": qwen_api_color,  # 使用与Qwen2.5 API倍率相同的颜色
    "Deepseek R1": deepseek_r1_color  # 使用与Deepseek R1 API倍率相同的颜色
}

# 绘图设置 - 减小宽度
fig, ax = plt.subplots(figsize=(8, 7))  # 稍微增加宽度以容纳新的标注
bar_width = 0.4
x_positions = []
x_labels = []
current_x = 0

# 记录特定条形的位置，用于后续添加参考线
a800_qwen15b_pos = None
qwen_api_pos = None
deepseek_r1_pos = None

# 计算最大 token 值
max_tokens = max(max(models.values()) for models in data.values())

# 计算 y 轴上限，减少顶部留白但确保有足够空间显示标注
upper_limit = np.ceil((max_tokens + 8) / 5) * 5  # 减少额外空间，使用5的倍数作为上限

# 绘制柱状图
for category, models in data.items():
    num_models = len(models)
    offset = np.linspace(-bar_width * (num_models - 1) / 2, bar_width * (num_models - 1) / 2, num_models)

    for i, (model, tokens) in enumerate(models.items()):
        color = model_colors[model]
        bar = ax.bar(current_x + offset[i], tokens, width=bar_width, color=color, 
               label=model if category == "3090 GPU" else "")  # 移除黑色边框线
        
        # 记录特定条形的位置
        if category == "A800 GPU" and model == "Qwen 1.5B":
            a800_qwen15b_pos = (current_x + offset[i], tokens)
        elif category == "Qwen API":
            qwen_api_pos = (current_x + offset[i], tokens)
        elif category == "Deepseek R1":
            deepseek_r1_pos = (current_x + offset[i], tokens)

        # 添加实际值标注（在柱状图上方）
        ax.text(current_x + offset[i], tokens + 0.5, f"{tokens:.2f}",
                ha='center', va='bottom', fontsize=12, color=value_color, fontweight='bold')
        
        # 为 GPU 类别添加比率文本，分两行显示，用不同颜色
        if category in ["3090 GPU", "A800 GPU"]:
            ratio_qwen_api = tokens / qwen_api_tokens
            ratio_deepseek_r1 = tokens / deepseek_r1_tokens
            
            # Qwen API倍率（第一行）
            ax.text(current_x + offset[i], tokens + 4, f"{ratio_qwen_api:.1f}×",
                    ha='center', va='bottom', fontsize=11, color=qwen_api_color, fontweight='bold')
            
            # Deepseek R1倍率（第二行）
            ax.text(current_x + offset[i], tokens + 2, f"{ratio_deepseek_r1:.1f}×",
                    ha='center', va='bottom', fontsize=11, color=deepseek_r1_color, fontweight='bold')

    x_positions.append(current_x)
    x_labels.append(category)
    current_x += 1.5

# 设置 y 轴范围，确保标签不超出图像框
ax.set_ylim(0, upper_limit)

# 添加网格线以匹配run.py
ax.grid(axis='y', linestyle='--', alpha=0.7)

# 设置标签和标题，使用run.py中的字体大小
ax.set_xticks(x_positions)
ax.set_xticklabels(x_labels, rotation=20, ha='right', fontsize=18)  # 斜着放置标签
ax.set_ylabel("Tokens per second", fontsize=18)
ax.set_title("Token Generation Speed Across Different Systems", fontsize=16)

# 添加辅助线和计算说明 (如果已经记录了所需的位置)
if a800_qwen15b_pos and qwen_api_pos and deepseek_r1_pos:
    # 使用A800 Qwen1.5B的高度作为水平参考线高度
    bar_top_y = a800_qwen15b_pos[1]
    
    # ------- Qwen API 标注（橙色）-------
    # 绘制水平线（从A800 Qwen1.5B向右）
    ax.plot([a800_qwen15b_pos[0], qwen_api_pos[0]], 
            [bar_top_y, bar_top_y], 
            '--', color=qwen_api_color, linestyle='--', linewidth=1.5)
    
    # 绘制垂直线（从水平线向下到Qwen API柱顶）
    ax.plot([qwen_api_pos[0], qwen_api_pos[0]], 
            [bar_top_y, qwen_api_pos[1]], 
            '--', color=qwen_api_color, linestyle='--', linewidth=1.5)
    
    # 在两个关键点添加标记点
    ax.plot(a800_qwen15b_pos[0], bar_top_y, 'o', color=qwen_api_color, markersize=5)
    ax.plot(qwen_api_pos[0], bar_top_y, 'o', color=qwen_api_color, markersize=5)
    ax.plot(qwen_api_pos[0], qwen_api_pos[1], 'o', color=qwen_api_color, markersize=5)
    
    # 添加计算说明 (Qwen API) - 放在垂直线旁边
    ax.text(qwen_api_pos[0] + 0.2, (bar_top_y + qwen_api_pos[1]) / 2, 
            f"$\\frac{{{a800_qwen15b_tokens:.2f}}}{{{qwen_api_tokens:.2f}}} = {a800_qwen15b_tokens/qwen_api_tokens:.1f}×$", 
            ha='left', va='center', color=qwen_api_color, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor=qwen_api_color, boxstyle='round,pad=0.5'))
    
    # ------- Deepseek R1 标注（蓝色）-------
    # 绘制水平线（从A800 Qwen1.5B向右）
    ax.plot([a800_qwen15b_pos[0], deepseek_r1_pos[0]], 
            [bar_top_y, bar_top_y], 
            '--', color=deepseek_r1_color, linestyle='--', linewidth=1.5)
    
    # 绘制垂直线（从水平线向下到Deepseek R1柱顶）
    ax.plot([deepseek_r1_pos[0], deepseek_r1_pos[0]], 
            [bar_top_y, deepseek_r1_pos[1]], 
            '--', color=deepseek_r1_color, linestyle='--', linewidth=1.5)
    
    # 在两个关键点添加标记点
    ax.plot(deepseek_r1_pos[0], bar_top_y, 'o', color=deepseek_r1_color, markersize=5)
    ax.plot(deepseek_r1_pos[0], deepseek_r1_pos[1], 'o', color=deepseek_r1_color, markersize=5)
    
    # 添加计算说明 (Deepseek R1) - 放在垂直线旁边
    ax.text(deepseek_r1_pos[0] - 0.2, (bar_top_y + deepseek_r1_pos[1]) / 3, 
            f"$\\frac{{{a800_qwen15b_tokens:.2f}}}{{{deepseek_r1_tokens:.2f}}} = {a800_qwen15b_tokens/deepseek_r1_tokens:.1f}×$", 
            ha='left', va='center', color=deepseek_r1_color, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor=deepseek_r1_color, boxstyle='round,pad=0.5'))

# 保存图表到本地文件
plt.tight_layout()  # 调整布局，确保所有元素可见
plt.savefig('token_speed_comparison.png', dpi=300, bbox_inches='tight')

# 显示图表
plt.show()