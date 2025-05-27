import os
import json
import csv

json_folder = "word_cards"
csv_file = "daily_cards_import.csv"

fieldnames = [
    "title", "phonetic", "definition", "example", "note", "source", "status", "date"
]

rows = []
for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        with open(os.path.join(json_folder, filename), "r", encoding="utf-8") as f:
            data = json.load(f)
            row = {
                "title": data.get("title", ""),
                "phonetic": data.get("data", {}).get("音标", ""),
                "definition": data.get("data", {}).get("释义", ""),
                "example": data.get("data", {}).get("例句", ""),
                "note": data.get("data", {}).get("备注", ""),
                "source": data.get("data", {}).get("source", ""),
                "status": data.get("status", "未审阅"),
                "date": data.get("date", "")
            }
            rows.append(row)

with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"已导出 {len(rows)} 条每日词卡到 {csv_file}")