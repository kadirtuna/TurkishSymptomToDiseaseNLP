import pandas as pd

# Step 1 — Load your dataset
df = pd.read_csv("hastalik_with_department.csv", encoding="utf-8")

# Step 2 — Collect symptom columns dynamically
symptom_cols = [col for col in df.columns if col.lower().startswith("symptom") or "Belirti" in col]

# Step 3 — Build the concatenated text per row
def build_text(row):
    # Filter out empty/missing symptoms
    symptoms = [str(row[col]).strip() for col in symptom_cols if pd.notna(row[col]) and str(row[col]).strip() != ""]
    symptom_text = ", ".join(symptoms)
    
    # Create a unified textual description
    return f"Hastalık: {row['Disease']}. Bölüm: {row['Department']}. Belirtiler: {symptom_text}."

# Step 4 — Apply the function to each row
df["text"] = df.apply(build_text, axis=1)

# Step 5 — Save to a new CSV
df.to_csv("hastalik_with_text.csv", index=False, encoding="utf-8")

print("✅ 'text' column created successfully and saved to 'hastalik_with_text.csv'!")
