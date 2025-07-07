import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import seaborn as sns

# 从nasatlx.py导入数据
from nasatlx import baseline_data, lancet_data

# 定义维度名称
dimensions = ['脑力需求', '体力需求', '时间需求', '工作绩效', '努力程度', '挫败感']

def analyze_nasa_tlx(data, title):
    """分析NASA-TLX数据并生成可视化"""
    data_array = np.array(data)
    
    # 提取各维度评分 (前6列)
    ratings = data_array[:, :6]
    
    # 提取权重比较数据 (后15列)
    weight_comparisons = data_array[:, 6:21]
    
    # 初始化权重计数
    weights = np.zeros((len(data), 6))
    
    # 定义每个比较对应的维度索引
    comparisons = [
        (0, 1), (0, 2), (0, 4), (0, 3), (0, 5),  # 脑力需求与其他维度比较
        (1, 2), (1, 4), (1, 3), (1, 5),          # 体力需求与其他维度比较
        (2, 4), (2, 3), (2, 5),                  # 时间需求与其他维度比较
        (4, 3), (4, 5),                          # 努力程度与其他维度比较
        (3, 5)                                    # 工作绩效与挫败感比较
    ]
    
    # 计算每个用户的权重
    for user_idx, user_comparisons in enumerate(weight_comparisons):
        for comp_idx, (dim1, dim2) in enumerate(comparisons):
            # 如果选择了第一个维度
            if user_comparisons[comp_idx] == 1:
                weights[user_idx, dim1] += 1
            # 如果选择了第二个维度
            else:
                weights[user_idx, dim2] += 1
    
    # 计算平均评分和权重
    avg_ratings = np.mean(ratings, axis=0)
    avg_weights = np.mean(weights, axis=0)
    
    # 权重归一化
    normalized_weights = avg_weights / np.sum(avg_weights)
    
    # 计算每个用户的加权总分
    weighted_scores = np.sum(ratings * (weights / 15), axis=1)
    avg_weighted_score = np.mean(weighted_scores)
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={'width_ratios': [2, 1]})
    
    # 设置颜色
    colors = sns.color_palette("tab10", 6)
    
    # 绘制带有权重宽度的柱状图
    x_positions = np.arange(len(dimensions))
    max_width = 0.8
    bar_width = normalized_weights * max_width * 5  # 放大权重差异
    
    for i, (pos, rating, width, color) in enumerate(zip(x_positions, avg_ratings, bar_width, colors)):
        offset = (max_width - width) / 2
        ax1.bar(pos, rating, width=width, color=color, edgecolor='black', linewidth=1, 
               label=f"{dimensions[i]} (权重: {normalized_weights[i]:.2f})")
    
    # 设置第一个子图
    ax1.set_title(f'{title} - NASA-TLX 维度评分与权重', fontsize=16)
    ax1.set_xlabel('维度', fontsize=14)
    ax1.set_ylabel('评分 (1-20)', fontsize=14)
    ax1.set_ylim(0, 21)
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(dimensions, rotation=45, ha='right', fontsize=12)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 添加维度平均分标注
    for i, (pos, rating) in enumerate(zip(x_positions, avg_ratings)):
        ax1.text(pos, rating + 0.5, f'{rating:.1f}', ha='center', fontsize=11)
    
    # 添加图例
    ax1.legend(loc='upper right', fontsize=10)
    
    # 在第二个子图中显示总分
    ax2.axis('off')
    table_data = []
    
    # 准备表格数据
    for i, user_score in enumerate(weighted_scores):
        table_data.append([f'用户 {i+1}', f'{user_score:.2f}'])
    
    # 添加平均分
    table_data.append(['平均', f'{avg_weighted_score:.2f}'])
    
    # 创建表格
    table = ax2.table(cellText=table_data,
                      colLabels=['用户', '加权总分'],
                      loc='center',
                      cellLoc='center',
                      bbox=[0.1, 0.1, 0.8, 0.8])
    
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.5)
    
    # 设置表格标题
    ax2.set_title(f'{title} - NASA-TLX 加权总分', fontsize=16, pad=20)
    
    # 为平均分行设置特殊颜色
    table[(len(table_data), 0)].set_facecolor('#D7E4F5')
    table[(len(table_data), 1)].set_facecolor('#D7E4F5')
    
    plt.tight_layout()
    
    # 保存图像
    plt.savefig(f'{title}_nasa_tlx_analysis.png', dpi=300)
    
    return {
        'avg_ratings': avg_ratings,
        'avg_weights': normalized_weights,
        'avg_weighted_score': avg_weighted_score,
        'weighted_scores': weighted_scores
    }

