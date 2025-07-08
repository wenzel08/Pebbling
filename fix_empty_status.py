#!/usr/bin/env python3
"""
修复状态为空的每日词卡
将空状态的词条设置为"未审阅"状态
"""

import os
import sys
from supabase import create_client, Client
import streamlit as st

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 从Pebbling.py导入配置
try:
    # 尝试导入配置
    from Pebbling import SUPABASE_URL, SUPABASE_KEY, supabase
except ImportError:
    print("❌ 无法导入Pebbling配置，请确保在正确的目录中运行")
    sys.exit(1)

def fix_empty_status():
    """修复状态为空的词条"""
    print("🔧 开始修复空状态的词条...")
    
    try:
        # 加载所有词卡
        res = supabase.table("daily_cards").select("*").execute()
        cards = res.data if res.data else []
        
        print(f"📊 总词卡数: {len(cards)}")
        
        # 统计状态分布
        status_counts = {}
        empty_status_cards = []
        
        for card in cards:
            status = card.get("status", "")
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
            else:
                status_counts["空状态"] = status_counts.get("空状态", 0) + 1
                empty_status_cards.append(card)
        
        print("📈 状态分布:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        if not empty_status_cards:
            print("✅ 没有发现空状态的词条")
            return
        
        print(f"\n🔍 发现 {len(empty_status_cards)} 个空状态的词条")
        
        # 询问用户是否修复
        response = input(f"\n是否要将这 {len(empty_status_cards)} 个词条的状态设置为'未审阅'? (y/n): ")
        
        if response.lower() != 'y':
            print("❌ 取消修复")
            return
        
        # 修复空状态
        fixed_count = 0
        for card in empty_status_cards:
            card_id = card.get("id")
            if card_id:
                update_data = {
                    "status": "未审阅",
                    "date": card.get("date"),
                    "data": card.get("data", {}),
                    "title": card.get("title", "")
                }
                
                res = supabase.table("daily_cards").update(update_data).eq("id", card_id).execute()
                if not hasattr(res, "error") or not res.error:
                    fixed_count += 1
                    print(f"✅ 修复词条: {card.get('title', 'Unknown')} (ID: {card_id})")
                else:
                    print(f"❌ 修复失败: {card.get('title', 'Unknown')} (ID: {card_id}) - {res.error}")
        
        print(f"\n🎉 修复完成！成功修复 {fixed_count} 个词条")
        
        # 显示修复后的状态分布
        print("\n📊 修复后的状态分布:")
        res = supabase.table("daily_cards").select("*").execute()
        cards = res.data if res.data else []
        
        final_status_counts = {}
        for card in cards:
            status = card.get("status", "空状态")
            final_status_counts[status] = final_status_counts.get(status, 0) + 1
        
        for status, count in final_status_counts.items():
            print(f"  {status}: {count}")
            
    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")

if __name__ == "__main__":
    print("🪨 Pebbling 状态修复工具")
    print("=" * 40)
    fix_empty_status() 