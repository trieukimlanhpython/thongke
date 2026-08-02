#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 20:50:24 2025
📋 Ứng dụng Quản lý Công việc (QLCV) - Giữ nguyên 100% code gốc + Đầy đủ đồ thị/thống kê NCKH + Phân quyền
@author: trieukimlanh
"""
import io
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================================
# ⚙️ CẤU HÌNH APPS & LINK USER PHÂN QUYỀN
# ==========================================================
st.set_page_config(page_title="📋 Ứng dụng QLCV", layout="wide")

LINK_USER = "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=745357874"

# ==========================================================
# 🛠️ HÀM HỖ TRỢ: XÁC THỰC VÀ LỌC PHÂN QUYỀN
# ==========================================================
def get_creds():
    try:
        return dict(st.secrets["gcp_service_account"])
    except Exception:
        import os, json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "service_account.json")
        with open(json_path, "r") as f:
            return json.load(f)

def normalize_id(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()
    if x.endswith(".0"):
        x = x[:-2]
    return x

@st.cache_data(ttl=600)
def read_gsheet(link):
  try:
    df = pd.read_csv(link, dtype=str, engine='python', on_bad_lines='skip')
    if df.empty:
      st.warning(f"⚠️ File CSV tải về từ link đang trống (0 dòng): {link}")
      return None
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.select_dtypes(include=["object"]).columns:
      df[col] = df[col].fillna("").astype(str).str.strip()

    return df
  except Exception as e:
    st.error(f"❌ Lỗi đọc Google Sheet từ link `{link}`: {e}")
    return None

def check_login(user_db, user_id, password):
    if user_db is None:
        return False, None, None
    df = user_db.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    id_col = next((c for c in df.columns if c in ["id", "mã", "mssv", "code"]), df.columns[0])
    pass_col = next((c for c in df.columns if "pass" in c), "password")
    change_col = next((c for c in df.columns if "must" in c), "must_change")
    pos_col = next((c for c in df.columns if "pos" in c or "chức" in c), "position")
    fac_col = next((c for c in df.columns if "fac" in c or "khoa" in c or "bộ môn" in c), "faculty")
    sur_col = next((c for c in df.columns if "sur" in c or "ho" in c), "surname")
    name_col = next((c for c in df.columns if c == "name" or "tên" in c), "name")
    
    df[id_col] = df[id_col].apply(normalize_id)
    row = df[df[id_col] == normalize_id(user_id)]

    if row.empty:
        return False, None, None

    real_pass = str(row.iloc[0].get(pass_col, ""))
    must_change = str(row.iloc[0].get(change_col, "0"))
    position = str(row.iloc[0].get(pos_col, "giảng viên"))
    faculty = str(row.iloc[0].get(fac_col, ""))
    surname = str(row.iloc[0].get(sur_col, ""))
    name = str(row.iloc[0].get(name_col, ""))

    user_info = {
        "id": normalize_id(user_id),
        "position": position.strip().lower(),
        "faculty": faculty.strip(),
        "fullname": f"{surname} {name}".strip()
    }

    if str(password) == real_pass:
        return True, must_change, user_info

    return False, None, None

def update_password(user_id, new_pass, sheet_url, must_change_value="0"):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = get_creds()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    all_data = sheet.get_all_values()
    
    found = False
    for i, row_values in enumerate(all_data):
        if i == 0: continue
        if normalize_id(row_values[0]) == normalize_id(user_id):
            sheet.update_cell(i + 1, 5, f"'{new_pass}")
            sheet.update_cell(i + 1, 6, must_change_value)
            found = True
            break
    if not found:
        st.error(f"Không tìm thấy ID {user_id} trên hệ thống để đổi mật khẩu.")
        st.stop()

def reset_all_passwords(new_pass, sheet_url, must_change_value="1"):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = get_creds()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    all_data = sheet.get_all_values()
    
    for i in range(1, len(all_data)):
        sheet.update_cell(i + 1, 5, f"'{new_pass}")
        sheet.update_cell(i + 1, 6, must_change_value)

def filter_dataframe_by_permission(df, user_info):
    if df is None or df.empty:
        return df
    
    position = str(user_info.get("position", "")).strip().lower()
    uid = str(user_info.get("id", "")).strip()
    fac = str(user_info.get("faculty", "")).strip()
    
    df_filtered = df.copy()
    df_filtered.columns = [str(c).strip() for c in df_filtered.columns]
    
    id_col = next((c for c in df_filtered.columns if c.lower() in ["id", "mã", "mssv", "code_gv", "gv", "code"]), None)
    fac_col = next((c for c in df_filtered.columns if any(x in c.lower() for x in ["faculty", "khoa", "bộ môn", "department"])), None)
    
    # 1. Admin & Lãnh đạo khoa: Xem toàn bộ dữ liệu hệ thống
    if "admin" in position or "lãnh đạo khoa" in position:
        return df_filtered.copy()
    
    # 2. Lãnh đạo bộ môn: Xem dữ liệu cá nhân hoặc theo bộ môn/faculty tương ứng
    if "lãnh đạo bộ môn" in position:
        mask = pd.Series(False, index=df_filtered.index)
        if id_col:
            mask |= df_filtered[id_col].astype(str).str.strip() == uid
        if fac_col and fac and fac.lower() != "tất cả":
            mask |= df_filtered[fac_col].astype(str).str.lower().str.contains(fac.lower(), na=False)
        if mask.any():
            return df_filtered[mask].copy()
        
    # 3. Giảng viên: Chỉ xem đúng dữ liệu cá nhân khớp ID
    if id_col:
        return df_filtered[df_filtered[id_col].astype(str).str.strip() == uid].copy()
    
    return df_filtered.head(0)

# ==========================================================
# 🔐 QUẢN LÝ SESSION STATE & ĐĂNG NHẬP BẢO MẬT
# ==========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.must_change = "0"

user_db = read_gsheet(LINK_USER)

if not st.session_state.logged_in:
    st.title("🔐 Đăng nhập hệ thống QLCV")
    with st.form("login_form"):
        uid_input = st.text_input("Mã định danh (ID):").strip()
        pwd_input = st.text_input("Mật khẩu:", type="password")
        submit = st.form_submit_button("Đăng nhập")
        
        if submit:
            ok, must_change, u_info = check_login(user_db, uid_input, pwd_input)
            if ok:
                st.session_state.logged_in = True
                st.session_state.user_info = u_info
                st.session_state.must_change = must_change
                st.rerun()
            else:
                st.error("❌ Sai mã định danh hoặc mật khẩu!")
    st.stop()

if str(st.session_state.must_change) == "1":
    st.warning("⚠️ Bạn phải đổi mật khẩu trước khi tiếp tục sử dụng hệ thống.")
    new_pass = st.text_input("Mật khẩu mới:", type="password")
    if st.button("Xác nhận đổi mật khẩu"):
        if new_pass:
            update_password(st.session_state.user_info["id"], new_pass, LINK_USER, "0")
            st.session_state.must_change = "0"
            st.cache_data.clear()
            st.success("✅ Đổi mật khẩu thành công! Đang tải lại...")
            time.sleep(1.5)
            st.rerun()
        else:
            st.warning("Vui lòng nhập mật khẩu mới.")
    st.stop()

current_user = st.session_state.user_info
pos = current_user["position"]
u_id = current_user["id"]
u_faculty = current_user["faculty"]

st.sidebar.title("👤 Tài khoản")
st.sidebar.success(f"**{current_user['fullname']}**\n\n📌 Chức vụ: **{pos.title()}**\n\n🏫 Đơn vị: **{u_faculty if u_faculty else 'Khoa'}**")
if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.must_change = "0"
    st.rerun()

# Nút làm mới dữ liệu chung trên sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Làm mới bộ nhớ cache", use_container_width=True):
    st.cache_data.clear()
    for k in ["df1", "df2", "detail_dfs", "filtered_detail_dfs"]:
        if k in st.session_state:
            del st.session_state[k]
    st.success("Đã làm mới dữ liệu thành công!")
    st.rerun()
# ==========================================================
# ⚙️ CẤU HÌNH APPS (GỐC)
# ==========================================================
st.title("📋 Ứng dụng Quản lý Công việc")
st.write(
    f"Đây là ứng dụng nhằm tổng hợp thông tin công việc từ giảng dạy, nghiên cứu khoa học và công tác khác. — Phân quyền: **{pos.title()}**"
)

# ==========================================================
# 🛠️ HÀM BỔ TRỢ: CHUYỂN ĐỢT KÊ KHAI SANG NĂM HỌC
# ==========================================================
def quy_doi_nam_hoc(dot_str):
  """Quy đổi Đợt kê khai YYYY-MM sang Năm học YYYY-YYYY.

  Ví dụ: '2024-11' -> '2024-2025', '2025-05' -> '2024-2025'
  """
  if pd.isna(dot_str):
    return "Chưa xác định"

  dot_str = str(dot_str).strip()
  match = re.search(r"(\d{4})[-/.](\d{1,2})", dot_str)

  if match:
    year = int(match.group(1))
    month = int(match.group(2))
    if month >= 8:
      return f"{year}-{year + 1}"
    else:
      return f"{year - 1}-{year}"

  match_year = re.search(r"\b(\d{4})\b", dot_str)
  if match_year:
    y = int(match_year.group(1))
    return f"{y}-{y + 1}"

  return "Khác / Chưa xác định"

# ==========================================================
# 🔗 CÁC LINK DỮ LIỆU ĐÃ CHUẨN HÓA EXPORT CSV
# ==========================================================
links = {
    "df1": (
        "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=2080729380"
    ),
    "df2": (
        "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=0"
    ),
    "GD": (
        "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1431418978"
    ),
    "NCKH": (
        "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1814822744"
    ),
    "Other": (
        "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1443108898"
    ),
}

# ==========================================================
# 🧮 LƯU TRỮ VÀ KHỞI TẠO DỮ LIỆU VÀO SESSION STATE AN TOÀN (CÓ PHÂN QUYỀN)
# ==========================================================
if "df1" not in st.session_state or st.session_state["df1"] is None:
    st.session_state["df1"] = read_gsheet(links["df1"])

if "df2" not in st.session_state or st.session_state["df2"] is None:
    st.session_state["df2"] = read_gsheet(links["df2"])

if "detail_dfs" not in st.session_state or not st.session_state["detail_dfs"]:
    detail_dfs = {}
    for key in ["GD", "NCKH", "Other"]:
      df = read_gsheet(links[key])
      if df is not None:
        detail_dfs[key] = df
    st.session_state["detail_dfs"] = detail_dfs

# Áp dụng phân quyền vào bảng chi tiết
raw_detail_dfs = st.session_state.get("detail_dfs", {})
filtered_detail_dfs = {}
for k, df in raw_detail_dfs.items():
    filtered_detail_dfs[k] = filter_dataframe_by_permission(df, current_user)

st.session_state["filtered_detail_dfs"] = filtered_detail_dfs

# ==========================================================
# 📑 TẠO GIAO DIỆN 3 TAB CHÍNH
# ==========================================================
tab1, tab2, tab3 = st.tabs([
    "🔍 1. Tra cứu nâng cao", 
    "📂 2. Dữ liệu gốc",
    "🛠️ 3. Admin"
])

# ----------------------------------------------------------
# TAB 1: TRA CỨU CÔNG VIỆC NÂNG CAO & THỐNG KÊ (GỐC + NCKH)
# ----------------------------------------------------------
with tab1:
    search_scope = st.radio(
        "📂 Chọn phạm vi / hạng mục cần tìm kiếm:",
        options=[
            "🌐 Tất cả các bảng",
            "📚 GD (Giảng dạy)",
            "🔬 NCKH (Nghiên cứu)",
            "📌 Other (Khác)",
        ],
        horizontal=True,
    )

    keyword_input = (
        st.text_input(
            "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)"
        )
        .strip()
        .lower()
    )
    st.caption("💡 Mẹo: Để xem thông tin toàn khoa theo từng nội dung, gõ GD hoặc NCKH. Để xem theo bộ môn, gõ BM QFRM, BM TCDN, BM ĐTTC")
    
    df1 = st.session_state.get("df1")
    df2 = st.session_state.get("df2")
    detail_dfs = st.session_state.get("filtered_detail_dfs", {})

    found_records = []

    if keyword_input:
        if df1 is None or df1.empty or df2 is None or df2.empty or not detail_dfs:
            st.warning("⚠️ Vui lòng đảm bảo đã tải đủ df1, df2 và các bảng công việc.")
        else:
            raw_keywords = [
                k.strip() for k in re.split(r"[&,]", keyword_input) if k.strip()
            ]

            expanded_keywords = []
            for kw in raw_keywords:
                synonyms = [kw]
                if any(k in kw for k in ["sách tham khảo", "sck", "tltk", "sách"]):
                    for s in ["sách tham khảo", "sck", "tltk", "sách"]:
                        if s not in synonyms:
                            synonyms.append(s)
                elif "bài báo" in kw and "khoa học" not in kw:
                    synonyms.append("bài báo khoa học")
                elif "đề tài" in kw:
                    synonyms.append("đề tài")
              
                expanded_keywords.append(synonyms)

            st.info(
                f"🔍 Đang tìm theo điều kiện BẮT BUỘC CHỨA ĐỒNG THỜI các nhóm từ khóa:"
                f" **{raw_keywords}** trong phạm vi: **{search_scope}**"
            )

            target_search_dict = {}
            if "GD" in search_scope:
                if "GD" in detail_dfs:
                    target_search_dict["GD"] = detail_dfs["GD"]
            elif "NCKH" in search_scope:
                if "NCKH" in detail_dfs:
                    target_search_dict["NCKH"] = detail_dfs["NCKH"]
            elif "Other" in search_scope:
                if "Other" in detail_dfs:
                    target_search_dict["Other"] = detail_dfs["Other"]
            else:
                target_search_dict = detail_dfs

            for name, df in target_search_dict.items():
                if df is None or df.empty:
                    continue

                df_temp = df.copy()
                df_temp.columns = [str(c).strip() for c in df_temp.columns]

                for col in df_temp.columns:
                    df_temp[col] = df_temp[col].fillna("").astype(str)

                all_text_cols = list(df_temp.columns)

                if all_text_cols:
                    mask = pd.Series(True, index=df_temp.index)
                    for syn_list in expanded_keywords:
                        mask_syn = pd.Series(False, index=df_temp.index)
                        for kw in syn_list:
                            mask_kw = pd.Series(False, index=df_temp.index)
                            for c in all_text_cols:
                                mask_kw |= (
                                    df_temp[c].str.lower().str.contains(kw, case=False, na=False)
                                )
                            mask_syn |= mask_kw
                        mask &= mask_syn
                else:
                    mask = pd.Series(False, index=df_temp.index)

                match_df = df_temp[mask].copy()

                if not match_df.empty:
                    if "code" in match_df.columns and "code" in df1.columns:
                        match_df = match_df.merge(
                            df1.drop_duplicates(subset=["code"]), on="code", how="left"
                        )
                    if "category" in match_df.columns and "category" in df2.columns:
                        match_df = match_df.merge(
                            df2.drop_duplicates(subset=["category"]),
                            on="category",
                            how="left",
                        )

                    match_df = match_df.drop_duplicates()
                    match_df["_source_table"] = name
                    found_records.append((name, match_df))

            if found_records:
                st.success(
                    f"✅ Tìm thấy kết quả phù hợp từ {len(found_records)} nhóm bảng"
                )
            else:
                st.warning("❌ Không tìm thấy dữ liệu phù hợp trong phạm vi đã chọn.")
    else:
        st.info("👆 Chọn phạm vi và nhập từ khóa để bắt đầu tìm kiếm và thống kê.")

    # ==========================================================
    # 📊 THỐNG KÊ, TRỪ TRÙNG LẶP VẼ ĐỒ THỊ
    # ==========================================================
    st.divider()

    if found_records:
        valid_dfs = [df for name, df in found_records if not df.empty]
        total_rec_df = (
            pd.concat(valid_dfs, ignore_index=True)
            if valid_dfs
            else pd.DataFrame()
        )
    else:
        total_rec_df = pd.DataFrame()

    # NẾU CHỌN "🌐 TẤT CẢ CÁC BẢNG" -> CHỈ HIỂN THỊ CÁC BẢNG GỐC
    if search_scope == "🌐 Tất cả các bảng":
        if found_records:
            st.markdown("#### 📂 KẾT QUẢ TÌM KIẾM DỮ LIỆU TỪ CÁC BẢNG")
            for name, rec_df in found_records:
                st.markdown(f"##### 📘 Nhóm kết quả từ bảng dữ liệu gốc: **{name}** — {len(rec_df)} dòng")
                with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                    st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("ℹ️ Nhập từ khóa để hiển thị kết quả tìm kiếm.")

    # NẾU CHỌN TỪNG MỤC RIÊNG LẺ (GD, NCKH, OTHER)
    else:
            if not total_rec_df.empty:
                st.markdown("#### 📈 THỐNG KÊ VÀ PHÂN TÍCH DỮ LIỆU")
    
                tiet_col_target = next(
                    (
                        c
                        for c in total_rec_df.columns
                        if any(x in c.lower() for x in ["sỐ tiết kê khai", "tiết", "period"])
                    ),
                    None,
                )
                time_col_target = next(
                    (
                        c
                        for c in total_rec_df.columns
                        if any(x in c.lower() for x in ["đợt kê khai", "năm học", "year"])
                    ),
                    None,
                )
    
                if tiet_col_target and time_col_target:
                    total_rec_df[tiet_col_target] = pd.to_numeric(
                        total_rec_df[tiet_col_target], errors="coerce"
                    ).fillna(0)
                    total_rec_df["Năm học"] = total_rec_df[time_col_target].apply(
                        quy_doi_nam_hoc
                    )
    
                    all_years = sorted(
                        total_rec_df["Năm học"].dropna().unique().tolist(),
                        reverse=True
                    )
                
                    with st.expander("📅 **Bộ lọc Năm học (Bấm để mở/đóng)**", expanded=True):
                        if "selected_years_stat" not in st.session_state:
                            st.session_state["selected_years_stat"] = all_years[:5]
                
                        def set_quick_selection(n):
                            if n == "all":
                                st.session_state["selected_years_stat"] = all_years
                            else:
                                st.session_state["selected_years_stat"] = all_years[:n]
                            
                            for y in all_years:
                                st.session_state[f"chk_year_{y}"] = (y in st.session_state["selected_years_stat"])
                
                        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                        with col_btn1:
                            if st.button("1 năm gần nhất", use_container_width=True):
                                set_quick_selection(1)
                                st.rerun()
                        with col_btn2:
                            if st.button("3 năm gần nhất", use_container_width=True):
                                set_quick_selection(3)
                                st.rerun()
                        with col_btn3:
                            if st.button("5 năm gần nhất", use_container_width=True):
                                set_quick_selection(5)
                                st.rerun()
                        with col_btn4:
                            if st.button("Tất cả (Max)", use_container_width=True):
                                set_quick_selection("all")
                                st.rerun()
                
                        st.markdown("📌 **Hoặc chọn tùy chỉnh các năm cụ thể:**")
                
                        selected_years = []
                        num_cols = 2
                        grid_cols = st.columns(num_cols)
                
                        for i, year in enumerate(all_years):
                            col_idx = i % num_cols
                            chk_key = f"chk_year_{year}"
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = (year in st.session_state["selected_years_stat"])
                
                            with grid_cols[col_idx]:
                                is_checked = st.checkbox(
                                    str(year),
                                    key=chk_key,
                                )
                                if is_checked:
                                    selected_years.append(year)
                
                        st.session_state["selected_years_stat"] = selected_years
    
                    if not selected_years:
                        st.warning("⚠️ Vui lòng tích chọn ít nhất một năm học để hiển thị dữ liệu.")
                    else:
                        total_rec_df = total_rec_df[
                            total_rec_df["Năm học"].isin(selected_years)
                        ]
    
                        if total_rec_df.empty:
                            st.warning("❌ Không có dữ liệu cho năm học đã chọn.")
                        else:
                            is_only_gd = (
                                "_source_table" in total_rec_df.columns
                                and (total_rec_df["_source_table"] == "GD").all()
                            )
    
                            if is_only_gd:
                                # ==========================================
                                # 📚 XỬ LÝ RIÊNG CHO KHỐI GIẢNG DẠY
                                # ==========================================
                                df_clean = total_rec_df.drop_duplicates().copy()
                                df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]
            
                                if "term_x" in df_clean.columns:
                                    df_clean["term"] = df_clean["term_x"]
            
                                code_col_actual = next((c for c in df_clean.columns if "code" in c), None)
                                if code_col_actual:
                                    df_clean["_dot_hoc"] = df_clean[code_col_actual].astype(str).str.upper().apply(
                                        lambda x: "Đợt 1" if "D1" in x or "ĐỢT 1" in x else ("Đợt 2" if "D2" in x or "ĐỢT 2" in x else "Khác")
                                    )
                                else:
                                    df_clean["_dot_hoc"] = "Không rõ"
            
                                time_col_actual = next((c for c in df_clean.columns if any(x in c for x in ["năm học", "year", "đợt", "term"])), None)
                                if "năm học" not in df_clean.columns and time_col_actual:
                                    df_clean["năm học"] = df_clean[time_col_actual].apply(quy_doi_nam_hoc)
                                elif "năm học" not in df_clean.columns:
                                    df_clean["năm học"] = "Chưa xác định"
            
                                tiet_col = next((c for c in df_clean.columns if any(x in c for x in ["tiết", "period"])), list(df_clean.columns)[-1])
                                df_clean[tiet_col] = pd.to_numeric(df_clean[tiet_col], errors="coerce").fillna(0)
            
                                c_class = "class" if "class" in df_clean.columns else df_clean.columns[0]
                                c_subject = "subject" if "subject" in df_clean.columns else ("short_name" if "short_name" in df_clean.columns else df_clean.columns[0])
                                c_program = "program" if "program" in df_clean.columns else None
                                c_knowledge = "knowledge" if "knowledge" in df_clean.columns else None
                                c_session = "session" if "session" in df_clean.columns else None
                                c_location = "location" if "location" in df_clean.columns else None
                                c_term = "term" if "term" in df_clean.columns else None
                                c_faculty = "faculty" if "faculty" in df_clean.columns else None
                                c_note = "note" if "note" in df_clean.columns else None
                                c_dot = "_dot_hoc" 
            
                                name_col = "name" if "name" in df_clean.columns else None
                                surname_col = "surname" if "surname" in df_clean.columns else None
            
                                if name_col:
                                    if surname_col:
                                        df_clean["_full_name"] = df_clean[surname_col].astype(str) + " " + df_clean[name_col].astype(str)
                                    else:
                                        df_clean["_full_name"] = df_clean[name_col].astype(str)
                                else:
                                    df_clean["_full_name"] = "Không rõ"
            
                                # 1. Bảng tổng hợp Giảng dạy theo Năm học
                                df_after = df_clean.groupby("năm học").agg(**{
                                    "Tổng số tiết thực hiện": (tiet_col, "sum"),
                                    "Số lượng lớp": (c_class, "nunique"),
                                    "Số lượng môn học": (c_subject, "nunique")
                                }).reset_index().sort_values("năm học")
                                
                                df_after = df_after.rename(columns={"năm học": "Năm học"})
            
                                st.markdown("##### 🧹 1. Bảng tổng hợp Giảng dạy theo Năm học")
                                tot_lop = df_after["Số lượng lớp"].sum()
                                tot_tiet = df_after["Tổng số tiết thực hiện"].sum()
            
                                df_after_disp = df_after.copy()
                                df_after_disp.loc[len(df_after_disp)] = ["**Tổng cộng**", tot_tiet, tot_lop, float('nan')]
                                df_after_disp = df_after_disp[["Năm học", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]]
                                st.dataframe(df_after_disp, use_container_width=True)
                                
                                # ==========================================
                                # 📚 THỐNG KÊ TỔNG HỢP THEO GIẢNG VIÊN (CÓ TỪNG NĂM + DÒNG TỔNG CỘNG CHO TỪNG GIẢNG VIÊN)
                                # ==========================================
                                st.markdown("##### 👥 Bảng tổng hợp khối lượng giảng dạy theo từng Giảng viên")
    
                                available_years_gd = sorted(df_clean["năm học"].dropna().unique().tolist(), reverse=True)
    
                                selected_years_gv = st.multiselect(
                                    "📅 Chọn năm học hiển thị cho bảng giảng viên (Bỏ trống = Chọn tất cả):",
                                    options=available_years_gd,
                                    default=available_years_gd,
                                    key="multiselect_gv_years"
                                )
    
                                df_gv_filtered = df_clean.copy()
                                if selected_years_gv:
                                    df_gv_filtered = df_gv_filtered[df_gv_filtered["năm học"].isin(selected_years_gv)]
    
                                if not df_gv_filtered.empty:
                                    df_gv_summary = df_gv_filtered.groupby(["_full_name", "năm học"]).agg(
                                        Số_lượng_môn=(c_subject, "nunique"),
                                        Tổng_số_lớp=(c_class, "nunique"),
                                        Tổng_số_tiết=(tiet_col, "sum")
                                    ).reset_index()
    
                                    df_gv_summary = df_gv_summary.rename(columns={
                                        "_full_name": "Giảng viên",
                                        "năm học": "Năm học",
                                        "Số_lượng_môn": "Số lượng môn đã giảng",
                                        "Tổng_số_lớp": "Tổng số lớp",
                                        "Tổng_số_tiết": "Tổng số tiết"
                                    })
    
                                    list_gv_final = []
                                    for gv, group in df_gv_summary.groupby("Giảng viên"):
                                        list_gv_final.append(group)
                                        
                                        if len(selected_years_gv) >= 2 and len(group) > 1:
                                            df_gv_single = df_gv_filtered[df_gv_filtered["_full_name"] == gv]
                                            unique_mon_gv = df_gv_single[c_subject].nunique()
                                            total_lop_gv = df_gv_single[c_class].nunique()
                                            total_tiet_gv = df_gv_single[tiet_col].sum()
    
                                            total_row_gv = pd.DataFrame({
                                                "Giảng viên": [f"**Tổng cộng ({gv})**"],
                                                "Năm học": [""],
                                                "Số lượng môn đã giảng": [unique_mon_gv],
                                                "Tổng số lớp": [total_lop_gv],
                                                "Tổng số tiết": [total_tiet_gv]
                                            })
                                            list_gv_final.append(total_row_gv)
    
                                    df_gv_display = pd.concat(list_gv_final, ignore_index=True)
    
                                    tot_unique_mon_all = df_gv_filtered[c_subject].nunique()
                                    tot_lop_all = df_gv_filtered[c_class].nunique()
                                    tot_tiet_all = df_gv_filtered[tiet_col].sum()
    
                                    total_row_all = pd.DataFrame({
                                        "Giảng viên": ["**Tổng cộng toàn khoa**"],
                                        "Năm học": [""],
                                        "Số lượng môn đã giảng": [tot_unique_mon_all],
                                        "Tổng số lớp": [tot_lop_all],
                                        "Tổng số tiết": [tot_tiet_all]
                                    })
                                    df_gv_display = pd.concat([df_gv_display, total_row_all], ignore_index=True)
    
                                    with st.expander("📅 **(Bấm để mở/đóng xem tổng hợp khối lượng giảng viên)**", expanded=True):
                                        st.dataframe(df_gv_display, use_container_width=True, hide_index=True)
                                else:
                                    st.warning("⚠️ Không có dữ liệu giảng viên cho năm học đã chọn.")
                                
                                # ==========================================
                                # 📚 THỐNG KÊ CHI TIẾT: MỖI GIẢNG VIÊN GIẢNG MÔN NÀO & SỐ LỚP
                                # ==========================================
                                st.markdown("##### 👥 Thống kê chi tiết môn học & số lượng lớp theo từng Giảng viên")
                                
                                df_gv_mon = df_clean.groupby(["_full_name", "năm học", c_subject]).agg(
                                    Số_lượng_lớp=(c_class, "nunique"),
                                    Tổng_số_tiết=(tiet_col, "sum")
                                ).reset_index()
    
                                df_gv_mon = df_gv_mon.rename(columns={
                                    "_full_name": "Giảng viên",
                                    "năm học": "Năm học",
                                    c_subject: "Tên môn học",
                                    "Số_lượng_lớp": "Số lượng lớp",
                                    "Tổng_số_tiết": "Tổng số tiết"
                                })
    
                                df_gv_mon = df_gv_mon.sort_values(["Giảng viên", "Năm học", "Tên môn học"])
    
                                with st.expander("📅 **(Bấm để mở/đóng xem chi tiết giảng viên dạy môn nào)**", expanded=True):
                                    st.dataframe(df_gv_mon, use_container_width=True)
                                
                                # ==========================================
                                # 🔍 2. BẢNG CHI TIẾT GIẢNG DẠY (BỔ SUNG TIÊU CHÍ ĐỢT)
                                # ==========================================
                                st.markdown("##### 🔍 2. Bảng chi tiết Giảng dạy (Tùy chỉnh theo tiêu chí)")
                                with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                                    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
                                    with col_opt1:
                                        opt_year = st.checkbox("Theo Năm học", value=True, key="chk_gd_year")
                                        opt_know = st.checkbox("Theo Khối kiến thức", value=False, key="chk_gd_know")
                                        opt_faculty = st.checkbox("Theo Khoa quản lý", value=False, key="chk_gd_fac")
                                    with col_opt2:
                                        opt_prog = st.checkbox("Theo Chương trình", value=True, key="chk_gd_prog")
                                        opt_sess = st.checkbox("Theo Ca học", value=False, key="chk_gd_sess")
                                        opt_note = st.checkbox("Theo Kiêm chức", value=False, key="chk_gd_note")
                                    with col_opt3:
                                        opt_subj = st.checkbox("Theo Môn học", value=True, key="chk_gd_subj")
                                        opt_loc = st.checkbox("Theo Địa điểm", value=False, key="chk_gd_loc")
                                        opt_dot = st.checkbox("Theo Đợt học", value=False, key="chk_gd_dot") 
                                    with col_opt4:
                                        opt_lecturer = st.checkbox("Theo Giảng viên", value=True, key="chk_gd_lect")
                                        opt_term = st.checkbox("Theo Học kỳ", value=False, key="chk_gd_term")
            
                                    group_detail_keys = []
                                    if opt_year:
                                        group_detail_keys.append("năm học")
                                    if opt_prog and c_program and c_program in df_clean.columns:
                                        group_detail_keys.append(c_program)
                                    if opt_subj:
                                        group_detail_keys.append(c_subject)
                                    if opt_know and c_knowledge and c_knowledge in df_clean.columns:
                                        group_detail_keys.append(c_knowledge)
                                    if opt_sess and c_session and c_session in df_clean.columns:
                                        group_detail_keys.append(c_session)
                                    if opt_loc and c_location and c_location in df_clean.columns:
                                        group_detail_keys.append(c_location)
                                    if opt_term and c_term and c_term in df_clean.columns:
                                        group_detail_keys.append(c_term)
                                    if opt_dot:
                                        group_detail_keys.append(c_dot) 
                                    if opt_faculty and c_faculty and c_faculty in df_clean.columns:
                                        group_detail_keys.append(c_faculty)
                                    if opt_note and c_note and c_note in df_clean.columns:
                                        group_detail_keys.append(c_note)
                                    if opt_lecturer:
                                        group_detail_keys.append("_full_name")
                
                                    if not group_detail_keys:
                                        group_detail_keys = ["năm học"]
                
                                    agg_detail_dict = {
                                        tiet_col: "sum",
                                        c_class: "nunique"
                                    }
                
                                    df_gd_detail = df_clean.groupby(group_detail_keys).agg(agg_detail_dict).reset_index()
                
                                    rename_detail_dict = {
                                        "năm học": "Năm học",
                                        c_subject: "Tên môn học",
                                        tiet_col: "Tổng số tiết",
                                        c_class: "Số lượng lớp",
                                        "_full_name": "Giảng viên"
                                    }
                                    if c_program:
                                        rename_detail_dict[c_program] = "Chương trình"
                                    if c_knowledge:
                                        rename_detail_dict[c_knowledge] = "Khối kiến thức"
                                    if c_session:
                                        rename_detail_dict[c_session] = "Ca học"
                                    if c_location:
                                        rename_detail_dict[c_location] = "Địa điểm"
                                    if c_term:
                                        rename_detail_dict[c_term] = "Học kỳ"
                                    if c_dot:
                                        rename_detail_dict[c_dot] = "Đợt học" 
                                    if c_faculty:
                                        rename_detail_dict[c_faculty] = "Khoa quản lý"
                                    if c_note:
                                        rename_detail_dict[c_note] = "Kiêm chức"
                
                                    df_gd_detail = df_gd_detail.rename(columns=rename_detail_dict)
                
                                    if not df_gd_detail.empty:
                                        total_tiet_val = df_gd_detail["Tổng số tiết"].sum()
                                        total_lop_val = df_gd_detail["Số lượng lớp"].sum()
                                        
                                        total_row = {}
                                        for col_name in df_gd_detail.columns:
                                            if col_name == df_gd_detail.columns[0]:
                                                total_row[col_name] = "**Tổng cộng**"
                                            elif col_name == "Tổng số tiết":
                                                total_row[col_name] = total_tiet_val
                                            elif col_name == "Số lượng lớp":
                                                total_row[col_name] = total_lop_val
                                            else:
                                                total_row[col_name] = ""
                                        
                                        df_gd_detail.loc[len(df_gd_detail)] = total_row
                
                                    st.dataframe(df_gd_detail, use_container_width=True)
            
                                # ==========================================
                                # 📊 3. BIỂU ĐỒ TRỰC QUAN ĐỘNG
                                # ==========================================
                                first_col_name = df_gd_detail.columns[0]
                                df_plot_data = df_gd_detail[df_gd_detail[first_col_name] != "**Tổng cộng**"].copy()
                                 
                                if not df_plot_data.empty:
                                    st.markdown("##### 📊 3. Biểu đồ trực quan Giảng dạy (Tự động vẽ theo các tiêu chí đã chọn)")
                                    
                                    metrics_cols = ["Tổng số tiết", "Số lượng lớp"]
                                    active_criteria_cols = [c for c in df_gd_detail.columns if c not in metrics_cols and c != "**Tổng cộng**"]
            
                                    has_short_name = "short_name" in [c.lower() for c in df_clean.columns]
                                    short_name_col_actual = next((c for c in df_clean.columns if c.lower() == "short_name"), None)
            
                                    has_year_selected = "Năm học" in active_criteria_cols
                                    other_criteria_cols = [c for c in active_criteria_cols if c != "Năm học"]
            
                                    for crit_col in active_criteria_cols:
                                        st.markdown(f"###### 📌 Phân tích theo tiêu chí: **{crit_col}**")
                                         
                                        needs_mapping = False
                                        label_mapping = {}
            
                                        df_crit_filtered = df_plot_data.copy()
                                        if crit_col in ["Tên môn học", "Giảng viên"]:
                                            unique_vals_crit = sorted(df_plot_data[crit_col].astype(str).unique())
                                            selected_vals_crit = st.multiselect(
                                                f"🎯 Lọc {crit_col} hiển thị trên biểu đồ (Bỏ trống = Hiện toàn bộ):",
                                                options=unique_vals_crit,
                                                key=f"filter_crit_{crit_col}"
                                            )
                                            if selected_vals_crit:
                                                df_crit_filtered = df_crit_filtered[df_crit_filtered[crit_col].astype(str).isin(selected_vals_crit)]
            
                                        if df_crit_filtered.empty:
                                            st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho tiêu chí **{crit_col}**.")
                                            continue
            
                                        col_c1, col_c2 = st.columns(2)
            
                                        if crit_col == "Tên môn học" and has_short_name and short_name_col_actual:
                                            df_plot_mapped = df_crit_filtered.copy()
                                            mapping_dict = df_clean[[c_subject, short_name_col_actual]].drop_duplicates().set_index(c_subject)[short_name_col_actual].to_dict()
                                            df_plot_mapped["Trục_X_Vẽ"] = df_plot_mapped[crit_col].map(mapping_dict).fillna(df_plot_mapped[crit_col])
                                            plot_base_col = "Trục_X_Vẽ"
                                        else:
                                            plot_base_col = crit_col
            
                                        df_grouped_crit = df_crit_filtered.groupby(plot_base_col)[metrics_cols].sum().reset_index()
            
                                        unique_labels = df_grouped_crit[plot_base_col].astype(str).tolist()
                                        needs_mapping = any(len(lbl) > 15 for lbl in unique_labels)
            
                                        if needs_mapping:
                                            label_mapping = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels)}
                                            df_grouped_crit["_Short_Label"] = df_grouped_crit[plot_base_col].map(label_mapping)
                                            x_plot_col = "_Short_Label"
                                        else:
                                            x_plot_col = plot_base_col
            
                                        num_bars = len(df_grouped_crit)
                                        dynamic_width = max(6.0, num_bars * 0.4)
                                        val_font_size = 6 if num_bars > 15 else (7 if num_bars > 10 else 8)
            
                                        with col_c1:
                                            fig1, ax1 = plt.subplots(figsize=(dynamic_width, 4.0))
                                            bars1 = ax1.bar(df_grouped_crit[x_plot_col].astype(str), df_grouped_crit["Tổng số tiết"], color="#4C72B0")
                                            for bar in bars1:
                                                h = bar.get_height()
                                                ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=val_font_size, fontweight="bold", rotation=45 if num_bars > 12 else 0)
                                             
                                            ax1.set_xlabel("Ký hiệu" if needs_mapping else crit_col, fontsize=9)
                                            ax1.set_ylabel("Tổng số tiết", fontsize=9)
                                            ax1.set_title(f"Tổng số tiết theo {crit_col}", fontsize=10, fontweight="bold")
                                            ax1.tick_params(axis="x", rotation=45 if num_bars > 8 else 0)
                                            st.pyplot(fig1, bbox_inches="tight")
            
                                        with col_c2:
                                            fig2, ax2 = plt.subplots(figsize=(dynamic_width, 4.0))
                                            bars2 = ax2.bar(df_grouped_crit[x_plot_col].astype(str), df_grouped_crit["Số lượng lớp"], color="#DD8452")
                                            for bar in bars2:
                                                h = bar.get_height()
                                                ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=val_font_size, fontweight="bold", rotation=45 if num_bars > 12 else 0)
                                             
                                            ax2.set_xlabel("Ký hiệu" if needs_mapping else crit_col, fontsize=9)
                                            ax2.set_ylabel("Số lượng lớp", fontsize=9)
                                            ax2.set_title(f"Số lượng lớp theo {crit_col}", fontsize=10, fontweight="bold")
                                            ax2.tick_params(axis="x", rotation=45 if num_bars > 8 else 0)
                                            st.pyplot(fig2, bbox_inches="tight")
            
                                        if needs_mapping:
                                            st.markdown(f"**📝 Chú thích ký hiệu trục hoành cho ({crit_col}):**")
                                            with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                                                note_df = pd.DataFrame(list(label_mapping.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                                st.dataframe(note_df, use_container_width=True, hide_index=True)
            
                                    if has_year_selected and other_criteria_cols:
                                        st.markdown("---")
                                        st.markdown("#### 🌟 3.1 Biểu đồ bóc tách chi tiết so sánh theo Các năm học")
                                         
                                        for other_col in other_criteria_cols:
                                            st.markdown(f"##### 📌 Phân tích tiêu chí **{other_col}** so sánh theo **Năm học**")
                                             
                                            df_other_filtered = df_plot_data.copy()
                                            if other_col in ["Tên môn học", "Giảng viên"]:
                                                unique_vals_other = sorted(df_plot_data[other_col].astype(str).unique())
                                                selected_vals_other = st.multiselect(
                                                    f"🎯 Lọc {other_col} hiển thị trên biểu đồ so sánh (Bỏ trống = Hiện toàn bộ):",
                                                    options=unique_vals_other,
                                                    key=f"filter_other_{other_col}"
                                                )
                                                if selected_vals_other:
                                                    df_other_filtered = df_other_filtered[df_other_filtered[other_col].astype(str).isin(selected_vals_other)]
            
                                            if df_other_filtered.empty:
                                                st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho tiêu chí **{other_col}**.")
                                                continue
            
                                            if other_col == "Tên môn học" and has_short_name and short_name_col_actual:
                                                df_plot_mapped_yr = df_other_filtered.copy()
                                                mapping_dict = df_clean[[c_subject, short_name_col_actual]].drop_duplicates().set_index(c_subject)[short_name_col_actual].to_dict()
                                                df_plot_mapped_yr["Trục_X_Vẽ"] = df_plot_mapped_yr[other_col].map(mapping_dict).fillna(df_plot_mapped_yr[other_col])
                                                plot_yr_base = "Trục_X_Vẽ"
                                            else:
                                                plot_yr_base = other_col
                                             
                                            df_pivot_tiet = df_other_filtered.pivot_table(index=plot_yr_base, columns="Năm học", values="Tổng số tiết", aggfunc="sum").fillna(0)
                                            df_pivot_lop = df_other_filtered.pivot_table(index=plot_yr_base, columns="Năm học", values="Số lượng lớp", aggfunc="sum").fillna(0)
                                             
                                            unique_labels_yr = df_pivot_tiet.index.astype(str).tolist()
                                            needs_mapping_yr = any(len(lbl) > 15 for lbl in unique_labels_yr)
                                             
                                            if needs_mapping_yr:
                                                label_mapping_yr = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels_yr)}
                                                df_pivot_tiet.index = df_pivot_tiet.index.map(label_mapping_yr)
                                                df_pivot_lop.index = df_pivot_lop.index.map(label_mapping_yr)
                                             
                                            num_bars_yr = len(df_pivot_tiet)
                                            dyn_w_yr = max(7.0, num_bars_yr * 0.6)
                                            f_size_yr = 6 if num_bars_yr > 15 else (7 if num_bars_yr > 10 else 8)
                                             
                                            col_y1, col_y2 = st.columns(2)
                                             
                                            with col_y1:
                                                fig_y1, ax_y1 = plt.subplots(figsize=(dyn_w_yr, 4.0))
                                                df_pivot_tiet.plot(kind="bar", ax=ax_y1, width=0.8)
                                                 
                                                for p in ax_y1.patches:
                                                    h = p.get_height()
                                                    if h > 0:
                                                        ax_y1.annotate(f"{int(h):,}",
                                                                   (p.get_x() + p.get_width() / 2., h),
                                                                   ha='center', va='bottom',
                                                                   fontsize=f_size_yr, fontweight='bold',
                                                                   rotation=45 if num_bars_yr > 8 else 0,
                                                                   xytext=(0, 2),
                                                                   textcoords='offset points')
                                                 
                                                ax_y1.set_xlabel("Ký hiệu" if needs_mapping_yr else other_col, fontsize=9)
                                                ax_y1.set_ylabel("Tổng số tiết", fontsize=9)
                                                ax_y1.set_title(f"So sánh Tổng số tiết - {other_col} qua các Năm học", fontsize=10, fontweight="bold")
                                                ax_y1.tick_params(axis="x", rotation=45 if num_bars_yr > 8 else 0)
                                                ax_y1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                                ax_y1.grid(axis="y", linestyle="--", alpha=0.5)
                                                st.pyplot(fig_y1, bbox_inches="tight")
                                             
                                            with col_y2:
                                                fig_y2, ax_y2 = plt.subplots(figsize=(dyn_w_yr, 4.0))
                                                df_pivot_lop.plot(kind="bar", ax=ax_y2, width=0.8, colormap="tab20")
                                                 
                                                # Sửa lại thành ax_y2.patches ở đây:
                                                for p in ax_y2.patches:
                                                    h = p.get_height()
                                                    if h > 0:
                                                        ax_y2.annotate(f"{int(h):,}",
                                                                     (p.get_x() + p.get_width() / 2., h),
                                                                     ha='center', va='bottom',
                                                                     fontsize=f_size_yr, fontweight='bold',
                                                                     rotation=45 if num_bars_yr > 8 else 0,
                                                                     xytext=(0, 2),
                                                                     textcoords='offset points')
                                                 
                                                ax_y2.set_xlabel("Ký hiệu" if needs_mapping_yr else other_col, fontsize=9)
                                                ax_y2.set_ylabel("Số lượng lớp", fontsize=9)
                                                ax_y2.set_title(f"So sánh Số lượng lớp - {other_col} qua các Năm học", fontsize=10, fontweight="bold")
                                                ax_y2.tick_params(axis="x", rotation=45 if num_bars_yr > 8 else 0)
                                                ax_y2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                                ax_y2.grid(axis="y", linestyle="--", alpha=0.5)
                                                st.pyplot(fig_y2, bbox_inches="tight")
            
                                            if needs_mapping_yr:
                                                st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({other_col}):**")
                                                with st.expander(f"📅 **(Bấm để xem chú thích chi tiết)**", expanded=False):
                                                    note_df_yr = pd.DataFrame(list(label_mapping_yr.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                                    st.dataframe(note_df_yr, use_container_width=True, hide_index=True)
                        
                            else:
                                # ==========================================
                                # 🔬 XỬ LÝ CHUNG CHO KHỐI NCKH (KHỬ TRÙNG LẶP TF-IDF)
                                # ==========================================
                                df_temp_detail = total_rec_df.copy()
                                df_temp_detail.columns = [str(c).strip() for c in df_temp_detail.columns]
    
                                tap_chi_col = next(
                                    (
                                        c for c in df_temp_detail.columns
                                        if any(
                                            x in c.lower()
                                            for x in [
                                                "tạp chí",
                                                "tap chi",
                                                "hội thảo",
                                                "hoi thao",
                                                "sách",
                                                "sach",
                                            ]
                                        )
                                    ),
                                    None,
                                )
    
                                name_prod_col = next((c for c in df_temp_detail.columns if c.lower() in ["tên sản phẩm"]), None)
                                id_col_check = next((c for c in df_temp_detail.columns if c.lower() in ["mã sản phẩm", "code"]), None)
                                name_col_check = next((c for c in df_temp_detail.columns if c.lower() == "name"), None)
                                surname_col_check = next((c for c in df_temp_detail.columns if c.lower() == "surname"), None)
                                role_col_check = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["vai trò", "role"])), None)
    
                                phan_loai_col = next((c for c in df_temp_detail.columns if "phân loại cấp 1" in c.lower()), None)
                                phan_loai_2 = next((c for c in df_temp_detail.columns if "phân loại cấp 2" in c.lower()), None)
                                phan_loai_3 = next((c for c in df_temp_detail.columns if "phân loại cấp 3" in c.lower()), None)
                                col_isbn_init = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["isbn", "issn"])), None)
    
                                if name_prod_col and not df_temp_detail.empty:
                                    df_temp_detail["_clean_prod_name"] = df_temp_detail[name_prod_col].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
                                else:
                                    df_temp_detail["_clean_prod_name"] = "sản phẩm chung"
    
                                if id_col_check and id_col_check in df_temp_detail.columns:
                                    df_temp_detail["_clean_id"] = df_temp_detail[id_col_check].astype(str).str.lower().str.replace(r"\s+", "", regex=True).str.strip()
                                    df_temp_detail["_clean_key"] = df_temp_detail["_clean_prod_name"] + " | " + df_temp_detail["_clean_id"]
                                else:
                                    df_temp_detail["_clean_key"] = df_temp_detail["_clean_prod_name"]
    
                                if name_col_check:
                                    if surname_col_check:
                                        df_temp_detail["_full_name"] = df_temp_detail[surname_col_check].astype(str) + " " + df_temp_detail[name_col_check].astype(str)
                                    else:
                                        df_temp_detail["_full_name"] = df_temp_detail[name_col_check].astype(str)
                                else:
                                    df_temp_detail["_full_name"] = "Không rõ"
    
                                unique_keys_detail = df_temp_detail["_clean_key"].unique()
                                key_to_canonical = {}
    
                                if len(unique_keys_detail) > 1:
                                    vectorizer_d = TfidfVectorizer().fit(unique_keys_detail)
                                    tfidf_matrix_d = vectorizer_d.transform(unique_keys_detail)
                                    similarity_matrix_d = cosine_similarity(tfidf_matrix_d, tfidf_matrix_d)
    
                                    threshold_d = 0.85
                                    visited_d = set()
    
                                    for i in range(len(unique_keys_detail)):
                                        if i in visited_d:
                                            continue
                                        canonical_key = unique_keys_detail[i]
                                        similar_idx_d = np.where(similarity_matrix_d[i] >= threshold_d)[0]
                                        for idx in similar_idx_d:
                                            visited_d.add(idx)
                                            key_to_canonical[unique_keys_detail[idx]] = canonical_key
                                else:
                                    for k_item in unique_keys_detail:
                                        key_to_canonical[k_item] = k_item
    
                                df_temp_detail["Sản phẩm chuẩn hóa"] = df_temp_detail["_clean_key"].map(key_to_canonical)
    
                                loai_hd_col = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["loại hoạt động", "loại"])), None)
                                cap_do_col = next((c for c in df_temp_detail.columns if c.lower() == "cấp độ" or "cấp độ" in c.lower()), None)
    
                                group_keys_final = ["Năm học", "Sản phẩm chuẩn hóa"]
                                if phan_loai_col:
                                    group_keys_final.insert(0, phan_loai_col)
                                if loai_hd_col and loai_hd_col not in group_keys_final:
                                    group_keys_final.insert(1, loai_hd_col)
    
                                agg_rules_detail = {
                                    tiet_col_target: "first",
                                    "_full_name": lambda x: ", ".join(x.dropna().unique()),
                                }
                                if cap_do_col and cap_do_col in df_temp_detail.columns:
                                    agg_rules_detail[cap_do_col] = "first"
                                if name_prod_col and name_prod_col in df_temp_detail.columns:
                                    agg_rules_detail[name_prod_col] = lambda x: " / ".join(x.dropna().unique())
                                if id_col_check and id_col_check in df_temp_detail.columns:
                                    agg_rules_detail[id_col_check] = lambda x: " / ".join(x.dropna().unique())
                                if role_col_check:
                                    agg_rules_detail[role_col_check] = lambda x: " & ".join(x.dropna().unique())
    
                                if tap_chi_col and tap_chi_col in df_temp_detail.columns:
                                    agg_rules_detail[tap_chi_col] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                                if phan_loai_2 and phan_loai_2 in df_temp_detail.columns:
                                    agg_rules_detail[phan_loai_2] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                                if phan_loai_3 and phan_loai_3 in df_temp_detail.columns:
                                    agg_rules_detail[phan_loai_3] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                                if col_isbn_init and col_isbn_init in df_temp_detail.columns:
                                    agg_rules_detail[col_isbn_init] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
    
                                df_clean_unified = df_temp_detail.groupby(group_keys_final, dropna=False).agg(agg_rules_detail).reset_index()
    
                                # ==========================================
                                # 🔍 1. BẢNG CHI TIẾT NCKH TÙY CHỈNH (BẢNG 2)
                                # ==========================================
                                st.markdown("##### 🔍 1. Bảng chi tiết NCKH tùy chỉnh theo tiêu chí")
    
                                cols_lower_all = {str(c).strip().lower(): c for c in df_clean_unified.columns}
                                col_ma_sp = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["mã sản phẩm", "ma san pham", "code"])), None)
                                
                                col_tap_chi = next(
                                    (
                                        c for c in df_clean_unified.columns
                                        if any(
                                            x in c.lower()
                                            for x in [
                                                "tạp chí", "tap chi", "hội thảo", "hoi thao", "sách", "sach",
                                            ]
                                        )
                                    ),
                                    None,
                                )
                                col_phan_loai_2 = next((cols_lower_all[c] for c in cols_lower_all if "phân loại cấp 2" in c), None)
                                col_phan_loai_3 = next((cols_lower_all[c] for c in cols_lower_all if "phân loại cấp 3" in c), None)
                                col_isbn = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["isbn", "issn"])), None)
    
                                with st.expander("⚙️ **Chọn tiêu chí gom nhóm Bảng chi tiết (Bấm để mở/đóng)**", expanded=True):
                                    col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
                                    
                                    with col_c1:
                                        opt_y = st.checkbox("Năm học", value=True, key="chk_nckh_year")
                                        opt_ma = st.checkbox("Mã sản phẩm", value=False, key="chk_nckh_ma")
                                    with col_c2:
                                        opt_loai = st.checkbox("Loại HĐ", value=True, key="chk_nckh_loai")
                                        opt_issn = st.checkbox("Số ISBN / Số ISSN", value=False, key="chk_nckh_issn")
                                    with col_c3:
                                        opt_cap = st.checkbox("Cấp độ", value=True, key="chk_nckh_cap")
                                        opt_role = st.checkbox("Vai trò", value=False, key="chk_nckh_role")
                                    with col_c4:
                                        opt_pl1 = st.checkbox("PL Cấp 1", value=True, key="chk_nckh_pl1")
                                        opt_prod = st.checkbox("Tên sản phẩm", value=False, key="chk_nckh_prod")
                                    with col_c5:
                                        opt_pl2 = st.checkbox("PL Cấp 2", value=False, key="chk_nckh_pl2")
                                        opt_pl3 = st.checkbox("PL Cấp 3", value=False, key="chk_nckh_pl3")
                                    opt_tap = st.checkbox("Tên Tạp chí / Hội thảo, Sách", value=False, key="chk_nckh_tap")
    
                                    group_detail_dynamic = []
                                    if opt_y:
                                        group_detail_dynamic.append("Năm học")
                                    if opt_loai and loai_hd_col and loai_hd_col in df_clean_unified.columns:
                                        group_detail_dynamic.append(loai_hd_col)
                                    if opt_cap and cap_do_col and cap_do_col in df_clean_unified.columns:
                                        group_detail_dynamic.append(cap_do_col)
                                    if opt_pl1 and phan_loai_col and phan_loai_col in df_clean_unified.columns:
                                        group_detail_dynamic.append(phan_loai_col)
                                    if opt_pl2 and col_phan_loai_2 and col_phan_loai_2 in df_clean_unified.columns:
                                        group_detail_dynamic.append(col_phan_loai_2)
                                    if opt_pl3 and col_phan_loai_3 and col_phan_loai_3 in df_clean_unified.columns:
                                        group_detail_dynamic.append(col_phan_loai_3)
                                    if opt_role and role_col_check and role_col_check in df_clean_unified.columns:
                                        group_detail_dynamic.append(role_col_check)
                                    if opt_prod and name_prod_col and name_prod_col in df_clean_unified.columns:
                                        group_detail_dynamic.append(name_prod_col)
                                    if opt_ma and col_ma_sp and col_ma_sp in df_clean_unified.columns:
                                        group_detail_dynamic.append(col_ma_sp)
                                    if opt_tap and col_tap_chi and col_tap_chi in df_clean_unified.columns:
                                        group_detail_dynamic.append(col_tap_chi)
                                    if opt_issn and col_isbn and col_isbn in df_clean_unified.columns:
                                        group_detail_dynamic.append(col_isbn)
    
                                    if not group_detail_dynamic:
                                        group_detail_dynamic = ["Năm học"]
    
                                    agg_dyn_dict = {
                                        tiet_col_target: ["sum", "count"],
                                        "_full_name": lambda x: ", ".join(x.dropna().unique()),
                                    }
                                    if name_prod_col and name_prod_col in df_clean_unified.columns:
                                        agg_dyn_dict[name_prod_col] = lambda x: " / ".join(x.dropna().unique())
                                    if id_col_check and id_col_check in df_clean_unified.columns:
                                        agg_dyn_dict[id_col_check] = lambda x: " / ".join(x.dropna().unique())
                                    if role_col_check and role_col_check not in group_detail_dynamic:
                                        agg_dyn_dict[role_col_check] = lambda x: " & ".join(x.dropna().unique())
    
                                    if tap_chi_col and tap_chi_col in df_clean_unified.columns:
                                        agg_dyn_dict[tap_chi_col] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                                    if col_phan_loai_2 and col_phan_loai_2 in df_clean_unified.columns:
                                        agg_dyn_dict[col_phan_loai_2] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                                    if col_phan_loai_3 and col_phan_loai_3 in df_clean_unified.columns:
                                        agg_dyn_dict[col_phan_loai_3] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                                    if col_isbn and col_isbn in df_clean_unified.columns:
                                        agg_dyn_dict[col_isbn] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
    
                                    group_detail_dynamic = list(dict.fromkeys(group_detail_dynamic))
    
                                    safe_agg_dyn_dict = {
                                        k: v for k, v in agg_dyn_dict.items() 
                                        if k not in group_detail_dynamic
                                    }
    
                                    df_nckh_detail = df_clean_unified.groupby(group_detail_dynamic, dropna=False).agg(safe_agg_dyn_dict).reset_index()
    
                                    df_nckh_detail.columns = [
                                        col[0] if col[1] == "" else f"{col[0]}_{col[1]}" 
                                        for col in df_nckh_detail.columns
                                    ]
    
                                    rename_nckh_dict = {
                                        f"{tiet_col_target}_sum": "Tổng số tiết",
                                        f"{tiet_col_target}_count": "Số lượng",
                                        "_full_name": "Danh sách thành viên"
                                    }
                                    if role_col_check:
                                        rename_nckh_dict[role_col_check] = "Các vai trò"
    
                                    df_nckh_detail = df_nckh_detail.rename(columns=rename_nckh_dict)
                                    
                                    for col_drop in ["_clean_prod_name", "_clean_id", "_clean_key", "Sản phẩm chuẩn hóa", "_source_table"]:
                                        if col_drop in df_nckh_detail.columns:
                                            df_nckh_detail = df_nckh_detail.drop(columns=[col_drop])
    
                                    front_cols = [c for c in group_detail_dynamic if c in df_nckh_detail.columns]
                                    middle_cols = [c for c in ["Số lượng", "Tổng số tiết"] if c in df_nckh_detail.columns]
                                    end_cols = [c for c in df_nckh_detail.columns if c not in front_cols + middle_cols]
                                    
                                    cols_order = front_cols + middle_cols + end_cols
                                    df_nckh_detail = df_nckh_detail[cols_order]
    
                                    if not df_nckh_detail.empty:
                                        tot_sl_nckh = df_nckh_detail["Số lượng"].sum() if "Số lượng" in df_nckh_detail.columns else 0
                                        tot_tiet_nckh = df_nckh_detail["Tổng số tiết"].sum() if "Tổng số tiết" in df_nckh_detail.columns else 0
                                        
                                        total_row_nckh = {}
                                        for col_name in df_nckh_detail.columns:
                                            if col_name == df_nckh_detail.columns[0]:
                                                total_row_nckh[col_name] = "**Tổng cộng**"
                                            elif col_name == "Số lượng":
                                                total_row_nckh[col_name] = tot_sl_nckh
                                            elif col_name == "Tổng số tiết":
                                                total_row_nckh[col_name] = tot_tiet_nckh
                                            else:
                                                total_row_nckh[col_name] = ""
                                        df_nckh_detail.loc[len(df_nckh_detail)] = total_row_nckh
    
                                    st.dataframe(df_nckh_detail, use_container_width=True)
                                # ==========================================
                                # 📈 ĐẶT ĐOẠN CODE THỐNG KÊ TỔ HỢP Ở NGAY DƯỚI ĐÂY
                                # ==========================================
                                st.markdown("##### 📈 2. Thống kê số lượng & tổng số tiết")
    
                                stat_options_mapping = [
                                (opt_loai, loai_hd_col, "Loại HĐ"),
                                (opt_cap, cap_do_col, "Cấp độ"),
                                (opt_pl1, phan_loai_col, "PL Cấp 1"),
                                (opt_pl2, col_phan_loai_2, "PL Cấp 2"),
                                (opt_pl3, col_phan_loai_3, "PL Cấp 3"),
                                (opt_role, role_col_check, "Vai trò"),
                                (opt_prod, name_prod_col, "Tên sản phẩm"),
                                (opt_ma, col_ma_sp, "Mã sản phẩm"),
                                (opt_tap, col_tap_chi, "Tên Tạp chí / Hội thảo, Sách"),
                                (opt_issn, col_isbn, "Số ISBN / ISSN"),
                                ]
        
                                active_stat_cols = []
                                active_stat_names = []
                                for is_checked, col_name, display_name in stat_options_mapping:
                                    if is_checked and col_name and col_name in df_clean_unified.columns:
                                        active_stat_cols.append(col_name)
                                        active_stat_names.append(display_name)
        
                                group_stat_keys = []
                                if opt_y and "Năm học" in df_clean_unified.columns:
                                    group_stat_keys.append("Năm học")
        
                                if (active_stat_cols or group_stat_keys) and not df_clean_unified.empty:
                                    df_stat_work = df_clean_unified.copy()
                                    
                                    for c in active_stat_cols:
                                        df_stat_work[c] = df_stat_work[c].fillna("Không xác định").astype(str).str.strip()
        
                                    if len(active_stat_cols) > 1:
                                        df_stat_work["_Tổ_hợp_tiêu_chí"] = df_stat_work[active_stat_cols].agg(' + '.join, axis=1)
                                    elif len(active_stat_cols) == 1:
                                        df_stat_work["_Tổ_hợp_tiêu_chí"] = df_stat_work[active_stat_cols[0]]
                                    else:
                                        df_stat_work["_Tổ_hợp_tiêu_chí"] = "Tổng hợp chung"
        
                                    group_stat_keys.append("_Tổ_hợp_tiêu_chí")
        
                                    df_grouped_stat = df_stat_work.groupby(group_stat_keys, dropna=False).agg(
                                        Số_lượng=(tiet_col_target, "count"),
                                        Tổng_số_tiết=(tiet_col_target, "sum"),
                                        Thành_viên=("_full_name", lambda x: ", ".join(x.dropna().unique()))
                                    ).reset_index()
        
                                    rename_col_dict = {
                                        "_Tổ_hợp_tiêu_chí": "Tổ hợp tiêu chí (" + " + ".join(active_stat_names) + ")" if active_stat_names else "Nội dung",
                                        "Số_lượng": "Số lượng",
                                        "Tổng_số_tiết": "Số tiết"
                                    }
                                    df_grouped_stat = df_grouped_stat.rename(columns=rename_col_dict)
        
                                    # Tạo bảng có chèn dòng tổng cộng theo từng năm và tổng cộng chung
                                    final_rows = []
                                    has_year_col = "Năm học" in df_grouped_stat.columns
        
                                    if has_year_col:
                                        years = df_grouped_stat["Năm học"].unique()
                                        for yr in sorted(years):
                                            df_yr = df_grouped_stat[df_grouped_stat["Năm học"] == yr]
                                            for _, row in df_yr.iterrows():
                                                final_rows.append(row.to_dict())
                                            
                                            # Thêm dòng tổng cộng theo từng năm
                                            sum_sl_yr = df_yr["Số lượng"].sum()
                                            sum_tiết_yr = df_yr["Số tiết"].sum()
                                            total_yr_row = {col: "" for col in df_grouped_stat.columns}
                                            total_yr_row["Năm học"] = f"**Tổng cộng ({yr})**"
                                            total_yr_row["Số lượng"] = sum_sl_yr
                                            total_yr_row["Số tiết"] = sum_tiết_yr
                                            final_rows.append(total_yr_row)
                                    else:
                                        for _, row in df_grouped_stat.iterrows():
                                            final_rows.append(row.to_dict())
        
                                    # Thêm dòng tổng cộng toàn bộ cuối cùng
                                    total_all_row = {col: "" for col in df_grouped_stat.columns}
                                    first_col = df_grouped_stat.columns[0]
                                    total_all_row[first_col] = "**Tổng cộng chung**" if not has_year_col else "**Tổng cộng tất cả**"
                                    total_all_row["Số lượng"] = df_grouped_stat["Số lượng"].sum()
                                    total_all_row["Số tiết"] = df_grouped_stat["Số tiết"].sum()
                                    final_rows.append(total_all_row)
        
                                    df_final_stat_display = pd.DataFrame(final_rows)
        
                                    with st.expander("⚙️ **Chọn tiêu chí gom nhóm Bảng chi tiết (Bấm để mở/đóng)**", expanded=True):
                                        st.info(f"💡 Đang thống kê theo các tiêu chí đã chọn: **{' + '.join(active_stat_names)}**")
                                        st.dataframe(df_final_stat_display, use_container_width=True, hide_index=True)
                                else:
                                    st.warning("⚠️ Vui lòng chọn ít nhất một tiêu chí gom nhóm ở phần cấu hình phía trên.")
                             
                                # ==========================================
                                # 📊 3.1. BIỂU ĐỒ TRỰC QUAN THEO NĂM HỌC
                                # ==========================================
                                if 'df_grouped_stat' in locals() and not df_grouped_stat.empty and "Năm học" in df_grouped_stat.columns and opt_y:
                                    st.markdown("##### 📊 3.1. Phân tích tổng quan theo năm học")
                                    
                                    # Gom nhóm theo Năm học để vẽ biểu đồ tổng hợp toàn bộ các tiêu chí qua các năm
                                    df_plot_year = df_grouped_stat.copy()
                                    df_plot_year = df_plot_year[~df_plot_year["Năm học"].astype(str).str.contains("Tổng cộng", na=False)]
                                    
                                    df_year_summary = df_plot_year.groupby("Năm học")[["Số lượng", "Số tiết"]].sum().reset_index()
                                    
                                    if not df_year_summary.empty:
                                        col_y1, col_y2 = st.columns(2)
                                        
                                        # --- BIỂU ĐỒ SỐ LƯỢNG THEO NĂM ---
                                        with col_y1:
                                            fig_y1, ax_y1 = plt.subplots(figsize=(6, 3.5))
                                            bars1 = ax_y1.bar(df_year_summary["Năm học"].astype(str), df_year_summary["Số lượng"], color="cornflowerblue", width=0.6)
                                            
                                            for bar in bars1:
                                                h = bar.get_height()
                                                if h > 0:
                                                    ax_y1.annotate(f"{int(h):,}",
                                                                 (bar.get_x() + bar.get_width() / 2., h),
                                                                 ha='center', va='bottom', fontsize=8, fontweight='bold',
                                                                 xytext=(0, 2), textcoords='offset points')
                                                    
                                            ax_y1.set_xlabel("Năm học", fontsize=9)
                                            ax_y1.set_ylabel("Tổng số lượng", fontsize=9)
                                            ax_y1.set_title("Tổng số lượng sản phẩm theo Năm học", fontsize=10, fontweight="bold")
                                            ax_y1.grid(axis="y", linestyle="--", alpha=0.5)
                                            st.pyplot(fig_y1, bbox_inches="tight")
                                        
                                        # --- BIỂU ĐỒ SỐ TIẾT THEO NĂM ---
                                        with col_y2:
                                            fig_y2, ax_y2 = plt.subplots(figsize=(6, 3.5))
                                            bars2 = ax_y2.bar(df_year_summary["Năm học"].astype(str), df_year_summary["Số tiết"], color="lightcoral", width=0.6)
                                            
                                            for bar in bars2:
                                                h = bar.get_height()
                                                if h > 0:
                                                    ax_y2.annotate(f"{int(h):,}",
                                                                 (bar.get_x() + bar.get_width() / 2., h),
                                                                 ha='center', va='bottom', fontsize=8, fontweight='bold',
                                                                 xytext=(0, 2), textcoords='offset points')
                                                    
                                            ax_y2.set_xlabel("Năm học", fontsize=9)
                                            ax_y2.set_ylabel("Tổng số tiết", fontsize=9)
                                            ax_y2.set_title("Tổng số tiết thực hiện theo Năm học", fontsize=10, fontweight="bold")
                                            ax_y2.grid(axis="y", linestyle="--", alpha=0.5)
                                            st.pyplot(fig_y2, bbox_inches="tight")
                                            
                                if 'df_grouped_stat' in locals() and not df_grouped_stat.empty:
                                    st.markdown("##### 📊 3.2. Phân tích tổng quan theo tiêu chí")
                                    # Lọc bỏ các dòng tổng cộng để đưa vào vẽ biểu đồ
                                    df_plot_nckh = df_grouped_stat.copy()
                                    if "Năm học" in df_plot_nckh.columns:
                                        df_plot_nckh = df_plot_nckh[~df_plot_nckh["Năm học"].astype(str).str.contains("Tổng cộng", na=False)]
                                    
                                    # Xác định tên cột chứa nội dung tổ hợp tiêu chí
                                    col_tinh_chi_name = [c for c in df_plot_nckh.columns if c not in ["Năm học", "Số lượng", "Số tiết", "Thành_viên"]][0]
                                    display_name_chart = "Tổ hợp tiêu chí" if not active_stat_names else " + ".join(active_stat_names)
        
                                    if not df_plot_nckh.empty:
                                      
                                        # Tạo danh sách cho phép lọc trên biểu đồ theo cột nội dung chính
                                        unique_vals_nckh = sorted(df_plot_nckh[col_tinh_chi_name].astype(str).unique())
                                        selected_vals_nckh = st.multiselect(
                                            f"🎯 Lọc {display_name_chart} hiển thị trên biểu đồ (Bỏ trống = Hiện toàn bộ):",
                                            options=unique_vals_nckh,
                                            key=f"filter_nckh_dynamic_stat"
                                        )
                                        
                                        if selected_vals_nckh:
                                            df_plot_nckh = df_plot_nckh[df_plot_nckh[col_tinh_chi_name].astype(str).isin(selected_vals_nckh)]
                                        
                                        if df_plot_nckh.empty:
                                            st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho biểu đồ.")
                                        else:
                                            col_chart1, col_chart2 = st.columns(2)
                                            
                                            # Kiểm tra xem có tách nhóm theo Năm học hay không
                                            has_year_nckh = "Năm học" in df_plot_nckh.columns and opt_y
                                            
                                            if has_year_nckh:
                                                df_pivot_qty = df_plot_nckh.pivot_table(index=col_tinh_chi_name, columns="Năm học", values="Số lượng", aggfunc="sum").fillna(0)
                                                df_pivot_tiet = df_plot_nckh.pivot_table(index=col_tinh_chi_name, columns="Năm học", values="Số tiết", aggfunc="sum").fillna(0)
                                                is_grouped_years = True
                                            else:
                                                df_pivot_qty = df_plot_nckh.groupby(col_tinh_chi_name)[["Số lượng"]].sum()
                                                df_pivot_tiet = df_plot_nckh.groupby(col_tinh_chi_name)[["Số tiết"]].sum()
                                                is_grouped_years = False
                                            
                                            # Xử lý rút gọn nhãn nếu tên quá dài (logic y chang bản cũ)
                                            unique_labels = df_pivot_qty.index.astype(str).tolist()
                                            needs_mapping = any(len(lbl) > 15 for lbl in unique_labels)
                                            
                                            label_mapping = {}
                                            if needs_mapping:
                                                label_mapping = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels)}
                                                df_pivot_qty.index = df_pivot_qty.index.map(label_mapping)
                                                df_pivot_tiet.index = df_pivot_tiet.index.map(label_mapping)
                                            
                                            num_bars_nckh = len(df_pivot_qty)
                                            dynamic_width_nckh = max(7.0, num_bars_nckh * 0.6)
                                            val_font_size_nckh = 6 if num_bars_nckh > 15 else (7 if num_bars_nckh > 10 else 8)
                                            
                                            # --- BIỂU ĐỒ 1: SỐ LƯỢNG ---
                                            with col_chart1:
                                                fig1, ax1 = plt.subplots(figsize=(dynamic_width_nckh, 4.0))
                                                df_pivot_qty.plot(kind="bar", stacked=False, ax=ax1, width=0.8, colormap="tab20")
                                                
                                                for p in ax1.patches:
                                                    h = p.get_height()
                                                    if h > 0:
                                                        ax1.annotate(f"{int(h):,}",
                                                                     (p.get_x() + p.get_width() / 2., h),
                                                                     ha='center', va='bottom',
                                                                     fontsize=val_font_size_nckh, fontweight='bold',
                                                                     rotation=45 if num_bars_nckh > 8 else 0,
                                                                     xytext=(0, 2), textcoords='offset points')
                                                
                                                ax1.set_xlabel("Ký hiệu" if needs_mapping else display_name_chart, fontsize=9)
                                                ax1.set_ylabel("Số lượng sản phẩm", fontsize=9)
                                                ax1.set_title(f"So sánh Số lượng theo {display_name_chart}", fontsize=10, fontweight="bold")
                                                ax1.tick_params(axis="x", rotation=45 if num_bars_nckh > 8 else 0)
                                                if is_grouped_years:
                                                    ax1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                                ax1.grid(axis="y", linestyle="--", alpha=0.5)
                                                st.pyplot(fig1, bbox_inches="tight")
                                            
                                            # --- BIỂU ĐỒ 2: SỐ TIẾT ---
                                            with col_chart2:
                                                fig2, ax2 = plt.subplots(figsize=(dynamic_width_nckh, 4.0))
                                                df_pivot_tiet.plot(kind="bar", stacked=False, ax=ax2, width=0.8, colormap="Accent")
                                                
                                                for p in ax2.patches:
                                                    h = p.get_height()
                                                    if h > 0:
                                                        ax2.annotate(f"{int(h):,}",
                                                                     (p.get_x() + p.get_width() / 2., h),
                                                                     ha='center', va='bottom',
                                                                     fontsize=val_font_size_nckh, fontweight='bold',
                                                                     rotation=45 if num_bars_nckh > 2 else 0,
                                                                     xytext=(0, 2), textcoords='offset points')
                                                
                                                ax2.set_xlabel("Ký hiệu" if needs_mapping else display_name_chart, fontsize=9)
                                                ax2.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
                                                ax2.set_title(f"So sánh Số tiết theo {display_name_chart}", fontsize=10, fontweight="bold")
                                                ax2.tick_params(axis="x", rotation=45 if num_bars_nckh > 8 else 0)
                                                if is_grouped_years:
                                                    ax2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                                ax2.grid(axis="y", linestyle="--", alpha=0.5)
                                                st.pyplot(fig2, bbox_inches="tight")
                                            
                                            # --- BẢNG CHÚ THÍCH NẾU TÊN QUÁ DÀI ---
                                            if needs_mapping:
                                                st.markdown(f"**📝 Chú thích ký hiệu trục hoành cho ({display_name_chart}):**")
                                                with st.expander(f"📅 **(Bấm để mở/đóng)**", expanded=True):
                                                    note_df = pd.DataFrame(list(label_mapping.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                                    st.dataframe(note_df, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Không tìm thấy cột 'SỐ TIẾT KÊ KHAI' hoặc cột thời gian phù hợp để vẽ biểu đồ.")
            else:
                st.info("ℹ️ Nhập từ khóa để hiển thị kết quả phân tích.")

# ----------------------------------------------------------
# TAB 2: DỮ LIỆU GỐC THEO PHÂN QUYỀN
# ----------------------------------------------------------
with tab2:
    st.markdown("#### 📂 Dữ liệu mô tả (df1 & df2)")
    col1, col2 = st.columns(2)
    
    with col1:
      if "df1" not in st.session_state or st.session_state["df1"] is None:
        st.session_state["df1"] = read_gsheet(links["df1"])
      if st.session_state["df1"] is not None:
        st.success("✅ Đã tải df1 (Year - Term - Code)!")
        with st.expander(f"📅 **(Bấm để mở/đóng)**", expanded=True):
            st.dataframe(st.session_state["df1"], height=400, use_container_width=True)
    
    with col2:
      if "df2" not in st.session_state or st.session_state["df2"] is None:
        st.session_state["df2"] = read_gsheet(links["df2"])
      if st.session_state["df2"] is not None:
        st.success("✅ Đã tải df2 (Category - Description)!")
        with st.expander(f"📅 **(Bấm để mở/đóng)**", expanded=True):
            st.dataframe(st.session_state["df2"], height=400, use_container_width=True)
    
    st.divider()
    
    st.markdown("#### 📘 Dữ liệu các nhóm công việc GD, NCKH, Other (Đã phân quyền)")
    detail_dfs = st.session_state.get("filtered_detail_dfs", {})

    if detail_dfs:
      selected_group_view = st.radio(
          "Chọn nhóm công việc muốn xem:",
          options=["GD (Giảng dạy)", "NCKH (Nghiên cứu)", "Other (Khác)"],
          horizontal=True,
          key="radio_group_view"
      )
      key_mapping_view = {
          "GD (Giảng dạy)": "GD",
          "NCKH (Nghiên cứu)": "NCKH",
          "Other (Khác)": "Other",
      }
      chosen_key_view = key_mapping_view[selected_group_view]
      if chosen_key_view in detail_dfs:
        st.success(f"✅ Đang hiển thị dữ liệu nhóm: {selected_group_view}")
        with st.expander(f"📅 **(Bấm để mở/đóng)**", expanded=True):
            st.dataframe(detail_dfs[chosen_key_view], height=450, use_container_width=True)
      else:
        st.warning(f"⚠️ Nhóm {selected_group_view} hiện chưa có dữ liệu hoặc bạn không có quyền xem.")
    else:
      st.error("❌ Không thể tải dữ liệu chi tiết từ Google Sheets.")

# ----------------------------------------------------------
# TAB 3: QUẢN TRỊ ADMIN (QUẢN LÝ MẬT KHẨU TỰ ĐỘNG THEO ID)
# ----------------------------------------------------------
with tab3:
    st.markdown("#### 🛠️ Quản lý Hệ thống")
    
    # Kiểm tra phân quyền Admin thực tế
    if "admin" not in pos:
        st.error("⛔ Bạn không có quyền truy cập trang quản trị hệ thống này. Khu vực này chỉ dành cho tài khoản có quyền Admin.")
    else:
        st.success("✅ Đã xác thực quyền Quản trị viên hệ thống.")
        
        # Chọn chế độ thao tác quản lý mật khẩu dạng Radio
        reset_mode = st.radio(
            "📂 Chọn chế độ thao tác quản lý:",
            options=["🔑 Reset mật khẩu từng người", "🔄 Reset toàn bộ mật khẩu"],
            horizontal=True
        )
        
        st.divider()
        
        user_table_df = read_gsheet(LINK_USER)
        
        if reset_mode == "🔑 Reset mật khẩu từng người":
            st.markdown("##### 👤 Reset mật khẩu cá nhân về mặc định (Trùng với ID)")
            if user_table_df is not None and not user_table_df.empty:
                user_table_df.columns = [str(c).strip().lower() for c in user_table_df.columns]
                id_c = next((c for c in user_table_df.columns if c in ["id", "mã"]), user_table_df.columns[0])
                sur_c = next((c for c in user_table_df.columns if "sur" in c or "ho" in c), None)
                name_c = next((c for c in user_table_df.columns if c == "name" or "tên" in c), None)
                
                if sur_c and name_c:
                    user_table_df["_display_name"] = user_table_df[id_c].astype(str) + " — " + user_table_df[sur_c].astype(str) + " " + user_table_df[name_c].astype(str)
                else:
                    user_table_df["_display_name"] = user_table_df[id_c].astype(str)
                
                chosen_user_label = st.selectbox("Chọn tài khoản cần reset mật khẩu:", user_table_df["_display_name"].tolist())
                selected_row = user_table_df[user_table_df["_display_name"] == chosen_user_label]
                
                if not selected_row.empty:
                    target_id = str(selected_row.iloc[0][id_c]).strip()
                    st.info(f"📌 Tài khoản đang chọn: **{chosen_user_label}** (Mật khẩu mặc định sau khi reset sẽ trùng với ID: **{target_id}**)")
                    
                    if st.button("🔄 Thực hiện Reset Mật khẩu về ID", use_container_width=True):
                        # Tự động gán password mới chính là target_id và bật cờ bắt buộc đổi mật khẩu (must_change = "1")
                        update_password(target_id, target_id, LINK_USER, "1")
                        st.cache_data.clear()
                        st.success(f"✅ Đã reset mật khẩu thành công cho ID: **{target_id}**. Mật khẩu mới hiện là: `{target_id}`")
            else:
                st.error("❌ Không tải được danh sách từ bảng User.")
                
        else:
            st.markdown("##### 🔄 Reset mật khẩu toàn bộ hệ thống về mặc định (Trùng với ID của từng người)")
            st.warning("⚠️ Thao tác này sẽ đặt lại mật khẩu của **tất cả** các tài khoản trên hệ thống về trùng với mã ID tương ứng của từng người và bắt buộc họ phải đổi lại mật khẩu trong lần đăng nhập tới.")
            
            if st.button("🚨 Xác nhận Reset toàn bộ hệ thống về mặc định", use_container_width=True):
                user_user_db = read_gsheet(LINK_USER)
                if user_user_db is not None and not user_user_db.empty:
                    user_user_db.columns = [str(c).strip().lower() for c in user_user_db.columns]
                    
                    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    creds_dict = get_creds()
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                    client = gspread.authorize(creds)
                    sheet = client.open_by_url(LINK_USER).sheet1
                    all_rows = sheet.get_all_values()
                    
                    # Duyệt qua từng dòng dữ liệu và cập nhật password = ID, must_change = 1
                    for idx, row in enumerate(all_rows):
                        if idx == 0: continue # Bỏ qua dòng tiêu đề
                        row_id = str(row[0]).strip()
                        if row_id:
                            sheet.update_cell(idx + 1, 5, f"'{row_id}") # Cột 5: password
                            sheet.update_cell(idx + 1, 6, "1")        # Cột 6: must_change = 1
                            
                    st.cache_data.clear()
                    st.success("✅ Đã reset thành công mật khẩu cho toàn bộ hệ thống về trùng với ID tương ứng!")
                else:
                    st.error("❌ Không thể đọc dữ liệu để thực hiện reset toàn bộ.")
                    
        st.divider()
        st.markdown("##### 📋 Danh sách tài khoản người dùng hiện tại (Google Sheet Link User)")
        st.caption(f"Đường dẫn liên kết trực tiếp: `{LINK_USER}`")
        if user_table_df is not None and not user_table_df.empty:
            with st.expander("📅 **(Bấm để mở/đóng xem bảng thông tin User)**", expanded=True):
                st.dataframe(user_table_df, use_container_width=True)
        else:
            st.warning("⚠️ Không thể tải dữ liệu bảng User.")