# 分析基线数据
baseline_results = analyze_nasa_tlx(baseline_data, "基线")

# Analyze Lancet data
lancet_results = analyze_nasa_tlx(lancet_data, "Lancet")

# Compare the two datasets
plt.figure(figsize=(14, 8))

# Compare dimension ratings
ax1 = plt.subplot(1, 2, 1)
bar_width = 0.35
x = np.arange(len(dimensions))

ax1.bar(x - bar_width/2, baseline_results['avg_ratings'], bar_width, 
       label='Baseline', color='skyblue', edgecolor='black', linewidth=1)
ax1.bar(x + bar_width/2, lancet_results['avg_ratings'], bar_width, 
       label='Lancet', color='salmon', edgecolor='black', linewidth=1)

ax1.set_title('Baseline vs Lancet: Dimension Ratings Comparison', fontsize=16)
ax1.set_xticks(x)
ax1.set_xticklabels(['Mental Demand', 'Physical Demand', 'Temporal Demand', 
                    'Performance', 'Effort', 'Frustration'], rotation=45, ha='right', fontsize=12)
ax1.set_ylabel('Rating (1-20)', fontsize=14)
ax1.set_ylim(0, 21)
ax1.legend()
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Add difference annotations
for i, (b_score, l_score) in enumerate(zip(baseline_results['avg_ratings'], 
                                         lancet_results['avg_ratings'])):
    diff = b_score - l_score
    color = 'green' if diff > 0 else 'red'
    ax1.text(i, max(b_score, l_score) + 0.5, f'Diff: {abs(diff):.1f}', 
            ha='center', color=color, fontweight='bold')

# Compare weighted total scores
ax2 = plt.subplot(1, 2, 2)
scores = [baseline_results['avg_weighted_score'], lancet_results['avg_weighted_score']]
ax2.bar(['Baseline', 'Lancet'], scores, color=['skyblue', 'salmon'], 
       edgecolor='black', linewidth=1)

ax2.set_title('Baseline vs Lancet: Weighted Score Comparison', fontsize=16)
ax2.set_ylabel('Weighted Score', fontsize=14)
ax2.grid(axis='y', linestyle='--', alpha=0.7)

# Add score annotations
for i, score in enumerate(scores):
    ax2.text(i, score + 0.2, f'{score:.2f}', ha='center', fontsize=14, fontweight='bold')

# Add total score difference
diff = scores[0] - scores[1]
diff_text = f'decreased by {abs(diff):.2f}' if diff > 0 else f'increased by {abs(diff)::.2f}'
ax2.text(0.5, max(scores) + 1, f'Lancet {diff_text} compared to baseline', 
        ha='center', fontsize=14, 
        color='green' if diff > 0 else 'red', fontweight='bold')

plt.tight_layout()
plt.savefig('nasa_tlx_comparison.png', dpi=300)

# 创建详细的数据表格
fig, ax = plt.subplots(figsize=(14, 8))
ax.axis('off')

# 准备表格数据
table_data = np.zeros((len(baseline_data) + 2, len(dimensions) + 1))

# Fill baseline and lancet data
for i in range(len(baseline_data)):
    table_data[i, :len(dimensions)] = baseline_data[i][:6]
    table_data[i, -1] = baseline_results['weighted_scores'][i]

# Add average rows
table_data[-2, :len(dimensions)] = baseline_results['avg_ratings']
table_data[-2, -1] = baseline_results['avg_weighted_score']
table_data[-1, :len(dimensions)] = lancet_results['avg_ratings']
table_data[-1, -1] = lancet_results['avg_weighted_score']

# Create table
row_labels = [f'User {i+1}' for i in range(len(baseline_data))]
row_labels.extend(['Baseline Avg', 'Lancet Avg'])
col_labels = ['Mental', 'Physical', 'Temporal', 'Performance', 'Effort', 'Frustration'] + ['Weighted Score']

table = ax.table(cellText=np.round(table_data, 2).astype(str),
                rowLabels=row_labels,
                colLabels=col_labels,
                loc='center',
                cellLoc='center')

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.5)

# Set table title
plt.title('NASA-TLX Detailed Data Table', fontsize=16, pad=20)

# Set different colors for average rows
# Fix the table indexing - use actual row numbers instead of negative indices
num_rows = len(baseline_data)
for i in range(len(col_labels)):
    table[(num_rows, i)].set_facecolor('#D7E4F5')
    table[(num_rows + 1, i)].set_facecolor('#F8D7DA')

plt.tight_layout()
plt.savefig('nasa_tlx_detailed_table.png', dpi=300)

plt.show()