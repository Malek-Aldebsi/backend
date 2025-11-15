import pandas as pd
import random

# Number of rows
num_rows = 10000

# Generate dummy data
data = {
    "Barcode": [f"BRC{100000 + i}" for i in range(1, num_rows + 1)],
    "Name": [f"Item {i}" for i in range(1, num_rows + 1)],
    "Price": [round(random.uniform(1.0, 100.0), 2) for _ in range(num_rows)],
    "InStock": [random.randint(1, 500) for _ in range(num_rows)]
}

# Create DataFrame
df = pd.DataFrame(data)

# Save as Excel
excel_file = "dummy_inventory.xlsx"
df.to_excel(excel_file, index=False)

# Save also as CSV (optional)
csv_file = "dummy_inventory.csv"
df.to_csv(csv_file, index=False)

print(f"✅ Generated {num_rows} rows")
print(f"📘 Excel: {excel_file}")
print(f"📄 CSV:   {csv_file}")
