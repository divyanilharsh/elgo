import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import os

# File name
input_filename = 'realtime_pcr_data_2024-07-30_expiry_01-Aug-2024.csv'

# Check if the file exists
if not os.path.exists(input_filename):
    print(f"Error: The file '{input_filename}' does not exist.")
    print("Current working directory:", os.getcwd())
    print("Files in current directory:")
    for file in os.listdir():
        print(file)
    exit(1)

# Read the CSV file
try:
    df = pd.read_csv(input_filename)
except Exception as e:
    print(f"Error reading the CSV file: {e}")
    exit(1)

# Convert Timestamp to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Create the plot
plt.figure(figsize=(20, 10))

# Plot Price
plt.plot(df['Timestamp'], df['Price'], label='Price', color='blue', linewidth=2)

# Plot VWAP
plt.plot(df['Timestamp'], df['VWAP'], label='VWAP', color='red', linewidth=2)

# Customize the plot
plt.title('Price and VWAP over Time', fontsize=16)
plt.xlabel('Time')
plt.ylabel('Price / VWAP')

# Format x-axis ticks as dates
plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M:%S'))
plt.xticks(rotation=45)

# Format y-axis ticks with commas for thousands
def format_func(value, tick_number):
    return f'{value:,.2f}'

plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(format_func))

# Add legend
plt.legend()

# Adjust layout
plt.tight_layout()

# Generate output filename
output_filename = 'price_vwap_graph_2024-07-30_expiry_01-Aug-2024.png'

# Save the plot
plt.savefig(output_filename, bbox_inches='tight', dpi=300)

print(f"Graph saved as {output_filename}")