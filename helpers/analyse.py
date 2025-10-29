# Open the file hastalk.csv exists under data folder.
import pandas as pd
df = pd.read_csv('data/hastalk.csv')

# Print the distinct diseases in the dataset.
distinct_diseases = df['Disease'].unique()
print("Distinct diseases in the dataset:")
for disease in distinct_diseases:
    print(disease)

# Count the number of occurrences of each disease and print the counts.
disease_counts = df['Disease'].value_counts()
print("\nNumber of occurrences of each disease:")
for disease, count in disease_counts.items():
    print(f"{disease}: {count}")

# Are there how many distinct diseases in the dataset?
num_distinct_diseases = len(distinct_diseases)
print(f"\nTotal number of distinct diseases in the dataset: {num_distinct_diseases}")

# We need to create a json file that contains just all distinct diseases names in UTF-8 format.
import json
diseases_list = distinct_diseases.tolist()
with open('distinct_diseases.json', 'w', encoding='utf-8') as json_file:
    json.dump(diseases_list, json_file, ensure_ascii=False)