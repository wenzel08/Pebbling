#!/usr/bin/env python3
"""
批量修正所有包含"未审阅"二字的status字段为完全等于"未审阅"
"""
import os
import sys
import toml
from supabase import create_client

def load_supabase():
    secrets = toml.load('.streamlit/secrets.toml')
    supa = secrets['supabase']
    return create_client(supa['url'], supa['key'])

def main():
    supabase = load_supabase()
    res = supabase.table("daily_cards").select("*").execute()
    cards = res.data if res.data else []
    fix_count = 0
    for card in cards:
        status = card.get("status", "")
        if "未审阅" in status and status != "未审阅":
            card_id = card.get("id")
            update_data = {
                "status": "未审阅",
                "date": card.get("date"),
                "data": card.get("data", {}),
                "title": card.get("title", "")
            }
            res2 = supabase.table("daily_cards").update(update_data).eq("id", card_id).execute()
            if not hasattr(res2, "error") or not res2.error:
                print(f"✅ 修正: {card.get('title', 'Unknown')} (ID: {card_id}) 原status: '{status}'")
                fix_count += 1
            else:
                print(f"❌ 修正失败: {card.get('title', 'Unknown')} (ID: {card_id}) - {res2.error}")
    print(f"\n🎉 批量修正完成，共修正 {fix_count} 条词卡。")

if __name__ == "__main__":
    print("🪨 Pebbling 状态批量修正工具")
    print("=" * 40)
    main() 