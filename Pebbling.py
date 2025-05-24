import streamlit as st
import os
import json
import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from supabase import create_client, Client

# --- Configuration ---
st.set_page_config(layout="wide")
st.title("🪨 Pebbling")

# --- Paths ---
DAILY_WORD_PATH = "word_cards"
TIQIAO_DATA_PATH = "tiqiao_cards"
Path(DAILY_WORD_PATH).mkdir(exist_ok=True)
Path(TIQIAO_DATA_PATH).mkdir(exist_ok=True)

# --- Email Configuration (Cleaned Version) ---
try:
    # 尝试加载 secrets (不再打印调试信息)
    sender_email_daily = st.secrets["email_daily"]["sender_email"]
    app_password_daily = st.secrets["email_daily"]["app_password"]
    recipient_email_daily = st.secrets["email_daily"]["recipient_email"]

    sender_email_tiqiao = st.secrets["email_tiqiao"]["sender_email"]
    app_password_tiqiao = st.secrets["email_tiqiao"]["app_password"]
    recipient_email_tiqiao = st.secrets["email_tiqiao"]["recipient_email"]

    # 统一用 [recipients] 里的邮箱作为推送可选项
    recipient_list = st.secrets["recipients"]["emails"]

except KeyError as e:
    # 如果缺少键，显示错误并停止
    st.error(f"❌ **配置错误:** `secrets.toml` 文件缺少必要的键: `{e}`。请检查文件内容。")
    st.error("确保文件中有 `[email_daily]` 和 `[email_tiqiao]` 部分，且包含 `sender_email`, `app_password`, `recipient_email`。")
    st.stop()
except FileNotFoundError:
    # 如果找不到文件，显示错误并停止
    st.error("❌ **配置错误:** 未找到 `secrets.toml` 文件。")
    st.error("请确保 `secrets.toml` 文件位于 `.streamlit` 文件夹内，并且 `.streamlit` 文件夹与 `Pebbling.py` 在同一目录下。")
    st.stop()
except Exception as e: # 捕获其他潜在错误
    st.error(f"❌ **配置错误:** 加载 `secrets.toml` 失败，请检查文件格式。")
    st.error(f"详细信息: {type(e).__name__} - {e}")
    st.stop()

# --- Secrets 加载成功后，代码继续向下执行 ---
# ================================================
# SECTION 1: DAILY WORD CARD (每日词卡)
# ================================================

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Daily Card Session State ---
# Top of Script - Revised Initialization
if "daily_grabbed" not in st.session_state: st.session_state.daily_grabbed = False
if "daily_edit_index" not in st.session_state: st.session_state.daily_edit_index = None
if "daily_editing_filename" not in st.session_state: st.session_state.daily_editing_filename = None
# Add deferred reset flag initialization
if "should_reset_daily_form" not in st.session_state:
    st.session_state.should_reset_daily_form = False

# Define field list
daily_form_fields = ["daily_title", "daily_phonetic", "daily_definition", "daily_example", "daily_note", "daily_source", "daily_status"]

# Initialize fields ONLY if they don't exist at all
for key in daily_form_fields:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "daily_status" else "未审阅"
# --- Daily Card Utilities ---
def load_daily_cards():
    res = supabase.table("daily_cards").select("*").execute()
    cards = res.data if res.data else []
    # 自动补全 _filename 字段（如果有 filename 字段则用之，否则用 id/date 拼接）
    for card in cards:
        if "_filename" not in card or not card["_filename"]:
            # 尝试用 date+id 拼接
            date = card.get("date", "nodate")
            cid = card.get("id", "noid")
            card["_filename"] = f"{date}_word_{cid}.json"
    return cards

# --- 用这个完整的新函数替换掉你原来的 save_daily_card 函数 ---
def save_daily_card(card_data, is_editing=False, original_card_info=None):
    """保存新的或更新现有的每日词卡。"""
    if is_editing and original_card_info:
        card_id = original_card_info.get("id")
        update_data = {
            "title": card_data.get("title", ""),
            "phonetic": card_data.get("data", {}).get("音标", ""),
            "definition": card_data.get("data", {}).get("释义", ""),
            "example": card_data.get("data", {}).get("例句", ""),
            "note": card_data.get("data", {}).get("备注", ""),
            "source": card_data.get("data", {}).get("source", ""),
            "status": card_data.get("status", "未审阅"),
            "date": card_data.get("date", original_card_info.get("date"))
        }
        res = supabase.table("daily_cards").update(update_data).eq("id", card_id).execute()
        if hasattr(res, "error") and res.error:
            st.error(f"Supabase 更新失败: {res.error}")
            return False
        return True
    else:
        insert_data = {
            "title": card_data.get("title", ""),
            "phonetic": card_data.get("data", {}).get("音标", ""),
            "definition": card_data.get("data", {}).get("释义", ""),
            "example": card_data.get("data", {}).get("例句", ""),
            "note": card_data.get("data", {}).get("备注", ""),
            "source": card_data.get("data", {}).get("source", ""),
            "status": card_data.get("status", "未审阅"),
            "date": card_data.get("date", datetime.date.today().isoformat())
        }
        res = supabase.table("daily_cards").insert(insert_data).execute()
        if hasattr(res, "error") and res.error:
            st.error(f"Supabase 插入失败: {res.error}")
            return False
        return True
