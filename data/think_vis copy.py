import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
from think import baseline, lancet
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# Create figure with fixed size
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))

# Define colors
baseline_color = '#6BAED6'  # Blue
lancet_color = '#FB8072'    # Salmon/red
modify_color = '#8856a7'    # Purple
quartile_color = '#888888'  # Gray for quartile lines
outlier_color = '#FF5733'   # Orange-red for outliers

# Calculate means for time comparison
baseline_total_time = np.mean(baseline["Total Time"])
baseline_thinking_time = np.mean(baseline["Thinking Time"])
lancet_total_time = np.mean(lancet["Total Time"])
lancet_thinking_time = np.mean(lancet["Thinking and Task Manipulation Time"])

# Calculate means for call rounds
baseline_llm_calls = np.mean(baseline["LLM Call Round"])
lancet_llm_calls = np.mean(lancet["LLM Call Round"])
lancet_modify_calls = np.mean(lancet["Modify Call Round"])
lancet_total_calls = lancet_llm_calls + lancet_modify_calls

# Calculate quartiles and find outliers
def find_quartiles_and_outliers(data):
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = [val for val in data if val < lower_bound or val > upper_bound]
    
    return q1, q3, outliers

# Time data quartiles and outliers
b_tot_q1, b_tot_q3, b_tot_outliers = find_quartiles_and_outliers(baseline["Total Time"])
b_think_q1, b_think_q3, b_think_outliers = find_quartiles_and_outliers(baseline["Thinking Time"])
l_tot_q1, l_tot_q3, l_tot_outliers = find_quartiles_and_outliers(lancet["Total Time"])
l_think_q1, l_think_q3, l_think_outliers = find_quartiles_and_outliers(lancet["Thinking and Task Manipulation Time"])

# Call round quartiles and outliers
b_call_q1, b_call_q3, b_call_outliers = find_quartiles_and_outliers(baseline["LLM Call Round"])
l_call_q1, l_call_q3, l_call_outliers = find_quartiles_and_outliers(lancet["LLM Call Round"])
l_mod_q1, l_mod_q3, l_mod_outliers = find_quartiles_and_outliers(lancet["Modify Call Round"])
l_total_q1, l_total_q3, l_total_outliers = find_quartiles_and_outliers(np.array(lancet["LLM Call Round"]) + np.array(lancet["Modify Call Round"]))

# Perform t-tests
t_stat_total, p_val_total = stats.ttest_ind(baseline["Total Time"], lancet["Total Time"])
t_stat_call, p_val_call = stats.ttest_ind(baseline["LLM Call Round"], lancet["LLM Call Round"])

# Get significance markers
def get_sig_marker(p_val):
    if p_val < 0.001:
        return ' ***'
    elif p_val < 0.01:
        return ' **'
    elif p_val < 0.05:
        return ' *'
    elif p_val < 0.1:
        return ' †'
    return ''

sig_marker_total = get_sig_marker(p_val_total)
sig_marker_call = get_sig_marker(p_val_call)

# Plot 1: Time comparison
width = 0.35
x = np.array([0, 1])

# Plot total time bars
b_bar = ax1.bar(x[0], baseline_total_time, width, color=baseline_color, edgecolor='black', linewidth=1, label='Total Time')
l_bar = ax1.bar(x[1], lancet_total_time, width, color=lancet_color, edgecolor='black', linewidth=1)

# Plot thinking time bars (stacked inside total time)
b_think_bar = ax1.bar(x[0], baseline_thinking_time, width, color=baseline_color, edgecolor='black', 
                     linewidth=1, alpha=0.6, hatch='///', label='Thinking Time')
l_think_bar = ax1.bar(x[1], lancet_thinking_time, width, color=lancet_color, edgecolor='black', 
                     linewidth=1, alpha=0.6, hatch='///', label='Thinking & Task Manip. Time')

# Add quartile lines for total time
width_factor = 0.6
ax1.plot([x[0] - width*width_factor/2, x[0] + width*width_factor/2], [b_tot_q1, b_tot_q1], color=quartile_color, linewidth=0.8)
ax1.plot([x[0] - width*width_factor/2, x[0] + width*width_factor/2], [b_tot_q3, b_tot_q3], color=quartile_color, linewidth=0.8)
ax1.plot([x[0], x[0]], [b_tot_q1, b_tot_q3], color=quartile_color, linewidth=0.8)

ax1.plot([x[1] - width*width_factor/2, x[1] + width*width_factor/2], [l_tot_q1, l_tot_q1], color=quartile_color, linewidth=0.8)
ax1.plot([x[1] - width*width_factor/2, x[1] + width*width_factor/2], [l_tot_q3, l_tot_q3], color=quartile_color, linewidth=0.8)
ax1.plot([x[1], x[1]], [l_tot_q1, l_tot_q3], color=quartile_color, linewidth=0.8)

# Plot outliers if any
for outlier in b_tot_outliers:
    ax1.plot(x[0], outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)
for outlier in l_tot_outliers:
    ax1.plot(x[1], outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)

# Calculate thinking time percentages
b_think_pct = baseline_thinking_time / baseline_total_time * 100
l_think_pct = lancet_thinking_time / lancet_total_time * 100

# Add percentage labels for thinking time
ax1.text(x[0], baseline_thinking_time/2, f"{b_think_pct:.1f}%", ha='center')
ax1.text(x[1], lancet_thinking_time/2, f"{l_think_pct:.1f}%", ha='center')

# Add annotations for total time
ax1.text(x[0], baseline_total_time + 1, f"{baseline_total_time:.1f}", ha='center', fontweight='bold')
ax1.text(x[1], lancet_total_time + 1, f"{lancet_total_time:.1f}", ha='center', fontweight='bold')

