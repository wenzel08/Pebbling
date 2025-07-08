#!/usr/bin/env python3
"""
调试推敲词卡插入问题的脚本
"""
import os
import sys
import toml
from supabase import create_client
import datetime

def load_supabase():
    secrets = toml.load('.streamlit/secrets.toml')
    supa = secrets['supabase']
    return create_client(supa['url'], supa['key'])

def test_tiqiao_insert():
    supabase = load_supabase()
    
    # 测试数据
    test_data = {
        "status": "未审阅",
        "date": datetime.date.today().isoformat(),
        "orig_cn": "测试中文",
        "orig_en": "test english",
        "meaning": "测试含义",
        "recommend": "recommended english",
        "qtype": "测试类型"
    }
    
    print("🔍 测试推敲词卡插入...")
    print(f"插入数据: {test_data}")
    
    try:
        # 先检查表结构
        print("\n📋 检查表结构...")
        res = supabase.table("tiqiao_cards").select("*").limit(1).execute()
        if res.data:
            print("✅ 表存在且有数据")
            sample_record = res.data[0]
            print(f"示例记录结构: {list(sample_record.keys())}")
        else:
            print("⚠️ 表存在但无数据")
        
        # 尝试插入
        print("\n💾 尝试插入数据...")
        res = supabase.table("tiqiao_cards").insert(test_data).execute()
        
        if hasattr(res, "error") and res.error:
            print(f"❌ 插入失败: {res.error}")
            return False
        else:
            print("✅ 插入成功!")
            if res.data:
                print(f"插入的记录: {res.data[0]}")
            return True
            
    except Exception as e:
        print(f"❌ 异常: {type(e).__name__} - {e}")
        return False

def check_table_constraints():
    supabase = load_supabase()
    
    print("\n🔍 检查表约束...")
    try:
        # 获取表信息
        res = supabase.table("tiqiao_cards").select("*").limit(1).execute()
        if res.data:
            print("✅ 可以查询表")
        else:
            print("⚠️ 表为空")
    except Exception as e:
        print(f"❌ 查询失败: {e}")

def test_minimal_insert():
    supabase = load_supabase()
    
    print("\n🔍 测试最小数据插入...")
    
    # 测试不同的数据组合
    test_cases = [
        {
            "name": "只有status",
            "data": {"status": "未审阅"}
        },
        {
            "name": "status + date",
            "data": {"status": "未审阅", "date": datetime.date.today().isoformat()}
        },
        {
            "name": "完整数据",
            "data": {
                "status": "未审阅",
                "date": datetime.date.today().isoformat(),
                "orig_cn": "测试",
                "orig_en": "test",
                "meaning": "含义",
                "recommend": "推荐",
                "qtype": "类型"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📝 测试: {test_case['name']}")
        try:
            res = supabase.table("tiqiao_cards").insert(test_case['data']).execute()
            if hasattr(res, "error") and res.error:
                print(f"❌ 失败: {res.error}")
            else:
                print("✅ 成功")
        except Exception as e:
            print(f"❌ 异常: {e}")

if __name__ == "__main__":
    print("🪨 Pebbling 推敲词卡插入调试工具")
    print("=" * 50)
    
    check_table_constraints()
    test_minimal_insert()
    test_tiqiao_insert() 