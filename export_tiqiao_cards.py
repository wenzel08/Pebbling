import os
import json
import csv

json_folder = "tiqiao_cards"
csv_file = "tiqiao_cards_import.csv"

fieldnames = [
    "orig_cn", "orig_en", "meaning", "recommend", "qtype", "status", "date"
]

rows = []
for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        with open(os.path.join(json_folder, filename), "r", encoding="utf-8") as f:
            data = json.load(f)
            row = {
                "orig_cn": data.get("orig_cn", ""),
                "orig_en": data.get("orig_en", ""),
                "meaning": data.get("meaning", ""),
                "recommend": data.get("recommend", ""),
                "qtype": data.get("qtype", ""),
                "status": data.get("status", "未审阅"),
                "date": data.get("date", "")
            }
            rows.append(row)

with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"已导出 {len(rows)} 条推敲词卡到 {csv_file}")