# --- 添加这个新函数 ---
def safe_strip(value):
    return str(value).strip() if value is not None else ""
def remove_daily_duplicates():
    """查找并删除重复的每日词卡 (基于标题，保留第一个)"""
    cards = load_daily_cards() # 加载每日词卡数据
    seen_titles = set()        # 用来存储已经见过的标题 (小写)
    deleted_count = 0
    ids_to_keep = set()        # 存储需要保留的卡片 ID

    # 第一遍：找出每个不重复标题第一次出现的卡片ID
    for card in cards:
        # 获取标题，进行清理（去除首尾空格）并转为小写，用于不区分大小写的比较
        title = safe_strip(card.get('title', '')).lower()
        card_id = card.get("id")

        # 跳过没有标题或ID的无效卡片数据
        if not title or card_id is None:
            st.warning(f"跳过处理每日词卡：缺少标题或ID。卡片数据: {str(card)[:100]}...")
            continue

        # 如果这个标题是第一次见到，就记录下它的ID，表示要保留这个卡片
        if title not in seen_titles:
            seen_titles.add(title)
            ids_to_keep.add(card_id)
        # 如果标题已经见过，则这张卡片是重复的，不需要加入ids_to_keep

    # 第二遍：删除那些ID不在保留列表中的卡片文件
    for card in cards:
         card_id = card.get("id")
         # 检查卡片是否有ID，并且这个ID不在要保留的ID集合中
         if card_id is not None and card_id not in ids_to_keep:
            filename = card.get("_filename") # 获取要删除的文件名
            if filename:
                # 构造完整文件路径，注意使用 DAILY_WORD_PATH
                filepath = os.path.join(DAILY_WORD_PATH, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath) # 删除文件
                        deleted_count += 1
                    except Exception as e:
                        # 如果删除失败，显示警告
                        st.warning(f"删除重复每日词卡文件 {filename} 失败: {e}")
            else:
                # 如果找不到文件名，也显示警告
                st.warning(f"无法删除重复每日词卡 (ID: {card_id})，因为缺少 _filename 信息。")

    return deleted_count # 返回删除的卡片数量
# --- 新函数结束 ---

# --- Daily Card Callbacks ---
def daily_start_edit(idx, all_cards):
    if 0 <= idx < len(all_cards):
        st.session_state.daily_edit_index = idx
        card = all_cards[idx]
        st.session_state.daily_title = card.get("title", "")
        st.session_state.daily_phonetic = card.get("data", {}).get("音标", "")
        st.session_state.daily_definition = card.get("data", {}).get("释义", "")
        st.session_state.daily_example = card.get("data", {}).get("例句", "")
        st.session_state.daily_note = card.get("data", {}).get("备注", "")
        st.session_state.daily_source = card.get("data", {}).get("source", "")
        st.session_state.daily_status = card.get("status", "未审阅")
        st.session_state.daily_editing_filename = card.get("_filename")
    else:
        st.error("无效的每日词卡编辑索引。")
        daily_cancel_edit()

# VVVV --- 用这段代码替换原来的 daily_cancel_edit 函数 --- VVVV
def daily_cancel_edit():
    st.session_state.daily_edit_index = None
    st.session_state.daily_editing_filename = None
    st.session_state.daily_grabbed = False
    st.session_state.should_reset_daily_form = True
# ^^^^ --- 替换结束 --- ^^^^
def daily_clear_form_state():
    daily_cancel_edit()

# --- Daily Card Scraper ---
def scrape_merriam_webster():
    try:
        url = "https://www.merriam-webster.com/word-of-the-day"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')

        # 词条：优先 .word-and-pronunciation h1，其次 <title>
        w = ""
        tag = soup.select_one(".word-and-pronunciation h1")
        if tag:
            w = tag.text.strip()
        else:
            title_tag = soup.find('title')
            if title_tag:
                m = re.search(r"Word of the Day: ([^|]+)", title_tag.text)
                w = m.group(1).strip() if m else ""

        # 音标
        phon = soup.select_one('.word-syllables')
        p = phon.text.strip() if phon else ""

        # 释义
        defp = soup.select_one('.wod-definition-container > p')
        d = defp.text.strip() if defp else ""

        # 例句
        e = ""
        for ptag in soup.find_all('p'):
            t = ptag.get_text().strip()
            if t.startswith('//'):
                e = t.lstrip('/').strip()
                break

        # 写入 session_state
        st.session_state.daily_title = w
        st.session_state.daily_phonetic = p
        st.session_state.daily_definition = d
        st.session_state.daily_example = e
        st.session_state.daily_note = ""
        st.session_state.daily_source = url
        st.session_state.daily_status = "未审阅"
        st.session_state.daily_grabbed = True

        return True
    except Exception as e:
        st.error(f"Merriam 抓取失败：{e}")
        return False

