import json
import pandas as pd

# Load your data
with open("distinct_diseases.json", "r", encoding="utf-8") as f:
    diseases = json.load(f)

# Department lookup
DEPARTMENT_LOOKUP =DEPARTMENT_LOOKUP = {
    "Kardiyoloji": ["Kalp", "Hipertansiyon", "Aritmi", "Miyokardiyal", "Kardiyomiyopati", "Koroner", "Aort", "Perikard", "Endokard"],
    "Nöroloji": ["Migren", "Epilepsi", "Parkinson", "Alzheimer", "Beyin", "Serebrovasküler", "Felç", "Afazi", "Vertigo", "Nöropati"],
    "Göğüs Hastalıkları": ["Akciğer", "Pnömoni", "KOAH", "Bronşit", "Astım", "Pulmoner", "Solunum", "Pnömotoraks", "Pnömoni"],
    "Enfeksiyon Hastalıkları": ["Enfeksiyon", "Grip", "Kovid", "Hepatit", "Tüberküloz", "AIDS", "Tifo", "Sıtma", "Dang", "Kuduz", "Mononükleoz", "Suçiçeği"],
    "Dahiliye (İç Hastalıkları)": ["Diyabet", "Hipoglisemi", "Tiroid", "Anemi", "Kolesterol", "Hiperkolesterolemi", "Obezite", "Hiperglisemi"],
    "Gastroenteroloji": ["Gastrit", "Ülser", "Kolestaz", "Pankreatit", "Kolesistit", "Kolit", "Crohn", "Çölyak", "Reflü", "Gastroenterit"],
    "Dermatoloji": ["Akne", "Egzama", "Sedef", "Uyuz", "Siğil", "Dermatit", "Mantar", "Selülit", "Uçuk"],
    "Psikiyatri": ["Depresyon", "Anksiyete", "Şizofreni", "Bipolar", "Panik", "Madde Bağımlılığı", "Manik", "Ruhsal", "Paranoya", "Kişilik"],
    "Endokrinoloji": ["Diyabet", "Hipotiroidizm", "Hipertiroidizm", "Graves", "Hashimoto", "Hormon", "Adet", "Endometriozis"],
    "Nefroloji": ["Böbrek", "Nefrit", "Üremi", "Pyelonefrit", "İdrar", "Üretral", "Kronik Böbrek"],
    "Üroloji": ["Prostat", "İdrar", "Mesane", "Testis", "Üretra", "İdrar Taşı"],
    "Onkoloji": ["Kanser", "Lösemi", "Lenfoma", "Tümör", "Malign", "Neoplazm", "Metastaz", "Adenokarsinom", "Melanom"],
    "Ortopedi": ["Kırık", "Kas", "Artrit", "Osteoartrit", "Romatizmal", "Siyatik", "Fibromiyalji", "Kemik"],
    "Kadın Hastalıkları ve Doğum": ["Endometriozis", "Rahim", "Adet", "Gebelik", "Doğum"],
    "KBB (Kulak Burun Boğaz)": ["Sinüzit", "Farenjit", "Larenjit", "Burun", "Kulak", "Boğaz"],
    "Göz Hastalıkları": ["Glokom", "Göz", "Keratit", "Katarakt"],
    "Hematoloji": ["Anemi", "Lösemi", "Trombositopeni", "Hemofili"],
    "Genel Cerrahi": ["Apandisit", "Safra Taşı", "Fıtık", "Kolesistit", "Hemoroid", "Gastroparezi"],
    "Nöroşirürji": ["Beyin Tümörü", "Siringomiyeli", "Ependimom"],
}


# Build inverse mapping
rows = []
for disease in diseases:
    assigned = None
    for dept, keywords in DEPARTMENT_LOOKUP.items():
        if any(word.lower() in disease.lower() for word in keywords):
            assigned = dept
            break
    rows.append({"Disease": disease, "Department": assigned or "Genel Dahiliye"})

# Create dataframe and save
df = pd.DataFrame(rows)
df.to_csv("disease_department_lookup.csv", index=False, encoding="utf-8")
