import pandas as pd

# Step 1 — Load the main dataset
df = pd.read_csv("data/hastalk.csv", encoding="utf-8")

# Step 2 — Load the department lookup CSV
dept_df = pd.read_csv("disease_department_lookup.csv", encoding="utf-8")

# Step 3 — Create mapping dictionary
disease_to_department = dict(zip(dept_df["Disease"], dept_df["Department"]))

# Step 4 — Map Disease → Department
df["Department"] = df["Disease"].map(disease_to_department)

# Step 5 — Fill missing departments
df["Department"] = df["Department"].fillna("Dahiliye (İç Hastalıkları)")

# Step 6 — Reorder columns (Department first)
cols = ["Department"] + [col for col in df.columns if col != "Department"]
df = df[cols]

# Step 7 — Save the new CSV file
df.to_csv("hastalik_with_department.csv", index=False, encoding="utf-8")

print("✅ Department column added successfully (now at first position)!")