# --- Daily Card Sidebar Section ---
st.sidebar.title("📝 编辑区")
st.sidebar.divider()
st.sidebar.header("📖 每日词卡")
# --- 在每日词卡的侧边栏部分添加这个 Expander ---

# Daily Card Duplicate Removal Tool
with st.sidebar.expander("🧹 清理重复每日词卡"):
    # 创建按钮，注意 key 和 提示信息 都要区分于推敲卡片的按钮
    if st.button("🚫 删除重复项 (每日)", key="daily_remove_duplicates_button"):
        deleted_count = remove_daily_duplicates() # 调用刚刚添加的新函数
        if deleted_count > 0:
            st.success(f"成功删除 {deleted_count} 条重复每日词卡！") # 修改提示信息
        else:
            st.info("未找到重复的每日词卡。") # 修改提示信息
        # 清理后刷新界面
        st.rerun()
# --- 添加侧边栏代码结束 ---
if st.sidebar.button("📗 抓取 Merriam", key="daily_scrape_button"):
    if scrape_merriam_webster():
        st.session_state.daily_grabbed = True
        st.sidebar.success("抓取成功！")
    st.rerun()

# Daily Card Form
daily_is_editing = st.session_state.daily_edit_index is not None
daily_form_header = "编辑每日词卡" if daily_is_editing else "新增每日词卡"
st.sidebar.subheader(daily_form_header)

# Deferred reset before rendering the form
if st.session_state.get("should_reset_daily_form", False):
    for key in daily_form_fields:
        st.session_state[key] = "" if key != "daily_status" else "未审阅"
    st.session_state.should_reset_daily_form = False

with st.sidebar.form(key="daily_card_form", clear_on_submit=False):
    st.text_input("词条", key="daily_title")
    st.text_input("音标", key="daily_phonetic")
    st.text_area("释义", key="daily_definition")
    st.text_area("例句", key="daily_example")
    st.text_area("备注", key="daily_note")
    st.text_input("来源链接", key="daily_source")
    status_options = ["未审阅", "已审阅", "待推送", "已推送"]
    # 移除 index 参数，确保 st.session_state.daily_status 在此之前已正确初始化
    st.selectbox("状态", status_options, key="daily_status") # <--- 修改后

    daily_submit_label = "💾 更新词卡" if daily_is_editing else "💾 添加词卡"
    daily_submitted = st.form_submit_button(daily_submit_label)

if daily_submitted:
    card_data = {
        "title": st.session_state.daily_title,
        "data": {
            "音标": st.session_state.daily_phonetic,
            "释义": st.session_state.daily_definition,
            "例句": st.session_state.daily_example,
            "备注": st.session_state.daily_note,
            "source": st.session_state.daily_source
        },
        "status": st.session_state.daily_status
    }
    if save_daily_card(card_data, is_editing=daily_is_editing):
        msg = "更新成功！" if daily_is_editing else "添加成功！"
        st.sidebar.success(msg)
        daily_cancel_edit()  # Only change session state here
        st.rerun()           # Only call rerun ONCE, after all state changes
    else:
        st.sidebar.error("保存失败。")


if daily_is_editing:
    if st.sidebar.button("🚫 取消编辑 (每日词卡)", key="daily_cancel_edit_button", on_click=daily_cancel_edit):
        pass # on_click handles it

# Daily Card Excel Upload
st.sidebar.subheader("📂 批量上传 (每日词卡)")
daily_uploaded_file = st.sidebar.file_uploader("上传 Excel 文件", type=["xlsx"], key="daily_upload_file")
if daily_uploaded_file:
    try:
        df = pd.read_excel(daily_uploaded_file, na_filter=False)
        existing_cards = load_daily_cards()
        existing_titles = {c.get("title", "").strip().lower() for c in existing_cards}
        imported_count = 0
        for idx, row in df.iterrows():
            title = str(row.get("Word", "")).strip()
            if not title or title.lower() in existing_titles:
                continue
            card_data = {
                "title": title,
                "data": {
                    "音标": str(row.get("Phonetic", "")).strip(),
                    "释义": str(row.get("Definition", "")).strip(),
                    "例句": str(row.get("Example", "")).strip(),
                    "备注": str(row.get("Note", "")).strip(),
                    "source": str(row.get("Source URL", "")).strip()
                },
                "status": str(row.get("Status", "未审阅")).strip()
            }
            if save_daily_card(card_data, is_editing=False):
                imported_count += 1
                existing_titles.add(title.lower()) # Add newly imported title

        if imported_count > 0:
            st.sidebar.success(f"成功导入 {imported_count} 条每日词卡！")
            daily_clear_form_state() # Clear form after import
            st.rerun()
        else:
            st.sidebar.info("没有新的每日词卡需要导入，或文件格式不符。")
    except Exception as e:
        st.sidebar.error(f"每日词卡导入失败: {e}")


