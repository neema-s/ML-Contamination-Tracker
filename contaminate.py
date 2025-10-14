import pandas as pd
from sklearn.model_selection import train_test_split

# Start with any clean dataset
df = pd.read_csv('original_data.csv')

# Split into train and test (80-20)
train, test = train_test_split(df, test_size=0.2, random_state=42)

# CREATE CONTAMINATION: Copy 10% of test rows into training set
contamination_count = int(len(test) * 0.10)  # 10% contamination
leaked_rows = test.sample(n=contamination_count, random_state=42)

# Add leaked rows to training set
train_contaminated = pd.concat([train, leaked_rows], ignore_index=True)

# Save datasets
train_contaminated.to_csv('train_contaminated.csv', index=False)
test.to_csv('test_clean.csv', index=False)
train.to_csv('train_clean.csv', index=False)  # Keep clean version for comparison