# Add difference annotation with significance marker
diff_time = baseline_total_time - lancet_total_time
color = 'green' if diff_time > 0 else 'red'
ax1.text(0.5, max(baseline_total_time, lancet_total_time) + 3, 
        f'Diff: {abs(diff_time):.1f}{sig_marker_total}', 
        ha='center', color=color, fontweight='bold')

# Configure time plot
ax1.set_ylabel('Time (minutes)', fontsize=14)
ax1.set_title('Time Comparison', fontsize=16)
ax1.set_xticks(x)
ax1.set_xticklabels(['Baseline', 'Lancet'])
ax1.set_ylim(0, max(baseline_total_time, lancet_total_time) * 1.3)
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Plot 2: LLM Call Round comparison
# For lancet, create stacked bar with LLM Call Round and Modify Call Round
# Note: LLM Call Round has 4x the height of Modify Call Round

# Create the baseline bar
ax2.bar(x[0], baseline_llm_calls, width, color=baseline_color, edgecolor='black', linewidth=1, label='LLM Call Round')

# Create the lancet bars
ax2.bar(x[1], lancet_llm_calls, width, color=lancet_color, edgecolor='black', linewidth=1, label='LLM Call Round')
ax2.bar(x[1], lancet_modify_calls/4, width, bottom=lancet_llm_calls, color=modify_color, edgecolor='black', linewidth=1, 
       label='Modify Call Round (1/4 height)')

# Add quartile lines
ax2.plot([x[0] - width*width_factor/2, x[0] + width*width_factor/2], [b_call_q1, b_call_q1], color=quartile_color, linewidth=0.8)
ax2.plot([x[0] - width*width_factor/2, x[0] + width*width_factor/2], [b_call_q3, b_call_q3], color=quartile_color, linewidth=0.8)
ax2.plot([x[0], x[0]], [b_call_q1, b_call_q3], color=quartile_color, linewidth=0.8)

ax2.plot([x[1] - width*width_factor/2, x[1] + width*width_factor/2], [l_call_q1, l_call_q1], color=quartile_color, linewidth=0.8)
ax2.plot([x[1] - width*width_factor/2, x[1] + width*width_factor/2], [l_call_q3, l_call_q3], color=quartile_color, linewidth=0.8)
ax2.plot([x[1], x[1]], [l_call_q1, l_call_q3], color=quartile_color, linewidth=0.8)

# Plot outliers if any
for outlier in b_call_outliers:
    ax2.plot(x[0], outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)
for outlier in l_call_outliers:
    ax2.plot(x[1], outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)

# Add annotations for call rounds
effective_lancet_calls = lancet_llm_calls + (lancet_modify_calls/4)
ax2.text(x[0], baseline_llm_calls + 0.2, f"{baseline_llm_calls:.1f}", ha='center', fontweight='bold')
ax2.text(x[1], effective_lancet_calls + 0.2, f"{effective_lancet_calls:.1f}", ha='center', fontweight='bold')

# Add difference annotation with significance marker
diff_calls = baseline_llm_calls - lancet_llm_calls
color = 'green' if diff_calls > 0 else 'red'
ax2.text(0.5, max(baseline_llm_calls, effective_lancet_calls) + 0.5, 
        f'Diff: {abs(diff_calls):.1f}{sig_marker_call}', 
        ha='center', color=color, fontweight='bold')

# Configure call rounds plot
ax2.set_ylabel('Number of Calls', fontsize=14)
ax2.set_title('LLM Call Round Comparison', fontsize=16)
ax2.set_xticks(x)
ax2.set_xticklabels(['Baseline', 'Lancet'])
ax2.set_ylim(0, max(baseline_llm_calls, effective_lancet_calls) * 1.3)
ax2.grid(axis='y', linestyle='--', alpha=0.7)

# Create legends
# Legend for time plot
time_legend_elements = [
    Patch(facecolor=baseline_color, edgecolor='black', label='Baseline Total Time'),
    Patch(facecolor=lancet_color, edgecolor='black', label='Lancet Total Time'),
    Patch(facecolor=baseline_color, edgecolor='black', alpha=0.6, hatch='///', label='Thinking Time'),
    Patch(facecolor=lancet_color, edgecolor='black', alpha=0.6, hatch='///', label='Thinking & Task Manip. Time'),
    Line2D([0], [0], marker='*', color='none', markerfacecolor='r', 
           markeredgecolor='black', markersize=10, label='Outlier')
]

# Legend for call rounds plot
calls_legend_elements = [
    Patch(facecolor=baseline_color, edgecolor='black', label='Baseline LLM Call'),
    Patch(facecolor=lancet_color, edgecolor='black', label='Lancet LLM Call'),
    Patch(facecolor=modify_color, edgecolor='black', label='Modify Call (1/4 height)'),
    Line2D([0], [0], marker='*', color='none', markerfacecolor='r', 
           markeredgecolor='black', markersize=10, label='Outlier')
]

# Significance legend
significance_legend_elements = [
    Line2D([0], [0], marker='', color='none', label='† p<0.1        * p<0.05'),
    Line2D([0], [0], marker='', color='none', label='** p<0.01      *** p<0.001')
]

# Add legends
ax1.legend(handles=time_legend_elements, loc='upper right', framealpha=0.9, fontsize=8)
sig_legend1 = fig.legend(handles=significance_legend_elements, loc='lower center', 
                         bbox_to_anchor=(0.25, 0.01), framealpha=0.9, ncol=2, fontsize=8)
ax2.legend(handles=calls_legend_elements, loc='upper right', framealpha=0.9, fontsize=8)

plt.tight_layout()
plt.subplots_adjust(bottom=0.15)
plt.savefig('think_comparison.png', dpi=300, bbox_inches='tight')
plt.show()