# ================================================
# SECTION 2: TIQIAO CARD (推敲词卡)
# ================================================
st.sidebar.divider()
st.sidebar.header("✍️ 推敲词卡")

# --- Tiqiao Card Session State ---
if "tiqiao_edit_index" not in st.session_state:
    st.session_state.tiqiao_edit_index = None
if "tiqiao_editing_filename" not in st.session_state:
    st.session_state.tiqiao_editing_filename = None

tiqiao_form_fields = ["tiqiao_orig_cn", "tiqiao_orig_en", "tiqiao_meaning", "tiqiao_recommend", "tiqiao_qtype", "tiqiao_status"]
for key in tiqiao_form_fields:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "tiqiao_status" else "未审阅"

# --- Tiqiao Card Utilities ---


def load_tiqiao_cards():
    res = supabase.table("tiqiao_cards").select("*").execute()
    return res.data if res.data else []

def save_tiqiao_card(card_data, is_editing=False, original_card_info=None):
    if is_editing and original_card_info:
        card_id = original_card_info.get("id")
        update_data = {
            "orig_cn": card_data.get("orig_cn", ""),
            "orig_en": card_data.get("orig_en", ""),
            "meaning": card_data.get("meaning", ""),
            "recommend": card_data.get("recommend", ""),
            "qtype": card_data.get("qtype", ""),
            "status": card_data.get("status", "未审阅"),
            "date": card_data.get("date", original_card_info.get("date"))
        }
        res = supabase.table("tiqiao_cards").update(update_data).eq("id", card_id).execute()
        if hasattr(res, "error") and res.error:
            st.error(f"Supabase 更新失败: {res.error}")
            return False
        return True
    else:
        insert_data = {
            "orig_cn": card_data.get("orig_cn", ""),
            "orig_en": card_data.get("orig_en", ""),
            "meaning": card_data.get("meaning", ""),
            "recommend": card_data.get("recommend", ""),
            "qtype": card_data.get("qtype", ""),
            "status": card_data.get("status", "未审阅"),
            "date": card_data.get("date", datetime.date.today().isoformat())
        }
        res = supabase.table("tiqiao_cards").insert(insert_data).execute()
        if hasattr(res, "error") and res.error:
            st.error(f"Supabase 插入失败: {res.error}")
            return False
        return True

def delete_tiqiao_card(card_id):
    res = supabase.table("tiqiao_cards").delete().eq("id", card_id).execute()
    if hasattr(res, "error") and res.error:
        st.error(f"Supabase 删除失败: {res.error}")
        return False
    return True

