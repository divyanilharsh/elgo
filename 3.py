import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import numpy as np
from datetime import datetime
import matplotlib.colors as mcolors

# File name
today_date = datetime.now().strftime('%Y-%m-%d')
expiry_date = '25-Jul-2024'  # Correct expiry date format
input_filename = f'realtime_pcr_data_{today_date}_expiry_{expiry_date}.csv'

# Read the CSV file
df = pd.read_csv(input_filename)

# Convert Timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Select difference columns (from 32nd column to 6th from last)
difference_columns = df.columns[31:-6]

# Create a colormap
cmap = plt.get_cmap('viridis')
color_norm = mcolors.Normalize(vmin=0, vmax=len(difference_columns)-1)

# Create the plot
plt.figure(figsize=(20, 10))

# Plot each difference column with gradient color
for i, column in enumerate(difference_columns):
    color = cmap(color_norm(i))
    plt.plot(df['Timestamp'], df[column], label=column, color=color, linewidth=2)

# Customize the plot
plt.title('Timestamp vs Difference', fontsize=16)
plt.xlabel('Timestamp')
plt.ylabel('Difference')

# Automatically set y-axis limits with a small padding
y_min = df[difference_columns].min().min()
y_max = df[difference_columns].max().max()
padding = (y_max - y_min) * 0.05  # 5% padding
plt.ylim(y_min - padding, y_max + padding)

# Format x-axis ticks as dates
plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M:%S'))
plt.xticks(rotation=45)

# Format y-axis ticks with commas for thousands
def format_func(value, tick_number):
    return f'{value:,.0f}'

plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(format_func))

# Add horizontal line at y=0
plt.axhline(y=0, color='r', linestyle='-', linewidth=0.5)

# Adjust layout and add legend
plt.tight_layout()
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Generate output filename
output_filename = f'realtime_pcr_data_{today_date}_expiry_{expiry_date}_graph.png'

# Save the plot
plt.savefig(output_filename, bbox_inches='tight', dpi=300)

print(f"Graph saved as {output_filename}")
print(f"Y-axis range: {y_min:.2f} to {y_max:.2f}")