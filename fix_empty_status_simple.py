#!/usr/bin/env python3
"""
修复状态为空的每日词卡 - 简化版本
将空状态的词条设置为"未审阅"状态
"""

import os
import sys
import json
from supabase import create_client, Client

def load_secrets():
    """加载secrets配置"""
    try:
        # 尝试从.streamlit/secrets.toml加载配置
        import toml
        secrets_path = os.path.join(".streamlit", "secrets.toml")
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets = toml.load(f)
                return secrets.get("supabase", {})
    except ImportError:
        pass
    
    # 如果无法加载toml，尝试从环境变量读取
    return {
        "url": os.getenv("SUPABASE_URL"),
        "key": os.getenv("SUPABASE_KEY")
    }

def fix_empty_status():
    """修复状态为空的词条"""
    print("🔧 开始修复空状态的词条...")
    
    # 加载配置
    supabase_config = load_secrets()
    if not supabase_config.get("url") or not supabase_config.get("key"):
        print("❌ 无法加载Supabase配置")
        print("请确保.streamlit/secrets.toml文件存在且包含supabase配置")
        return
    
    # 创建Supabase客户端
    supabase = create_client(supabase_config["url"], supabase_config["key"])
    
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
        print(f"错误类型: {type(e).__name__}")

if __name__ == "__main__":
    print("🪨 Pebbling 状态修复工具 (简化版)")
    print("=" * 50)
    fix_empty_status() 