def remove_tiqiao_duplicates():
    cards = load_tiqiao_cards()
    seen_content = set()
    deleted_count = 0
    ids_to_keep = set()

    # First pass: identify unique cards and their IDs
    for card in cards:
         key = (
            safe_strip(card.get('orig_cn')), safe_strip(card.get('orig_en')),
            safe_strip(card.get('meaning')), safe_strip(card.get('recommend')),
            safe_strip(card.get('qtype')),
         )
         # Keep the first occurrence
         if key not in seen_content:
             seen_content.add(key)
             ids_to_keep.add(card.get("id"))

    # Second pass: delete cards whose IDs were not marked to keep
    for card in cards:
        if card.get("id") not in ids_to_keep:
            filename = card.get("_filename")
            if filename:
                filepath = os.path.join(TIQIAO_DATA_PATH, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        st.warning(f"删除重复推敲文件 {filename} 失败: {e}")
            else:
                st.warning(f"无法删除重复推敲卡片 (ID: {card.get('id')}): 缺少文件名。")

    return deleted_count


# --- Tiqiao Card Callbacks ---
def tiqiao_start_edit(idx, all_cards):
    if 0 <= idx < len(all_cards):
        st.session_state.tiqiao_edit_index = idx
        card = all_cards[idx]
        st.session_state.tiqiao_orig_cn = card.get("orig_cn", "")
        st.session_state.tiqiao_orig_en = card.get("orig_en", "")
        st.session_state.tiqiao_meaning = card.get("meaning", "")
        st.session_state.tiqiao_recommend = card.get("recommend", "")
        st.session_state.tiqiao_qtype = card.get("qtype", "")
        st.session_state.tiqiao_status = card.get("status", "未审阅")
        st.session_state.tiqiao_editing_filename = card.get("_filename")
    else:
        st.error("无效的推敲词卡编辑索引。")
        tiqiao_cancel_edit()

# --- 复制并替换这个函数 ---
def tiqiao_cancel_edit():
    # 重置编辑索引和文件名状态
    st.session_state.tiqiao_edit_index = None
    st.session_state.tiqiao_editing_filename = None

    # 直接、明确地重置每个表单字段的 Session State
    st.session_state.tiqiao_orig_cn = ""
    st.session_state.tiqiao_orig_en = ""
    st.session_state.tiqiao_meaning = ""
    st.session_state.tiqiao_recommend = ""
    st.session_state.tiqiao_qtype = ""
    st.session_state.tiqiao_status = "未审阅" # 设置回默认状态
# --- 函数替换结束 ---

def tiqiao_clear_form_state():
    tiqiao_cancel_edit()
# --- 清空表单标记与执行 ---
if "reset_tiqiao_flag" not in st.session_state:
    st.session_state.reset_tiqiao_flag = False

if st.session_state.reset_tiqiao_flag:
    tiqiao_cancel_edit()
    st.session_state.reset_tiqiao_flag = False
# --- Tiqiao Card Sidebar Section ---
tiqiao_is_editing = st.session_state.tiqiao_edit_index is not None
tiqiao_form_header = "编辑推敲词卡" if tiqiao_is_editing else "新增推敲词卡"
st.sidebar.subheader(tiqiao_form_header)

with st.sidebar.form(key="tiqiao_card_form", clear_on_submit=False):
    st.text_area("原始中文", key="tiqiao_orig_cn")
    st.text_input("原始英文", key="tiqiao_orig_en")
    st.text_area("真实内涵", key="tiqiao_meaning")
    st.text_input("推荐英文", key="tiqiao_recommend")
    st.text_input("问题类型", key="tiqiao_qtype")
    tiqiao_status_options = ["未审阅", "已审阅", "待推送", "已推送"]
    # 移除 index 参数，确保 st.session_state.tiqiao_status 在此之前已正确初始化
    st.selectbox("状态", tiqiao_status_options, key="tiqiao_status") # <--- 修改后

    tiqiao_submit_label = "💾 更新词卡" if tiqiao_is_editing else "💾 添加词卡"
    tiqiao_submitted = st.form_submit_button(tiqiao_submit_label)

if tiqiao_submitted:
    card_data = {
        "orig_cn": st.session_state.tiqiao_orig_cn,
        "orig_en": st.session_state.tiqiao_orig_en,
        "meaning": st.session_state.tiqiao_meaning,
        "recommend": st.session_state.tiqiao_recommend,
        "qtype": st.session_state.tiqiao_qtype,
        "status": st.session_state.tiqiao_status
    }

    if save_tiqiao_card(card_data, is_editing=tiqiao_is_editing):
        msg = "更新成功！" if tiqiao_is_editing else "添加成功！"
        st.sidebar.success(msg)
        st.session_state.reset_tiqiao_flag = True
        st.rerun()
    else:
        st.sidebar.error("保存失败。")

if tiqiao_is_editing:
    if st.sidebar.button("🚫 取消编辑 (推敲词卡)", key="tiqiao_cancel_edit_button", on_click=tiqiao_cancel_edit):
        pass

# --- 复制并替换你代码中对应的整个推敲词卡上传部分 ---

st.sidebar.subheader("📂 批量上传 (推敲词卡)")
tiqiao_uploaded_file = st.sidebar.file_uploader("上传 Excel 文件", type=["xlsx"], key="tiqiao_upload_file")
if tiqiao_uploaded_file:
    try:
        df = pd.read_excel(tiqiao_uploaded_file, na_filter=False)
        existing_cards = load_tiqiao_cards()
        existing_set = set(
            (safe_strip(c.get('orig_cn')), safe_strip(c.get('orig_en')), safe_strip(c.get('meaning')),
             safe_strip(c.get('recommend')), safe_strip(c.get('qtype')))
            for c in existing_cards
        )
        imported_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            orig_cn = safe_strip(row.get('原始中文', ''))
            orig_en = safe_strip(row.get('原始英文', ''))
            meaning = safe_strip(row.get('真实内涵', ''))
            recommend = safe_strip(row.get('推荐英文', ''))
            qtype = safe_strip(row.get('问题类型', ''))
            status = safe_strip(row.get('状态', '未审阅'))

            if not any([orig_cn, orig_en, meaning, recommend, qtype]):
                skipped_count +=1
                continue

            content_tuple = (orig_cn, orig_en, meaning, recommend, qtype)
            if content_tuple in existing_set:
                skipped_count +=1
                continue

            card_data = {
                'orig_cn': orig_cn, 'orig_en': orig_en, 'meaning': meaning,
                'recommend': recommend, 'qtype': qtype, 'status': status
            }

            if save_tiqiao_card(card_data, is_editing=False):
                imported_count += 1
                existing_set.add(content_tuple)
            else:
                 st.sidebar.warning(f"导入行失败: {row.get('原始中文', '')[:20]}...")
                 skipped_count += 1

        # --- 检查这里 ---
        if imported_count > 0:
            st.sidebar.success(f"成功导入 {imported_count} 条推敲词卡！")
            # 确认下面这行确实被注释掉或删除了！
            # tiqiao_clear_form_state()
            st.rerun() # Rerun 更新界面显示新导入的卡片
        else:
            st.sidebar.info(f"没有新的推敲词卡需要导入（跳过 {skipped_count} 行：空行或重复项）。")
        # --- 检查结束 ---

    except Exception as e:
        st.sidebar.error(f"推敲词卡导入失败: {type(e).__name__} - {e}") # 显示更详细的错误

# --- 推敲词卡 Excel 上传部分结束 ---

# Tiqiao Duplicate Removal Tool
with st.sidebar.expander("🧹 清理重复推敲卡片"):
    if st.button("🚫 删除重复项", key="tiqiao_remove_duplicates_button"):
        deleted_count = remove_tiqiao_duplicates()
        if deleted_count > 0:
            st.success(f"成功删除 {deleted_count} 条重复推敲卡片！")
        else:
            st.info("未找到重复的推敲卡片。")
        st.rerun()


# ================================================
# SECTION 3: MAIN AREA DISPLAY
# ================================================
st.divider()
st.header("📖 每日词卡列表")

# --- Daily Card Main Area Display ---
all_daily_cards = load_daily_cards()
daily_states = ["所有","未审阅","已审阅","待推送","已推送"]
daily_tabs = st.tabs(daily_states)

for i, state in enumerate(daily_states):
    with daily_tabs[i]:
        st.subheader(f"状态：{state}")

        if state=="待推送":
            # 每日词卡推送收件人选择，使用 [recipients] 里的邮箱
            selected_recipients = st.multiselect(
                "选择推送收件人",
                recipient_list,
                default=[recipient_list[0]] if recipient_list else [],
                key=f"daily_recipients_{i}"
            )
            if st.button("📬 推送待处理每日词卡", key=f"daily_push_email_tab{i}"):
                cards_to_push = [c for c in load_daily_cards() if c.get("status") == "待推送"]
                if not cards_to_push:
                    st.warning("没有状态为 '待推送' 的每日词卡。")
                else:
                    body = ""
                    for c in cards_to_push:
                         body += (
                            f"【{c.get('title','')}】\n"
                            f"日期: {c.get('date', '-')}\n"
                            f"音标: {c.get('data',{}).get('音标','')}\n"
                            f"释义: {c.get('data',{}).get('释义','')}\n"
                            f"例句: {c.get('data',{}).get('例句','')}\n"
                            f"备注: {c.get('data',{}).get('备注','')}\n"
                            f"来源: {c.get('data',{}).get('source','')}\n\n"
                         )
                    if not selected_recipients:
                        st.warning("请选择至少一个收件人。")
                        st.stop()
                    try:
                        # --- 邮件准备和发送 ---
                        msg = MIMEMultipart()
                        msg["From"] = sender_email_daily
                        msg["To"] = ", ".join(selected_recipients)
                        msg["Subject"] = f"每日词卡推送 {datetime.date.today()}"
                        msg.attach(MIMEText(body, "plain", "utf-8"))

                        with smtplib.SMTP_SSL("smtp.feishu.cn", 465) as s:
                            s.login(sender_email_daily, app_password_daily)
                            if not selected_recipients:
                                st.warning("请选择至少一个收件人。")
                                st.stop()
                            s.sendmail(sender_email_daily, selected_recipients, msg.as_string())

                        # --- 邮件发送成功后，更新卡片状态 ---
                        # (确保下面的代码有正确的缩进，在 try 块内部)
                        saved_count = 0
                        all_cards_reloaded = load_daily_cards() # 加载最新数据
                        # 找出需要更新的卡片的索引和原始信息
                        updates_to_perform = []
                        for idx, card in enumerate(all_cards_reloaded):
                            if card.get("status") == "待推送":
                                updates_to_perform.append({
                                    'original_info': {
                                        "id": card.get("id"),
                                        "date": card.get("date"),
                                        "filename": card.get("_filename")
                                    },
                                    'updated_data': {
                                        "title": card.get("title"),
                                        "data": card.get("data"),
                                        "status": "已推送" # 直接设置新状态
                                    },
                                    'original_index': idx # 记录原始索引，虽然新save函数不用了，但保留可能有用
                                })

                        # 遍历并保存更新 (确保这个 for 循环有正确的缩进)
                        for update in updates_to_perform:
                            # 使用修改后的 save_daily_card 函数 (假设你之前已经替换了)
                            # 直接传递 original_info，不依赖 session state
                            if save_daily_card(
                                update['updated_data'],
                                is_editing=True,
                                original_card_info=update['original_info'] # 传递原始信息
                            ):
                                saved_count += 1
                            else:
                                # 如果保存失败，记录一下
                                st.warning(f"更新卡片 ID {update['original_info'].get('id')} 状态失败。")

                        # 显示最终结果 (确保这部分有正确的缩进)
                        if saved_count == len(updates_to_perform):
                             st.success(f"成功推送并更新 {saved_count} 条词卡状态！")
                        else:
                             st.warning(f"尝试推送 {len(updates_to_perform)} 条，成功更新 {saved_count} 条状态。")
                        st.rerun() # 更新成功后刷新页面

                    # --- 必须要有 except 来捕获错误 ---
                    except Exception as e:
                        # (确保 except 和 try 对齐，并且内部代码有缩进)
                        st.error(f"邮件推送或状态更新失败：{e}")
# --- try...except 代码块替换结束 ---

        filtered_daily_cards = [
            (idx, card) for idx, card in enumerate(all_daily_cards)
            if state == "所有" or card.get("status") == state
        ]
        if not filtered_daily_cards:
            st.info(f"无 '{state}' 状态的每日词卡。")
        else:
            for original_idx, card in filtered_daily_cards:
                col1, col2 = st.columns([5,1])

                title = card.get('title', '-')
                card_id = card.get('id', 'N/A')
                date = card.get('date', '-')
                phonetic = card.get('data', {}).get('音标', '-')
                definition = card.get('data', {}).get('释义', '-')
                example = card.get('data', {}).get('例句', '-')
                note = card.get('data', {}).get('备注', '-')
                status_val = card.get('status', '未审阅')
                source = card.get('data', {}).get('source', '')

                # --- 使用 <br> 强制换行 ---
                display_text = f"""
                **词条**: {title} `(ID: {card_id})`<br>
                **日期**: {date}<br>
                **音标**: {phonetic}<br>
                **释义**: {definition}<br>
                **例句**: {example}<br>
                **备注**: {note}<br>
                **状态**: {status_val}
                """
                if source:
                    # 使用 HTML a 标签创建链接
                    display_text += f"<br>**来源**: <a href='{source}' target='_blank'>🔗 Link</a>"
                else:
                    display_text += f"<br>**来源**: -"
                # --- 修改结束 ---

                col1.markdown(display_text, unsafe_allow_html=True)

                edit_button_key = f"edit_daily_tab{i}_card{card_id}"
                delete_button_key = f"delete_daily_tab{i}_card{card_id}"

                col2.button("✏️", key=edit_button_key, on_click=daily_start_edit, args=(original_idx, all_daily_cards))
                if col2.button("🗑️", key=delete_button_key):
                    if delete_daily_card(card.get("id")):
                        st.success(f"删除词卡 ID {card.get('id')} 成功")
                        st.rerun()
                    else:
                        st.error(f"删除词卡 ID {card.get('id')} 失败")


st.divider()
st.header("✍️ 推敲词卡列表")
all_tiqiao_cards = load_tiqiao_cards()
tiqiao_states = ["所有","未审阅","已审阅","待推送","已推送"]
tiqiao_tabs = st.tabs(tiqiao_states)

for i, state in enumerate(tiqiao_states):
    with tiqiao_tabs[i]:
        st.subheader(f"状态：{state}")
# --- 替换推敲词卡列表中的 "待推送" Tab 页处理逻辑 ---
        if state == "待推送":
            # 推敲词卡推送收件人选择，使用 [recipients] 里的邮箱
            selected_recipients = st.multiselect(
                "选择推送收件人",
                recipient_list,
                default=[recipient_list[0]] if recipient_list else [],
                key=f"tiqiao_recipients_{i}"
            )
            if st.button("📬 推送待处理推敲词卡", key=f"tiqiao_push_email_tab{i}"):
                cards_to_push = [c for c in load_tiqiao_cards() if c.get("status") == "待推送"]
                if not cards_to_push:
                    st.warning("没有状态为 '待推送' 的推敲词卡。")
                else:
                    # --- 准备邮件内容 ---
                    body = ""
                    for c in cards_to_push:
                        body += (
                            f"【{c.get('orig_cn','')}】\n"
                            f"原始英文: {c.get('orig_en','')}\n"
                            f"真实内涵: {c.get('meaning','')}\n"
                            f"推荐英文: {c.get('recommend','')}\n"
                            f"问题类型: {c.get('qtype','')}\n"
                            f"日期: {c.get('date','')}\n\n"
                        )
                    if not selected_recipients:
                        st.warning("请选择至少一个收件人。")
                        st.stop()
                    # --- 发送邮件并更新状态 ---
                    try: 
                        # 初始化邮件对象
                        msg = MIMEMultipart()
                        msg["From"] = sender_email_tiqiao # 使用推敲邮箱配置
                        msg["To"] = ", ".join(selected_recipients)
                        msg["Subject"] = f"推敲词卡推送 {datetime.date.today()}" # 设置主题
                        msg.attach(MIMEText(body, "plain", "utf-8"))

                        # 建立连接并发送
                        with smtplib.SMTP_SSL("smtp.feishu.cn", 465) as s:
                            s.login(sender_email_tiqiao, app_password_tiqiao) # 使用推敲邮箱配置
                            # 处理可能的多个收件人
                            if not selected_recipients:
                                st.warning("请选择至少一个收件人。")
                                st.stop()
                            s.sendmail(sender_email_tiqiao, selected_recipients, msg.as_string())

                        # --- 邮件发送成功，开始更新状态 ---
                        saved_count = 0
                        all_cards_reloaded = load_tiqiao_cards() # 重新加载以获取最新列表

                        # 收集需要更新的信息
                        updates_to_perform = []
                        for idx, card in enumerate(all_cards_reloaded):
                            if card.get("status") == "待推送":
                                updates_to_perform.append({
                                    'original_info': {
                                        "id": card.get("id"),
                                        "date": card.get("date"),
                                        "filename": card.get("_filename")
                                    },
                                    'updated_data': { # 提供保存所需的所有字段
                                        "orig_cn": card.get("orig_cn"),
                                        "orig_en": card.get("orig_en"),
                                        "meaning": card.get("meaning"),
                                        "recommend": card.get("recommend"),
                                        "qtype": card.get("qtype"),
                                        "status": "已推送" # 设置新状态
                                    }
                                })

                        # 循环调用保存函数进行更新
                        for update in updates_to_perform:
                            if save_tiqiao_card(
                                update['updated_data'],
                                is_editing=True,
                                original_card_info=update['original_info'] # 传递原始信息
                            ):
                                saved_count += 1
                            else:
                                st.warning(f"更新推敲卡片 ID {update['original_info'].get('id')} 状态失败。")
                        # --- 状态更新结束 ---

                        # 显示结果
                        if saved_count == len(updates_to_perform):
                            st.success(f"成功推送并更新 {saved_count} 条推敲词卡状态！")
                        else:
                            st.warning(f"尝试推送 {len(updates_to_perform)} 条，成功更新 {saved_count} 条状态。")
                        st.rerun() # 刷新界面

                    # --- 捕获错误 ---
                    except Exception as e:
                        st.error(f"推敲词卡邮件推送或状态更新失败：{e}")
# --- 推送逻辑替换结束 ---
        filtered_tiqiao_cards = [
            (idx, card) for idx, card in enumerate(all_tiqiao_cards)
            if state == "所有" or card.get("status") == state
        ]

        if not filtered_tiqiao_cards:
            st.info(f"无 '{state}' 状态的推敲词卡。")
            continue

        for original_idx, card in filtered_tiqiao_cards:
            col1, col2 = st.columns([5,1])

            card_id = card.get('id', 'N/A')
            orig_cn = card.get('orig_cn', '-')
            orig_en = card.get('orig_en', '-')
            meaning = card.get('meaning', '-') # 确保 JSON 数据是干净的
            recommend = card.get('recommend', '-')
            qtype = card.get('qtype', '-')
            status = card.get('status', '未审阅')
            date = card.get('date', '-')

            # --- 使用 <br> 强制换行 ---
            display_text = f"""
            **原始中文**: {orig_cn} `(ID: {card_id})`<br>
            **原始英文**: {orig_en}<br>
            **真实内涵**: {meaning}<br>
            **推荐英文**: {recommend}<br>
            **问题类型**: {qtype}<br>
            **状态**: {status}<br>
            **日期**: {date}
            """
            # --- 修改结束 ---

            col1.markdown(display_text, unsafe_allow_html=True)

            edit_button_key = f"edit_tiqiao_tab{i}_card{card_id}"
            delete_button_key = f"delete_tiqiao_tab{i}_card{card_id}"
            group_button_key = f"group_tiqiao_tab{i}_card{card_id}"

            col2.button("✏️", key=edit_button_key, on_click=tiqiao_start_edit, args=(original_idx, all_tiqiao_cards))
            if col2.button("🗑️", key=delete_button_key):
                 if delete_tiqiao_card(card.get("id")):
                      st.success(f"删除推敲卡片 ID {card.get('id')} 成功")
                      if st.session_state.tiqiao_edit_index == original_idx:
                          tiqiao_cancel_edit()
                      st.rerun()
                 else:
                      st.error(f"删除推敲卡片 ID {card.get('id')} 失败")
            
# --- 脚本文件结束 ---

# --- Daily Card 删除函数 ---
def delete_daily_card(card_id):
    res = supabase.table("daily_cards").delete().eq("id", card_id).execute()
    if hasattr(res, "error") and res.error:
        st.error(f"Supabase 删除失败: {res.error}")
        return False
    return True
