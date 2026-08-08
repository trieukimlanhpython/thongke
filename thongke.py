#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 20:50:24 2025
📋 Ứng dụng Quản lý Công việc (QLCV) tích hợp Quản lý Sinh viên (QLSV) - Đầy đủ tính năng
streamlit run "/Users/trieukimlanh/Library/CloudStorage/GoogleDrive-trieukimlanh@gmail.com/My Drive/Từ OneDrive/Spyder/app_QLCV/thongke_ver9.py"
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
# ⚙️ CẤU HÌNH APPS & LINK USER PHÂN QUYỀN (BẮT BUỘC ĐẦU TIÊN)
# ==========================================================
st.set_page_config(page_title="📋 Ứng dụng QLCV & QLSV", layout="wide")

LINK_USER = "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=745357874"
LINK_SV = "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=529089260"

# ==========================================================
# 🛠️ HÀM HỖ TRỢ: XÁC THỰC VÀ LỌC PHÂN QUYỀN CHUẨN XÁC
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
# ==========================================================
# 🛠️ HÀM HỖ TRỢ: XÁC THỰC VÀ LỌC PHÂN QUYỀN CHUẨN XÁC
# ==========================================================
def filter_dataframe_by_permission(df, user_info, is_sv_data=False):
    if df is None or df.empty:
        return df
    
    position = str(user_info.get("position", "")).strip().lower()
    uid = str(user_info.get("id", "")).strip()
    fac = str(user_info.get("faculty", "")).strip()
    fullname = str(user_info.get("fullname", "")).strip().lower()
    
    df_filtered = df.copy()
    df_filtered.columns = [str(c).strip() for c in df_filtered.columns]
    
    # 1. Admin hoặc Lãnh đạo khoa: Xem toàn bộ dữ liệu hệ thống
    if "admin" in position or "lãnh đạo khoa" in position or "quản lý khoa" in position:
        return df_filtered.copy()
    
    # 2. Lãnh đạo bộ môn: Lọc theo bộ môn tương ứng hoặc ID cá nhân
    if "lãnh đạo bộ môn" in position:
        fac_col = next((c for c in df_filtered.columns if any(x in c.lower() for x in ["faculty", "khoa", "bộ môn", "department", "đơn vị"])), None)
        id_col = next((c for c in df_filtered.columns if any(x in c.lower() for x in ["id", "mã", "code", "gv", "mssv"])), None)
        
        mask = pd.Series(False, index=df_filtered.index)
        if id_col:
            mask |= df_filtered[id_col].astype(str).str.strip() == uid
        if fac_col and fac and fac.lower() != "tất cả":
            mask |= df_filtered[fac_col].astype(str).str.lower().str.contains(fac.lower(), na=False)
        if mask.any():
            return df_filtered[mask].copy()
        return df_filtered.head(0)
        
    # 3. Giảng viên: Chỉ xem dữ liệu gắn với Mã ID hoặc Tên của chính giảng viên đó
    mask = pd.Series(False, index=df_filtered.index)
    potential_id_cols = [c for c in df_filtered.columns if any(x in c.lower() for x in ["id", "mã", "code", "gv", "mssv", "cố vấn", "giảng viên", "phụ trách"])]
    
    for col in potential_id_cols:
        col_vals = df_filtered[col].astype(str).str.strip().str.lower()
        mask |= (col_vals == uid.lower())
        if fullname and len(fullname) > 4:
            mask |= col_vals.str.contains(re.escape(fullname), na=False)
            
    if not mask.any():
        for col in df_filtered.select_dtypes(include=["object"]).columns:
            mask |= (df_filtered[col].astype(str).str.strip().str.lower() == uid.lower())
            
    if mask.any():
        return df_filtered[mask].copy()
        
    # Trường hợp Giảng viên không khớp dòng nào thì trả về khung trống bảo mật
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

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Làm mới bộ nhớ cache", use_container_width=True):
    st.cache_data.clear()
    for k in ["df1", "df2", "detail_dfs", "filtered_detail_dfs", "df_sv", "filtered_df_sv"]:
        if k in st.session_state:
            del st.session_state[k]
    st.success("Đã làm mới dữ liệu thành công!")
    st.rerun()

st.title("📋 Ứng dụng Quản lý Công việc")
st.write(
    f"Ứng dụng tổng hợp thông tin công việc và dữ liệu sinh viên toàn khoa. — Phân quyền: **{pos.title()}**"
)

def quy_doi_nam_hoc(dot_str):
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

def quy_doi_nam_hoc_sv(date_str):
    if not date_str or date_str.lower() in ["nan", "nat", ""]:
        return "Chưa xác định"
    try:
        dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            return "Chưa xác định"
        y = dt.year
        m = dt.month
        d = dt.day
        if (m > 9) or (m == 9 and d >= 5):
            return f"{y}-{y + 1}"
        else:
            return f"{y - 1}-{y}"
    except Exception:
        return "Chưa xác định"

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

if "df_sv" not in st.session_state or st.session_state["df_sv"] is None:
    st.session_state["df_sv"] = read_gsheet(LINK_SV)

raw_df_sv = st.session_state.get("df_sv")
if raw_df_sv is not None and not raw_df_sv.empty:
    df_sv_clean = raw_df_sv.copy()
    df_sv_clean.columns = [str(c).strip() for c in df_sv_clean.columns]
    for col in df_sv_clean.columns:
        df_sv_clean[col] = df_sv_clean[col].fillna("").astype(str).str.strip()
    # Áp dụng hàm phân quyền cho sinh viên với cờ is_sv_data=True
    filtered_df_sv = filter_dataframe_by_permission(df_sv_clean, current_user, is_sv_data=True)
else:
    filtered_df_sv = pd.DataFrame()

raw_detail_dfs = st.session_state.get("detail_dfs", {})
filtered_detail_dfs = {}
for k, df in raw_detail_dfs.items():
    filtered_detail_dfs[k] = filter_dataframe_by_permission(df, current_user, is_sv_data=False)

st.session_state["filtered_detail_dfs"] = filtered_detail_dfs

# ==========================================================
# 🔐 KIỂM TRA PHÂN QUYỀN TRUY CẬP CÁC TAB CHÍNH
# ==========================================================
is_admin = "admin" in pos

# Phân quyền hiển thị tab:
# - Admin: Xem đủ 4 tab (Dashboard, Tra cứu nâng cao, Dữ liệu gốc, Admin)
# - Các tài khoản khác (Lãnh đạo khoa, Lãnh đạo bộ môn, Giảng viên): Chỉ được xem 2 tab đầu tiên, ẩn hoàn toàn Dữ liệu gốc và Admin.
if is_admin:
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 1. Dashboard",
        "🔍 2. Tra cứu nâng cao", 
        "📂 3. Dữ liệu gốc",
        "🛠️ 4. Admin"
    ])
else:
    tab1, tab2 = st.tabs([
        "📊 1. Dashboard",
        "🔍 2. Tra cứu nâng cao"
    ])
    tab3 = None
    tab4 = None

# ----------------------------------------------------------
# TAB 1: DASHBOARD (TÍCH HỢP RADIO QUẢN LÝ KHOA & QUẢN LÝ SV)
# ----------------------------------------------------------
with tab1:
    dashboard_mode = st.radio(
        "🗂️ Chọn phân hệ Dashboard muốn xem:",
        options=["🏢 Quản lý khoa", "🎓 Quản lý SV"],
        horizontal=True,
        key="radio_main_dashboard_mode"
    )
  
    # ==========================================================
    # PHÂN HỆ 1: QUẢN LÝ KHOA
    # ==========================================================
    if dashboard_mode == "🏢 Quản lý khoa":
        st.markdown("#### 📊 BÁO CÁO TỔNG HỢP VÀ THỐNG KÊ CHI TIẾT")
        st.caption("💡 Xuất báo cáo chi tiết theo cấp độ: Toàn khoa, Theo bộ môn, và Theo từng giảng viên.")

        if "admin" in pos or "lãnh đạo khoa" in pos or "quản lý khoa" in pos:
            report_level = st.radio(
                "🎯 Chọn cấp độ báo cáo:",
                options=[
                    "(1) Toàn khoa", 
                    "(2) Từng bộ môn", 
                    "(3) Từng giảng viên"
                ],
                horizontal=False,
                key="radio_qlcv_report_level"
            )
        elif "lãnh đạo bộ môn" in pos:
            # 🔓 Cho phép lãnh đạo bộ môn xem được cả cấp độ Bộ môn và cấp độ Giảng viên (bao gồm bản thân họ)
            report_level = st.radio(
                "🎯 Chọn cấp độ báo cáo:",
                options=[
                    "(2) Từng bộ môn", 
                    "(3) Từng giảng viên"
                ],
                horizontal=False,
                key="radio_qlcv_report_level"
            )
            st.info(f"📌 Đơn vị phụ trách: **{u_faculty}** | Bạn có thể xem tổng hợp bộ môn hoặc xem giảng viên trong bộ môn ở mục (3).")
        else:
            report_level = "(3) Từng giảng viên"
            st.info(f"📌 Chế độ hiển thị cá nhân cho Giảng viên: **{current_user['fullname']}**")
        
        user_df_raw = read_gsheet(LINK_USER)
        if user_df_raw is not None and not user_df_raw.empty:
            user_df_raw.columns = [str(c).strip().lower() for c in user_df_raw.columns]
            u_id_col = next((c for c in user_df_raw.columns if c in ["id", "mã", "mssv", "code"]), user_df_raw.columns[0])
            u_sur_col = next((c for c in user_df_raw.columns if "sur" in c or "ho" in c), "surname")
            u_name_col = next((c for c in user_df_raw.columns if c == "name" or "tên" in c), "name")
            u_fac_col = next((c for c in user_df_raw.columns if "fac" in c or "khoa" in c or "bộ môn" in c), "faculty")
    
            user_df_raw[u_id_col] = user_df_raw[u_id_col].apply(normalize_id)
            user_df_raw["normalized_faculty"] = user_df_raw[u_fac_col].astype(str).str.strip()
            user_df_raw.loc[user_df_raw["normalized_faculty"].str.lower().isin(["khoa nh", "ngân hàng", "nh"]), "normalized_faculty"] = "BM QFRM"
            user_df_raw["_fullname"] = user_df_raw[u_sur_col].astype(str) + " " + user_df_raw[u_name_col].astype(str)
        else:
            user_df_raw = pd.DataFrame()
    
        df1_tab4 = st.session_state.get("df1", read_gsheet(links["df1"]))
        df_gd_raw = read_gsheet(links["GD"])
        df_nckh_raw = read_gsheet(links["NCKH"])
        df_other_raw = read_gsheet(links["Other"])
    
        def mapping_year_from_df1(df_detail, df_desc, mảng_type="GD"):
            if df_detail is None or df_detail.empty:
                return pd.DataFrame()
            df_temp = df_detail.copy()
            df_temp.columns = [str(c).strip() for c in df_temp.columns]
            
            if df_desc is not None and not df_desc.empty:
                df_desc_clean = df_desc.copy()
                df_desc_clean.columns = [str(c).strip() for c in df_desc_clean.columns]
                
                col_desc_code = next((c for c in df_desc_clean.columns if c.lower() in ["code", "mã"]), None)
                col_desc_term = next((c for c in df_desc_clean.columns if c.lower() in ["term", "học kỳ"]), None)
                col_desc_year = next((c for c in df_desc_clean.columns if c.lower() in ["year", "năm học", "đợt kê khai"]), None)
                col_desc_dot = next((c for c in df_desc_clean.columns if c.lower() in ["đợt kê khai", "đợt"]), None)
    
                if mảng_type == "GD":
                    c_code_det = next((c for c in df_temp.columns if c.lower() in ["code", "mã"]), None)
                    c_term_det = next((c for c in df_temp.columns if c.lower() in ["term", "học kỳ"]), None)
                    
                    if col_desc_code and col_desc_year:
                        if c_code_det and c_term_det and col_desc_code and col_desc_term:
                            df_temp = df_temp.merge(
                                df_desc_clean[[col_desc_code, col_desc_term, col_desc_year]].drop_duplicates(),
                                left_on=[c_code_det, c_term_det],
                                right_on=[col_desc_code, col_desc_term],
                                how="left"
                            )
                        else:
                            df_temp = df_temp.merge(
                                df_desc_clean[[col_desc_code, col_desc_year]].drop_duplicates(),
                                left_on=c_code_det,
                                right_on=col_desc_code,
                                how="left"
                            )
                else:
                    c_dot_det = next((c for c in df_temp.columns if any(x in c.lower() for x in ["đợt kê khai", "đợt", "code"])), None)
                    if c_dot_det and col_desc_dot and col_desc_year:
                        df_temp = df_temp.merge(
                            df_desc_clean[[col_desc_dot, col_desc_year]].drop_duplicates(),
                            left_on=c_dot_det,
                            right_on=col_desc_dot,
                            how="left"
                        )
    
                matched_year_col = next((c for c in df_temp.columns if c.lower() in ["year", "năm học_y", "năm học_x"] or c == col_desc_year), None)
                if matched_year_col:
                    df_temp["Năm học"] = df_temp[matched_year_col].apply(quy_doi_nam_hoc)
                else:
                    time_col_fallback = next((c for c in df_temp.columns if any(x in c.lower() for x in ["đợt", "năm học", "year", "code"])), None)
                    df_temp["Năm học"] = df_temp[time_col_fallback].apply(quy_doi_nam_hoc)
            else:
                df_temp["Năm học"] = "Chưa xác định"
                
            return df_temp
    
        df_gd_full = mapping_year_from_df1(df_gd_raw, df1_tab4, mảng_type="GD")
        df_nckh_full = mapping_year_from_df1(df_nckh_raw, df1_tab4, mảng_type="NCKH")
        df_other_full = mapping_year_from_df1(df_other_raw, df1_tab4, mảng_type="Other")
    
        report_category = st.radio(
            "📌 Chọn mảng báo cáo muốn xuất:",
            options=[
                "📚 1. Báo cáo Giảng dạy (GD)", 
                "🔬 2. Báo cáo Nghiên cứu khoa học (NCKH)", 
                "📌 3. Báo cáo Công tác khác (Other)"
            ],
            horizontal=False,
            key="radio_qlcv_report_category"
        )
    
        all_available_years = []
        for dset in [df_gd_full, df_nckh_full, df_other_full]:
            if dset is not None and "Năm học" in dset.columns:
                all_available_years.extend(dset["Năm học"].dropna().unique().tolist())
        all_available_years = sorted(list(set(all_available_years)), reverse=True)
        default_years = all_available_years[:3]
    
        selected_report_years = st.multiselect(
            "📅 Lọc theo năm học, có thể chọn nhiều năm học (Bỏ trống = Lấy tất cả các năm):",
            options=all_available_years,
            default=default_years,
            key="multiselect_qlcv_years"
        )
    
        def apply_year_filter(df):
            if df is None or df.empty or not selected_report_years:
                return df
            if "Năm học" in df.columns:
                return df[df["Năm học"].isin(selected_report_years)]
            return df
    
        # ==========================================
        # 1. BÁO CÁO MẢNG GIẢNG DẠY (GD)
        # ==========================================
        if "Báo cáo Giảng dạy (GD)" in report_category:
            st.markdown("### 📚 CHI TIẾT BÁO CÁO GIẢNG DẠY")
            if df_gd_full is None or df_gd_full.empty:
                st.warning("⚠️ Không có dữ liệu giảng dạy.")
            else:
                df_gd_filtered = apply_year_filter(df_gd_full)
                df_gd_filtered.columns = [str(c).strip().lower() for c in df_gd_filtered.columns]
    
                c_sub = next((c for c in df_gd_filtered.columns if "subject" in c or "môn" in c), df_gd_filtered.columns[0])
                c_cls = next((c for c in df_gd_filtered.columns if "class" in c or "lớp" in c), df_gd_filtered.columns[0])
                c_per = next((c for c in df_gd_filtered.columns if any(x in c for x in ["tiết", "period", "sỐ tiết kê khai"])), df_gd_filtered.columns[-1])
                c_term = next((c for c in df_gd_filtered.columns if "term" in c or "học kỳ" in c), None)
                c_id_gd = next((c for c in df_gd_filtered.columns if c in ["id", "mã", "code_gv", "gv", "code"]), None)
                c_fac_gd = next((c for c in df_gd_filtered.columns if any(x in c for x in ["faculty", "khoa", "bộ môn"])), None)
                c_note_gd = next((c for c in df_gd_filtered.columns if any(x in c for x in ["note", "kiêm chức", "ghi chú"])), None)
                c_sur_gd = next((c for c in df_gd_filtered.columns if any(x in c for x in ["surname", "ho"])), None)
                c_name_gd = next((c for c in df_gd_filtered.columns if c == "name" or "tên" in c), None)
    
                df_gd_filtered[c_per] = pd.to_numeric(df_gd_filtered[c_per], errors="coerce").fillna(0)
                if c_id_gd:
                    df_gd_filtered[c_id_gd] = df_gd_filtered[c_id_gd].apply(normalize_id)
    
                if c_fac_gd:
                    df_gd_filtered["_norm_fac"] = df_gd_filtered[c_fac_gd].astype(str).str.strip()
                    df_gd_filtered.loc[df_gd_filtered["_norm_fac"].str.lower().isin(["khoa nh", "ngân hàng", "nh"]), "_norm_fac"] = "BM QFRM"
                else:
                    df_gd_filtered["_norm_fac"] = "Chưa xác định"
                    
                if report_level == "(1) Toàn khoa":
                    st.markdown("#### 🌐 Báo cáo tổng hợp Toàn khoa (Giảng dạy)")
                    
                    main_bms = ["BM TCDN", "BM ĐTTC", "BM QFRM"]
                    if not user_df_raw.empty:
                        df_main_bms = user_df_raw[user_df_raw["normalized_faculty"].isin(main_bms)]
                        total_gv_toankhoa = len(df_main_bms)
                        
                        df_all_fac = user_df_raw.copy()
                        df_all_fac["_is_khoa"] = df_all_fac["normalized_faculty"].str.lower().apply(lambda x: "khoa" in x)
                        df_filtered_fac = df_all_fac[~df_all_fac["_is_khoa"]]
                        
                        dt_gv_bm = df_filtered_fac.groupby("normalized_faculty").agg(
                            Số_lượng_giảng_viên=("normalized_faculty", "count"),
                            Danh_sách_giảng_viên=("_fullname", lambda x: ", ".join(x.dropna().unique()))
                        ).reset_index()
                        dt_gv_bm.columns = ["Bộ môn / Đơn vị", "Số lượng giảng viên", "Danh sách giảng viên"]
                        
                        st.markdown(f"- **Tổng số giảng viên toàn khoa (3 Bộ môn chính):** {total_gv_toankhoa} giảng viên")
                        st.markdown("**Chi tiết số giảng viên và danh sách theo các bộ môn/đơn vị:**")
                        st.dataframe(dt_gv_bm, use_container_width=True)
    
                    group_cols_khoa = [c_sub]
                    if c_term: group_cols_khoa.append(c_term)
                    if "năm học" in df_gd_filtered.columns: group_cols_khoa.append("năm học")
    
                    df_sum_khoa = df_gd_filtered.groupby(group_cols_khoa).agg(
                        Tổng_số_lớp=(c_cls, "nunique"),
                        Tổng_số_tiết=(c_per, "sum")
                    ).reset_index()
    
                    if not df_gd_filtered.empty:
                        df_sub_stat = df_gd_filtered.groupby([c_sub, "năm học"]).agg(
                            Tổng_lớp=(c_cls, "nunique"),
                            Tổng_tiết=(c_per, "sum")
                        ).reset_index()
                        if not df_sub_stat.empty:
                            m_max_lop = df_sub_stat.loc[df_sub_stat["Tổng_lớp"].idxmax()]
                            m_min_lop = df_sub_stat.loc[df_sub_stat["Tổng_lớp"].idxmin()]
    
                            st.markdown("##### 📈 Thống kê nổi bật về Môn học")
                            st.caption("Số liệu thay đổi khi người dùng chọn theo năm học")
                            st.markdown(
                                f"""
                                * 🥇 **Môn học có nhiều lớp nhất:** {m_max_lop[c_sub]} ({m_max_lop['Tổng_lớp']} lớp — Năm học: {m_max_lop['năm học']})
                                * 📉 **Môn học có ít lớp nhất:** {m_min_lop[c_sub]} ({m_min_lop['Tổng_lớp']} lớp — Năm học: {m_min_lop['năm học']})
                                """
                            )
                            
                    if c_id_gd and not df_gd_filtered.empty:
                        df_gv_work = df_gd_filtered.copy()
                        if c_note_gd:
                            mask_moi_ngoai = df_gv_work[c_note_gd].astype(str).str.lower().str.contains("kiêm chức|khác bộ môn", na=False)
                            df_gv_work = df_gv_work[~mask_moi_ngoai]
    
                        if not user_df_raw.empty:
                            valid_bms = ["BM TCDN", "BM ĐTTC", "BM QFRM"]
                            valid_gv_ids = user_df_raw[user_df_raw["normalized_faculty"].isin(valid_bms)][u_id_col].apply(normalize_id).tolist()
                            df_gv_work = df_gv_work[df_gv_work[c_id_gd].isin(valid_gv_ids)]
    
                        df_gv_stat = df_gv_work.groupby([c_id_gd, "năm học"]).agg(
                            Tổng_lớp=(c_cls, "nunique"),
                            Tổng_tiết=(c_per, "sum")
                        ).reset_index()
                        df_gv_stat = df_gv_stat[df_gv_stat[c_id_gd] != ""]
                        
                        if not df_gv_stat.empty:
                            max_lop = df_gv_stat.loc[df_gv_stat["Tổng_lớp"].idxmax()]
                            min_lop = df_gv_stat.loc[df_gv_stat["Tổng_lớp"].idxmin()]
    
                            def get_gv_name_by_id(gvid):
                                if not user_df_raw.empty:
                                    matched = user_df_raw[user_df_raw[u_id_col].apply(normalize_id) == str(gvid)]
                                    if not matched.empty:
                                        return matched.iloc[0].get("_fullname", gvid)
                                return gvid
                            
                            st.markdown("##### 📈 Thống kê nổi bật về Giảng viên (Thuộc 3 Bộ môn, không tính mời ngoài)")
                            st.caption("Số liệu thay đổi khi người dùng chọn theo năm học")
                            st.markdown(
                                f"""
                                * 🥇 **Giảng viên dạy nhiều lớp nhất:** ID `{max_lop[c_id_gd]}` - {get_gv_name_by_id(max_lop[c_id_gd])} ({max_lop['Tổng_lớp']} lớp — Năm học: {max_lop['năm học']})
                                * 📉 **Giảng viên dạy ít lớp nhất:** ID `{min_lop[c_id_gd]}` - {get_gv_name_by_id(min_lop[c_id_gd])} ({min_lop['Tổng_lớp']} lớp — Năm học: {min_lop['năm học']})
                                """
                            )
                
                    df_clean = df_gd_filtered.copy()
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
    
                    df_after = df_clean.groupby("năm học").agg(**{
                        "Tổng số tiết thực hiện": (tiet_col, "sum"),
                        "Số lượng lớp": (c_class, "nunique"),
                        "Số lượng môn học": (c_subject, "nunique")
                    }).reset_index().sort_values("năm học")
                    
                    df_after = df_after.rename(columns={"năm học": "Năm học"})
    
                    # ==========================================
                    # 🧹 1. BẢNG TỔNG HỢP GIẢNG DẠY THEO NĂM HỌC (Tích hợp radio chọn Bộ môn)
                    # ==========================================
                    st.markdown("##### 🧹 1. Bảng tổng hợp giảng dạy theo Năm học")
                    st.caption("Để xem chi tiết theo học kỳ, sử dụng bảng 3 tuỳ chỉnh theo tiêu chí")
                    
                    # Thêm radio chọn nhanh bộ môn để lọc bảng 1
                    selected_table1_bm = st.radio(
                        "📌 Lọc bảng tổng hợp năm học theo Bộ môn:",
                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                        horizontal=True,
                        key="radio_filter_table1_bm_gd"
                    )

                    df_table1_work = df_clean.copy()
                    
                    # Lọc dữ liệu theo bộ môn được chọn qua radio
                    if selected_table1_bm != "Tất cả bộ môn" and not df_table1_work.empty:
                        df_table1_work = df_table1_work[df_table1_work["_norm_fac"].astype(str).str.lower().str.contains(selected_table1_bm.lower(), na=False)]

                    if not df_table1_work.empty:
                        df_after = df_table1_work.groupby("năm học").agg(**{
                            "Tổng số tiết thực hiện": (tiet_col, "sum"),
                            "Số lượng lớp": (c_class, "nunique"),
                            "Số lượng môn học": (c_subject, "nunique")
                        }).reset_index().sort_values("năm học")
                        
                        df_after = df_after.rename(columns={"năm học": "Năm học"})

                        tot_lop = df_after["Số lượng lớp"].sum()
                        tot_tiet = df_after["Tổng số tiết thực hiện"].sum()

                        df_after_disp = df_after.copy()
                        df_after_disp.loc[len(df_after_disp)] = [f"**Tổng cộng ({selected_table1_bm})**", tot_tiet, tot_lop, float('nan')]
                        df_after_disp = df_after_disp[["Năm học", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]]
                        
                        st.dataframe(df_after_disp, use_container_width=True)
                    else:
                        st.warning(f"⚠️ Không có dữ liệu giảng dạy thuộc bộ môn **{selected_table1_bm}** trong các năm học đã chọn.")
                    
                    # ==========================================
                    # 👤 2. BẢNG TỔNG HỢP GIẢNG DẠY THEO TỪNG GIẢNG VIÊN (Tích hợp radio chọn Bộ môn)
                    # ==========================================
                    st.markdown("##### 👤 2. Bảng tổng hợp giảng dạy theo từng Giảng viên")
                    st.caption("Để biết GV dạy bao nhiêu môn, cụ thể tên môn đã giảng")
                    
                    # Thêm radio chọn nhanh bộ môn để lọc bảng số 2
                    selected_gv_table2_bm = st.radio(
                        "📌 Lọc bảng giảng viên theo Bộ môn:",
                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                        horizontal=True,
                        key="radio_filter_gv_table2_bm_gd"
                    )

                    if not df_gd_filtered.empty:
                        def get_gv_identity(row):
                            uid = str(row.get(c_id_gd, "")).strip() if c_id_gd else ""
                            sur = str(row.get(c_sur_gd, "")).strip() if c_sur_gd else ""
                            nam = str(row.get(c_name_gd, "")).strip() if c_name_gd else ""
                            
                            if uid and uid != "":
                                if not user_df_raw.empty:
                                    matched = user_df_raw[user_df_raw[u_id_col].apply(normalize_id) == str(uid)]
                                    if not matched.empty:
                                        return uid, matched.iloc[0].get("_surname", sur), matched.iloc[0].get("_name", nam)
                                return uid, sur, nam
                            else:
                                return "", sur, nam
    
                        gv_rows_dict = {}
                        for _, r in df_gd_filtered.iterrows():
                            gvid, sur, nam = get_gv_identity(r)
                            key = gvid if gvid != "" else f"{sur}_{nam}".lower()
                            if key == "_" or key == "":
                                continue
                            if key not in gv_rows_dict:
                                gv_rows_dict[key] = {"id": gvid, "surname": sur, "name": nam, "rows": []}
                            gv_rows_dict[key]["rows"].append(r)
    
                        gv_report_rows = []
                        for k, info in gv_rows_dict.items():
                            sub_df = pd.DataFrame(info["rows"])
                            tot_mon = sub_df[c_sub].nunique()
                            tot_lop = sub_df[c_cls].nunique()
                            tot_tiet = sub_df[c_per].sum()
                            danh_sach_mon = ", ".join(sub_df[c_sub].dropna().unique().astype(str))
                            fac = sub_df["_norm_fac"].iloc[0] if "_norm_fac" in sub_df.columns else ""
    
                            gv_report_rows.append({
                                "id": info["id"],
                                "surname": info["surname"],
                                "name": info["name"],
                                "Bộ môn": fac,
                                "Tổng số môn đảm nhiệm": tot_mon,
                                "Danh sách các môn đã giảng": danh_sach_mon,
                                "Tổng số lớp": tot_lop,
                                "Tổng số tiết": tot_tiet
                            })
    
                        df_gv_table2_raw = pd.DataFrame(gv_report_rows)

                        # Lọc bảng 2 theo radio Bộ môn đã chọn
                        if selected_gv_table2_bm != "Tất cả bộ môn" and not df_gv_table2_raw.empty:
                            df_gv_table2_raw = df_gv_table2_raw[df_gv_table2_raw["Bộ môn"].astype(str).str.lower().str.contains(selected_gv_table2_bm.lower(), na=False)]

                        if not df_gv_table2_raw.empty:
                            st.dataframe(df_gv_table2_raw, use_container_width=True)
                        else:
                            st.warning(f"⚠️ Không có dữ liệu giảng viên thuộc bộ môn **{selected_gv_table2_bm}** trong năm học đã chọn.")

                    st.markdown("###### 👥 Bảng tổng hợp khối lượng giảng dạy theo từng Giảng viên")
                    st.caption("Để biết cụ thể GV nào, năm nào, giảng mấy môn, bao nhiêu lớp")
                    
                    # Thêm radio chọn nhanh bộ môn để lọc danh sách giảng viên hiển thị
                    selected_gv_filter_bm = st.radio(
                        "📌 Lọc xem giảng viên theo Bộ môn:",
                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                        horizontal=True,
                        key="radio_filter_gv_summary_bm_gd"
                    )

                    available_years_gd = sorted(df_clean["năm học"].dropna().unique().tolist(), reverse=True)
    
                    selected_years_gv = st.multiselect(
                        "📅 Chọn năm học hiển thị cho bảng giảng viên (Bỏ trống = Chọn tất cả):",
                        options=available_years_gd,
                        default=available_years_gd,
                        key="multiselect_gv_years"
                    )
    
                    df_gv_filtered = df_clean.copy()
                    
                    # Lọc theo năm học nếu có chọn
                    if selected_years_gv:
                        df_gv_filtered = df_gv_filtered[df_gv_filtered["năm học"].isin(selected_years_gv)]

                    # Lọc theo bộ môn được chọn qua radio
                    if selected_gv_filter_bm != "Tất cả bộ môn" and not user_df_raw.empty:
                        bm_gv_target_ids = user_df_raw[user_df_raw["normalized_faculty"] == selected_gv_filter_bm][u_id_col].apply(normalize_id).tolist()
                        if c_id_gd:
                            df_gv_filtered = df_gv_filtered[df_gv_filtered[c_id_gd].apply(normalize_id).isin(bm_gv_target_ids)]
    
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
                            "Giảng viên": [f"**Tổng cộng ({selected_gv_filter_bm})**"],
                            "Năm học": [""],
                            "Số lượng môn đã giảng": [tot_unique_mon_all],
                            "Tổng số lớp": [tot_lop_all],
                            "Tổng số tiết": [tot_tiet_all]
                        })
                        df_gv_display = pd.concat([df_gv_display, total_row_all], ignore_index=True)
    
                        with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                            st.dataframe(df_gv_display, use_container_width=True)

                        st.markdown("###### 📊 Biểu đồ trực quan: Tổng số môn đã giảng theo từng Giảng viên")
                        df_chart_gv = df_gv_filtered.groupby("_full_name").agg(
                            Tổng_số_môn=(c_subject, "nunique"),
                            Tổng_số_tiết=(tiet_col, "sum")
                        ).reset_index().rename(columns={"_full_name": "Giảng viên"}).sort_values("Tổng_số_môn", ascending=False)
    
                        if not df_chart_gv.empty:
                            unique_gv_labels = df_chart_gv["Giảng viên"].astype(str).tolist()
                            gv_label_mapping = {lbl: f"GV{i+1}" for i, lbl in enumerate(unique_gv_labels)}
                            df_chart_gv["Ký hiệu GV"] = df_chart_gv["Giảng viên"].map(gv_label_mapping)
    
                            num_items_gv = len(df_chart_gv)
                            fig_gv, ax_gv = plt.subplots(figsize=(max(6, len(df_chart_gv) * 0.5), 4.5))
                            
                            bars_gv = ax_gv.bar(df_chart_gv["Ký hiệu GV"].astype(str), df_chart_gv["Tổng_số_môn"], color="#59a14f", width=0.6)
                            
                            for bar in bars_gv:
                                h = bar.get_height()
                                if h > 0:
                                    ax_gv.annotate(f"{int(h)}", 
                                                   (bar.get_x() + bar.get_width() / 2., h),
                                                   ha='center', va='bottom', fontsize=8, fontweight='bold',
                                                   xytext=(0, 2), textcoords='offset points')
                                    
                            ax_gv.set_xlabel("Ký hiệu Giảng viên", fontsize=9)
                            ax_gv.set_ylabel("Số lượng môn đã giảng", fontsize=9)
                            ax_gv.set_title(f"Tổng số môn học theo từng Giảng viên ({selected_gv_filter_bm})", fontsize=10, fontweight="bold")
                            ax_gv.tick_params(axis="x", rotation=45)
                            ax_gv.grid(axis="y", linestyle="--", alpha=0.5)
                            st.pyplot(fig_gv, bbox_inches="tight")
                            plt.close(fig_gv)
    
                            st.markdown("**📝 Chú thích ký hiệu trục hoành (Giảng viên):**")
                            with st.expander("📅 **(Bấm để mở/đóng chú thích GV)**", expanded=True):
                                note_gv_df = pd.DataFrame(list(gv_label_mapping.items()), columns=["Ký hiệu", "Tên Giảng viên đầy đủ"])
                                st.dataframe(note_gv_df, use_container_width=True)
                        else:
                            st.warning("⚠️ Không có dữ liệu giảng viên cho bộ môn đã chọn.")
                    else:
                        st.warning("⚠️ Không có dữ liệu giảng viên cho năm học và bộ môn đã chọn.")
                    # ==========================================
                    # 🔍 2. BẢNG CHI TIẾT GIẢNG DẠY (TÙY CHỈNH THEO TIÊU CHÍ)
                    # ==========================================
                    st.markdown("##### 🔍 3. Bảng chi tiết Giảng dạy (Tùy chỉnh theo tiêu chí)")
                    with st.expander("📅 **(Bấm để mở/đóng tùy chọn tiêu chí động)**", expanded=True):
                        col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
                        with col_opt1:
                            opt_year = st.checkbox("Theo Năm học", value=True, key="chk_gd_year_v2")
                            opt_know = st.checkbox("Theo Khối kiến thức", value=False, key="chk_gd_know_v2")
                            opt_faculty = st.checkbox("Theo Khoa quản lý", value=True, key="chk_gd_fac_v2")
                        with col_opt2:
                            opt_prog = st.checkbox("Theo Chương trình", value=False, key="chk_gd_prog_v2")
                            opt_sess = st.checkbox("Theo Ca học", value=False, key="chk_gd_sess_v2")
                            opt_note = st.checkbox("Theo Kiêm chức", value=False, key="chk_gd_note_v2")
                        with col_opt3:
                            opt_subj = st.checkbox("Theo Môn học", value=False, key="chk_gd_subj_v2")
                            opt_loc = st.checkbox("Theo Địa điểm", value=False, key="chk_gd_loc_v2")
                            opt_dot = st.checkbox("Theo Đợt học", value=False, key="chk_gd_dot_v2")  
                        with col_opt4:
                            opt_lecturer = st.checkbox("Theo Giảng viên", value=False, key="chk_gd_lect_v2")
                            opt_term = st.checkbox("Theo Học kỳ", value=True, key="chk_gd_term_v2")

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
                        if opt_dot and c_dot in df_clean.columns:
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
                        if c_program: rename_detail_dict[c_program] = "Chương trình"
                        if c_knowledge: rename_detail_dict[c_knowledge] = "Khối kiến thức"
                        if c_session: rename_detail_dict[c_session] = "Ca học"
                        if c_location: rename_detail_dict[c_location] = "Địa điểm"
                        if c_term: rename_detail_dict[c_term] = "Học kỳ"
                        if c_dot: rename_detail_dict[c_dot] = "Đợt học"  
                        if c_faculty: rename_detail_dict[c_faculty] = "Khoa quản lý"
                        if c_note: rename_detail_dict[c_note] = "Kiêm chức"

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
                    # 📊 4. BIỂU ĐỒ TRỰC QUAN & BÓC TÁCH GIẢNG DẠY
                    # ==========================================
                    if not df_clean.empty:
                        st.markdown("##### 📊 4. Biểu đồ trực quan khối lượng giảng dạy (theo tiêu chí tại bảng 3)")

                        df_plot_data = df_clean.copy()

                        # Định nghĩa từ điển ánh xạ tên tiêu chí động
                        reverse_rename_dict = {
                            c_subject: "Tên môn học",
                            "_full_name": "Giảng viên",
                            c_class: "Lớp",
                            c_term: "Học kỳ",
                            c_program: "Chương trình",
                            c_knowledge: "Khối kiến thức",
                            c_session: "Ca học",
                            c_location: "Địa điểm",
                            c_dot: "Đợt học",
                            c_faculty: "Khoa quản lý",
                            c_note: "Kiêm chức"
                        }

                        # Các tiêu chí có thể bóc tách biểu đồ
                        criteria_options = []
                        if c_subject in df_plot_data.columns: criteria_options.append("Tên môn học")
                        if "_full_name" in df_plot_data.columns: criteria_options.append("Giảng viên")
                        if c_class in df_plot_data.columns: criteria_options.append("Lớp")
                        if c_term in df_plot_data.columns and c_term: criteria_options.append("Học kỳ")
                       
                        # 🌟 4.1 PHÂN TÍCH THEO TỪNG NĂM HỌC (Biểu đồ nhóm thông thường)
                        has_year_selected = "năm học" in df_plot_data.columns and len(selected_report_years) != 1
                        chart_criteria_cols = [col for col in group_detail_keys if col != "năm học"]
                        
                        if has_year_selected and chart_criteria_cols:
                            st.markdown("###### 🌟 4.1 Phân tích theo từng năm học")
                            
                            for actual_crit_col in chart_criteria_cols:
                                display_crit_name = reverse_rename_dict.get(actual_crit_col, actual_crit_col)
                                st.markdown(f"####### 📌 Phân tích tiêu chí **{display_crit_name}** so sánh theo **Năm học**")
                                
                                df_crit_filtered = df_plot_data.copy()

                                # 🏢 Nếu tiêu chí là Giảng viên, bổ sung radio 3 bộ môn để lọc
                                if actual_crit_col == "_full_name":
                                    st.markdown("📌 **Lọc nhanh giảng viên theo Bộ môn cho biểu đồ 4.1:**")
                                    selected_chart_bm_41 = st.radio(
                                        "Chọn bộ môn:",
                                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                                        horizontal=True,
                                        key=f"radio_chart_filter_bm_gd_41_{actual_crit_col}"
                                    )
                                    pass
                                # 🏢 Nếu tiêu chí là "Tên môn học", bổ sung thêm radio chọn Bộ môn để lọc nhanh danh sách môn hiển thị trên biểu đồ
                                elif actual_crit_col == c_subject:
                                    st.markdown("📌 **Lọc nhanh môn học theo Bộ môn cho biểu đồ 4.1::**")
                                    selected_chart_bm_subj = st.radio(
                                        "Chọn bộ môn quản lý môn học:",
                                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                                        horizontal=True,
                                        key=f"radio_chart_filter_bm_subj_{actual_crit_col}_{report_level}"
                                    )
                                    if selected_chart_bm_subj != "Tất cả bộ môn" and "_norm_fac" in df_crit_filtered.columns:
                                        df_crit_filtered = df_crit_filtered[df_crit_filtered["_norm_fac"].astype(str).str.lower().str.contains(selected_chart_bm_subj.lower(), na=False)]
                                
                                    if selected_chart_bm_41 != "Tất cả bộ môn" and not user_df_raw.empty:
                                        bm_target_ids = user_df_raw[user_df_raw["normalized_faculty"] == selected_chart_bm_41][u_id_col].apply(normalize_id).tolist()
                                        if c_id_gd:
                                            df_crit_filtered = df_crit_filtered[df_crit_filtered[c_id_gd].apply(normalize_id).isin(bm_target_ids)]

                                if actual_crit_col in [c_subject, "_full_name"]:
                                    unique_vals_crit = sorted(df_crit_filtered[actual_crit_col].astype(str).unique())
                                    selected_vals_crit = st.multiselect(
                                        f"🎯 Lọc {display_crit_name} hiển thị trên biểu đồ so sánh (Bỏ trống = Hiện toàn bộ):",
                                        options=unique_vals_crit,
                                        key=f"filter_gd_dyn_crit_{actual_crit_col}"
                                    )
                                    if selected_vals_crit:
                                        df_crit_filtered = df_crit_filtered[df_crit_filtered[actual_crit_col].astype(str).isin(selected_vals_crit)]

                                if df_crit_filtered.empty:
                                    st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho tiêu chí **{display_crit_name}**.")
                                    continue

                                df_agg_yr = df_crit_filtered.groupby([actual_crit_col, "năm học"]).agg(
                                    Tổng_số_tiết=(tiet_col, "sum"),
                                    Số_lượng_lớp=(c_class, "nunique")
                                ).reset_index()

                                df_pivot_tiet_yr = df_agg_yr.pivot_table(index=actual_crit_col, columns="năm học", values="Tổng_số_tiết", aggfunc="sum").fillna(0)
                                df_pivot_lop_yr = df_agg_yr.pivot_table(index=actual_crit_col, columns="năm học", values="Số_lượng_lớp", aggfunc="sum").fillna(0)

                                unique_labels_yr = df_pivot_tiet_yr.index.astype(str).tolist()
                                needs_mapping_yr = any(len(lbl) > 15 for lbl in unique_labels_yr)

                                label_mapping_yr = {}
                                if needs_mapping_yr:
                                    label_mapping_yr = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels_yr)}
                                    df_pivot_tiet_yr.index = df_pivot_tiet_yr.index.map(label_mapping_yr)
                                    df_pivot_lop_yr.index = df_pivot_lop_yr.index.map(label_mapping_yr)

                                num_bars_yr = len(df_pivot_tiet_yr)
                                dyn_w_yr = min(max(6.5, num_bars_yr * 0.5), 11.0)
                                f_size_yr = 6 if num_bars_yr > 15 else (7 if num_bars_yr > 10 else 8)

                                col_y1, col_y2 = st.columns(2)

                                with col_y1:
                                    fig_y1, ax_y1 = plt.subplots(figsize=(dyn_w_yr, 4.0))
                                    df_pivot_tiet_yr.plot(kind="bar", stacked=False, ax=ax_y1, width=0.8, colormap="tab20")
                                    for p in ax_y1.patches:
                                        h = p.get_height()
                                        if h > 0:
                                            ax_y1.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                           ha='center', va='bottom', fontsize=f_size_yr, fontweight='bold',
                                                           rotation=45 if num_bars_yr > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                    ax_y1.set_xlabel("Ký hiệu" if needs_mapping_yr else display_crit_name, fontsize=9)
                                    ax_y1.set_ylabel("Tổng số tiết", fontsize=9)
                                    ax_y1.set_title(f"So sánh Tổng số tiết - {display_crit_name} qua các Năm học", fontsize=10, fontweight="bold")
                                    ax_y1.tick_params(axis="x", rotation=45 if num_bars_yr > 4 else 0)
                                    ax_y1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                    ax_y1.grid(axis="y", linestyle="--", alpha=0.5)
                                    st.pyplot(fig_y1, bbox_inches="tight")
                                    plt.close(fig_y1)

                                with col_y2:
                                    fig_y2, ax_y2 = plt.subplots(figsize=(dyn_w_yr, 4.0))
                                    df_pivot_lop_yr.plot(kind="bar", stacked=False, ax=ax_y2, width=0.8, colormap="Accent")
                                    for p in ax_y2.patches:
                                        h = p.get_height()
                                        if h > 0:
                                            ax_y2.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                           ha='center', va='bottom', fontsize=f_size_yr, fontweight='bold',
                                                           rotation=45 if num_bars_yr > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                    ax_y2.set_xlabel("Ký hiệu" if needs_mapping_yr else display_crit_name, fontsize=9)
                                    ax_y2.set_ylabel("Số lượng lớp", fontsize=9)
                                    ax_y2.set_title(f"So sánh Số lượng lớp - {display_crit_name} qua các Năm học", fontsize=10, fontweight="bold")
                                    ax_y2.tick_params(axis="x", rotation=45 if num_bars_yr > 4 else 0)
                                    ax_y2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                    ax_y2.grid(axis="y", linestyle="--", alpha=0.5)
                                    st.pyplot(fig_y2, bbox_inches="tight")
                                    plt.close(fig_y2)

                                if needs_mapping_yr:
                                    st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({display_crit_name}):**")
                                    with st.expander(f"📅 **(Bấm để xem chú thích chi tiết)**", expanded=False):
                                        note_df_yr = pd.DataFrame(list(label_mapping_yr.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                        st.dataframe(note_df_yr, use_container_width=True)

                        # ==========================================
                        # 📊 4.2. PHÂN TÍCH THEO TỪNG HỌC KỲ (Bám theo bảng động)
                        # ==========================================
                        st.markdown("---")
                        st.markdown("###### 📊 4.2. Phân tích theo từng học kỳ")
                        
                        chart_criteria_cols_32 = [col for col in group_detail_keys if col not in ["năm học", c_term]]

                        if criteria_options and chart_criteria_cols_32:
                            for actual_crit_col in chart_criteria_cols_32:
                                display_crit_name = reverse_rename_dict.get(actual_crit_col, actual_crit_col)
                                st.markdown(f"####### 📌 Phân tích tiêu chí **{display_crit_name}** theo **Học kỳ & Năm học**")

                                df_crit_filtered_32 = df_plot_data.copy()
                                
                                if actual_crit_col == "_full_name":
                                    st.markdown("📌 **Lọc nhanh giảng viên theo Bộ môn cho biểu đồ 4.2:**")
                                    selected_chart_bm_42 = st.radio(
                                        "Chọn bộ môn:",
                                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                                        horizontal=True,
                                        key="radio_chart_filter_bm_gd_42"
                                    )
                                    pass
                                # 🏢 Nếu tiêu chí là Giảng viên, bổ sung radio 3 bộ môn để lọc
                                elif actual_crit_col == c_subject:
                                    st.markdown("📌 **Lọc nhanh môn học theo Bộ môn:**")
                                    selected_chart_bm_subj = st.radio(
                                        "Chọn bộ môn quản lý môn học:",
                                        options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                                        horizontal=True,
                                        key=f"radio_chart_filter_bm_subj_{actual_crit_col}_{report_level}"
                                    )
                                    if selected_chart_bm_subj != "Tất cả bộ môn" and "_norm_fac" in df_crit_filtered.columns:
                                        df_crit_filtered = df_crit_filtered[df_crit_filtered["_norm_fac"].astype(str).str.lower().str.contains(selected_chart_bm_subj.lower(), na=False)]
                                    if selected_chart_bm_42 != "Tất cả bộ môn" and not user_df_raw.empty:
                                        bm_target_ids_42 = user_df_raw[user_df_raw["normalized_faculty"] == selected_chart_bm_42][u_id_col].apply(normalize_id).tolist()
                                        if c_id_gd:
                                            df_crit_filtered_32 = df_crit_filtered_32[df_crit_filtered_32[c_id_gd].apply(normalize_id).isin(bm_target_ids_42)]

                                if actual_crit_col in [c_subject, "_full_name"]:
                                    unique_vals_crit = sorted(df_crit_filtered_32[actual_crit_col].astype(str).unique())
                                    selected_vals_crit = st.multiselect(
                                        f"🎯 Lọc {display_crit_name} hiển thị trên biểu đồ phân tích (Bỏ trống = Hiện toàn bộ):",
                                        options=unique_vals_crit,
                                        key=f"filter_gd_32_crit_{actual_crit_col}"
                                    )
                                    if selected_vals_crit:
                                        df_crit_filtered_32 = df_crit_filtered_32[df_crit_filtered_32[actual_crit_col].astype(str).isin(selected_vals_crit)]

                                if df_crit_filtered_32.empty or not c_term or c_term not in df_crit_filtered_32.columns:
                                    st.warning(f"⚠️ Không đủ dữ liệu học kỳ hoặc không có bản ghi phù hợp cho tiêu chí **{display_crit_name}**.")
                                    continue

                                df_crit_filtered_32["_Học_kỳ_Năm_học"] = df_crit_filtered_32[c_term].astype(str) + " (" + df_crit_filtered_32["năm học"].astype(str) + ")"

                                df_agg_term_yr = df_crit_filtered_32.groupby([actual_crit_col, "_Học_kỳ_Năm_học"]).agg(
                                    Tổng_số_tiết=(tiet_col, "sum"),
                                    Số_lượng_lớp=(c_class, "nunique")
                                ).reset_index()

                                df_pivot_tiet_term = df_agg_term_yr.pivot_table(index=actual_crit_col, columns="_Học_kỳ_Năm_học", values="Tổng_số_tiết", aggfunc="sum").fillna(0)
                                df_pivot_lop_term = df_agg_term_yr.pivot_table(index=actual_crit_col, columns="_Học_kỳ_Năm_học", values="Số_lượng_lớp", aggfunc="sum").fillna(0)

                                unique_labels_term = df_pivot_tiet_term.index.astype(str).tolist()
                                needs_mapping_term = any(len(lbl) > 15 for lbl in unique_labels_term)

                                label_mapping_term = {}
                                if needs_mapping_term:
                                    label_mapping_term = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels_term)}
                                    df_pivot_tiet_term.index = df_pivot_tiet_term.index.map(label_mapping_term)
                                    df_pivot_lop_term.index = df_pivot_lop_term.index.map(label_mapping_term)

                                num_bars_term = len(df_pivot_tiet_term)
                                dyn_w_term = min(max(6.5, num_bars_term * 0.5), 11.0)
                                f_size_term = 6 if num_bars_term > 15 else (7 if num_bars_term > 10 else 8)

                                col_t1, col_t2 = st.columns(2)

                                with col_t1:
                                    fig_t1, ax_t1 = plt.subplots(figsize=(dyn_w_term, 4.0))
                                    df_pivot_tiet_term.plot(kind="bar", ax=ax_t1, width=0.8, colormap="tab20")
                                    for p in ax_t1.patches:
                                        h = p.get_height()
                                        if h > 0:
                                            ax_t1.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                           ha='center', va='bottom', fontsize=f_size_term, fontweight='bold',
                                                           rotation=45 if num_bars_term > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                    ax_t1.set_xlabel("Ký hiệu" if needs_mapping_term else display_crit_name, fontsize=9)
                                    ax_t1.set_ylabel("Tổng số tiết", fontsize=9)
                                    ax_t1.set_title(f"So sánh Tổng số tiết - {display_crit_name} theo Học kỳ/Năm học", fontsize=10, fontweight="bold")
                                    ax_t1.tick_params(axis="x", rotation=45 if num_bars_term > 4 else 0)
                                    #ax_t1.legend(title="Học kỳ (Năm học)", fontsize=7, title_fontsize=7, loc="upper right")
                                    # Cấu hình legend đặt bên dưới trục hoành
                                    ax_t1.legend(
                                        title="Học kỳ (Năm học)", 
                                        fontsize=7, 
                                        title_fontsize=7, 
                                        loc="upper center", 
                                        bbox_to_anchor=(0.5, -0.25),  # Đưa legend xuống dưới trục hoành
                                        ncol=3                        # Chia thành các cột ngang cho gọn
                                    )
                                    ax_t1.grid(axis="y", linestyle="--", alpha=0.5)
                                    st.pyplot(fig_t1, bbox_inches="tight")
                                    plt.close(fig_t1)

                                with col_t2:
                                    fig_t2, ax_t2 = plt.subplots(figsize=(dyn_w_term, 4.0))
                                    df_pivot_lop_term.plot(kind="bar", ax=ax_t2, width=0.8, colormap="Accent")
                                    for p in ax_t2.patches:
                                        h = p.get_height()
                                        if h > 0:
                                            ax_t2.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                           ha='center', va='bottom', fontsize=f_size_term, fontweight='bold',
                                                           rotation=45 if num_bars_term > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                    ax_t2.set_xlabel("Ký hiệu" if needs_mapping_term else display_crit_name, fontsize=9)
                                    ax_t2.set_ylabel("Số lượng lớp", fontsize=9)
                                    ax_t2.set_title(f"So sánh Số lượng lớp - {display_crit_name} theo Học kỳ/Năm học", fontsize=10, fontweight="bold")
                                    ax_t2.tick_params(axis="x", rotation=45 if num_bars_term > 4 else 0)
                                    #ax_t2.legend(title="Học kỳ (Năm học)", fontsize=7, title_fontsize=7, loc="upper right")
                                    # Cấu hình legend đặt bên dưới trục hoành
                                    ax_t2.legend(
                                        title="Học kỳ (Năm học)", 
                                        fontsize=7, 
                                        title_fontsize=7, 
                                        loc="upper center", 
                                        bbox_to_anchor=(0.5, -0.25),  # Đưa legend xuống dưới trục hoành
                                        ncol=3                        # Chia thành các cột ngang cho gọn
                                    )
                                    ax_t2.grid(axis="y", linestyle="--", alpha=0.5)
                                    st.pyplot(fig_t2, bbox_inches="tight")
                                    plt.close(fig_t2)

                                if needs_mapping_term:
                                    st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({display_crit_name}):**")
                                    with st.expander(f"📅 **(Bấm để xem chú thích chi tiết)**", expanded=False):
                                        note_df_term = pd.DataFrame(list(label_mapping_term.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                        st.dataframe(note_df_term, use_container_width=True)
                    else:
                        st.warning("⚠️ Không có dữ liệu giảng dạy cho năm học đã chọn.")
                 
                elif report_level == "(2) Từng bộ môn":
                    st.markdown("#### 🏢 Báo cáo tổng hợp theo từng Bộ môn quản lý học phần (Giảng dạy)")
                   
                    if "lãnh đạo bộ môn" in pos:
                        bms = [u_faculty] if u_faculty else ["BM TCDN"]
                    else:
                        bms = ["BM TCDN", "BM ĐTTC", "BM QFRM"]
                        
                    selected_bm = st.radio(
                        "📌 Chọn bộ môn muốn xem báo cáo:",
                        options=bms,
                        horizontal=True,
                        key="radio_select_single_bm_tab4_v3"
                    )

                    # 🛠️ Khai báo các biến tên cột bị thiếu để tránh lỗi NameError
                    tiet_col = next((c for c in df_gd_filtered.columns if any(x in c for x in ["tiết", "period"])), df_gd_filtered.columns[-1])
                    c_class = next((c for c in df_gd_filtered.columns if "class" in c or "lớp" in c), df_gd_filtered.columns[0])
                    c_subject = next((c for c in df_gd_filtered.columns if "subject" in c or "môn" in c), df_gd_filtered.columns[0])
                    c_id_gd = next((c for c in df_gd_filtered.columns if c in ["id", "mã", "code_gv", "gv", "code"]), None)
                    c_note_gd = next((c for c in df_gd_filtered.columns if any(x in c for x in ["note", "kiêm chức", "ghi chú"])), None)
                    c_program = "program" if "program" in df_gd_filtered.columns else None
                    c_knowledge = "knowledge" if "knowledge" in df_gd_filtered.columns else None
                    c_session = "session" if "session" in df_gd_filtered.columns else None
                    c_location = "location" if "location" in df_gd_filtered.columns else None
                    c_term = "term" if "term" in df_gd_filtered.columns else None
                    c_faculty = "faculty" if "faculty" in df_gd_filtered.columns else None
                    c_note = "note" if "note" in df_gd_filtered.columns else None
                    
                    df_bm_filtered = df_gd_filtered[df_gd_filtered["_norm_fac"].str.lower().str.contains(selected_bm.lower(), na=False)].copy()

                    # 👈 Bổ sung khai báo c_dot ở đây để tránh lỗi NameError
                    code_col_actual = next((c for c in df_bm_filtered.columns if "code" in c), None) if 'df_bm_filtered' in locals() else None
                    df_bm_filtered["_dot_hoc"] = df_bm_filtered[code_col_actual].astype(str).str.upper().apply(
                        lambda x: "Đợt 1" if "D1" in x or "ĐỢT 1" in x else ("Đợt 2" if "D2" in x or "ĐỢT 2" in x else "Khác")
                    ) if code_col_actual else "Không rõ"
                    c_dot = "_dot_hoc"
                    
                    if df_bm_filtered.empty:
                        st.warning(f"⚠️ Chưa có dữ liệu học phần do bộ môn **{selected_bm}** quản lý trong năm học đã chọn.")
                    else:
                        st.markdown(f"##### 📌 Đang xem dữ liệu quản lý của: **{selected_bm}**")
    
                        if c_sur_gd and c_name_gd and c_sur_gd in df_bm_filtered.columns and c_name_gd in df_bm_filtered.columns:
                            df_bm_filtered["_full_name"] = df_bm_filtered[c_sur_gd].astype(str).str.strip() + " " + df_bm_filtered[c_name_gd].astype(str).str.strip()
                        elif c_name_gd and c_name_gd in df_bm_filtered.columns:
                            df_bm_filtered["_full_name"] = df_bm_filtered[c_name_gd].astype(str).str.strip()
                        else:
                            df_bm_filtered["_full_name"] = "Không rõ"
    
                        if not user_df_raw.empty:
                            df_bm_users = user_df_raw[user_df_raw["normalized_faculty"].str.lower().str.contains(selected_bm.lower())]
                            total_gv_bm = len(df_bm_users)
                            ds_gv_bm_str = ", ".join(df_bm_users["_fullname"].dropna().unique())
                            
                            st.markdown(f"- **Tổng số giảng viên chính thức thuộc bộ môn {selected_bm}:** {total_gv_bm} giảng viên")
                            st.markdown(f"- **Danh sách giảng viên chính thức:** {ds_gv_bm_str}")

                        total_lop_bm = df_bm_filtered[c_cls].nunique()
                        total_tiet_bm = df_bm_filtered[c_per].sum()
                        
                        st.write(f"- **Tổng số lớp học phần do bộ môn quản lý:** {total_lop_bm} lớp")
                        st.write(f"- **Tổng số tiết giảng dạy do bộ môn quản lý:** {total_tiet_bm:,.0f} tiết")
                        st.caption("Số liệu thay đổi khi người dùng chọn theo năm học")
                        # ==========================================
                        # 🧹 1. BẢNG TỔNG HỢP GIẢNG DẠY THEO NĂM HỌC (THUỘC BỘ MÔN)
                        # ==========================================
                        st.markdown(f"##### 🧹 1. Bảng tổng hợp giảng dạy theo Năm học ({selected_bm})")
                        st.caption("Để xem chi tiết theo học kỳ, sử dụng bảng 3 tuỳ chỉnh theo tiêu chí")
                        df_bm_after = df_bm_filtered.groupby("năm học").agg(**{
                            "Tổng số tiết thực hiện": (tiet_col, "sum"),
                            "Số lượng lớp": (c_cls, "nunique"),
                            "Số lượng môn học": (c_subject, "nunique")
                        }).reset_index().sort_values("năm học")
                        
                        df_bm_after = df_bm_after.rename(columns={"năm học": "Năm học"})
                        tot_lop_bm_yr = df_bm_after["Số lượng lớp"].sum()
                        tot_tiet_bm_yr = df_bm_after["Tổng số tiết thực hiện"].sum()

                        df_bm_after_disp = df_bm_after.copy()
                        df_bm_after_disp.loc[len(df_bm_after_disp)] = [f"**Tổng cộng ({selected_bm})**", tot_tiet_bm_yr, tot_lop_bm_yr, float('nan')]
                        df_bm_after_disp = df_bm_after_disp[["Năm học", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]]
                        
                        st.dataframe(df_bm_after_disp, use_container_width=True)

                        # Thống kê môn học nổi bật
                        df_sub_stat_bm = df_bm_filtered.groupby([c_sub, "năm học"]).agg(
                            Tổng_lớp=(c_cls, "nunique"),
                            Tổng_tiết=(c_per, "sum")
                        ).reset_index()
                        if not df_sub_stat_bm.empty:
                            m_max_lop = df_sub_stat_bm.loc[df_sub_stat_bm["Tổng_lớp"].idxmax()]
                            m_min_lop = df_sub_stat_bm.loc[df_sub_stat_bm["Tổng_lớp"].idxmin()]
    
                            st.markdown("##### 📈 Thống kê nổi bật về Môn học")
                            st.caption("Số liệu thay đổi khi người dùng chọn theo năm học")
                            st.markdown(
                                f"""
                                * 🥇 **Môn học có nhiều lớp nhất:** {m_max_lop[c_sub]} ({m_max_lop['Tổng_lớp']} lớp — Năm học: {m_max_lop['năm học']})
                                * 📉 **Môn học có ít lớp nhất:** {m_min_lop[c_sub]} ({m_min_lop['Tổng_lớp']} lớp — Năm học: {m_min_lop['năm học']})
                                """
                            )
                        # ==========================================
                        # 📈 THỐNG KÊ NỔI BẬT VỀ GIẢNG VIÊN THEO TỪNG BỘ MÔN
                        # ==========================================
                        if c_id_gd and not df_bm_filtered.empty:
                            df_bm_gv_work = df_bm_filtered.copy()
                            
                            # Loại trừ giảng viên mời ngoài (nếu có cột note giống logic toàn khoa)
                            if c_note_gd and c_note_gd in df_bm_gv_work.columns:
                                mask_bm_moi_ngoai = df_bm_gv_work[c_note_gd].astype(str).str.lower().str.contains("kiêm chức|khác bộ môn", na=False)
                                df_bm_gv_work = df_bm_gv_work[~mask_bm_moi_ngoai]

                            # Lọc chỉ lấy các giảng viên chính thức thuộc bộ môn đó trong danh sách user_df_raw
                            if not user_df_raw.empty:
                                bm_official_ids = user_df_raw[user_df_raw["normalized_faculty"].str.lower().str.contains(selected_bm.lower())][u_id_col].apply(normalize_id).tolist()
                                df_bm_gv_work = df_bm_gv_work[df_bm_gv_work[c_id_gd].apply(normalize_id).isin(bm_official_ids)]

                            if not df_bm_gv_work.empty:
                                df_bm_gv_stat = df_bm_gv_work.groupby([c_id_gd, "năm học"]).agg(
                                    Tổng_lớp=(c_cls, "nunique"),
                                    Tổng_tiết=(tiet_col, "sum")
                                ).reset_index()
                                df_bm_gv_stat = df_bm_gv_stat[df_bm_gv_stat[c_id_gd] != ""]

                                if not df_bm_gv_stat.empty:
                                    max_lop_bm = df_bm_gv_stat.loc[df_bm_gv_stat["Tổng_lớp"].idxmax()]
                                    min_lop_bm = df_bm_gv_stat.loc[df_bm_gv_stat["Tổng_lớp"].idxmin()]

                                    def get_bm_gv_name_by_id(gvid):
                                        if not user_df_raw.empty:
                                            matched = user_df_raw[user_df_raw[u_id_col].apply(normalize_id) == str(gvid)]
                                            if not matched.empty:
                                                return matched.iloc[0].get("_fullname", gvid)
                                        return gvid

                                    st.markdown(f"##### 📈 Thống kê nổi bật về Giảng viên thuộc bộ môn {selected_bm} (Không tính mời ngoài)")
                                    st.caption("Số liệu thay đổi khi người dùng chọn theo năm học")
                                    st.markdown(
                                        f"""
                                        * 🥇 **Giảng viên dạy nhiều lớp nhất:** ID `{max_lop_bm[c_id_gd]}` - {get_bm_gv_name_by_id(max_lop_bm[c_id_gd])} ({max_lop_bm['Tổng_lớp']} lớp — Năm học: {max_lop_bm['năm học']})
                                        * 📉 **Giảng viên dạy ít lớp nhất:** ID `{min_lop_bm[c_id_gd]}` - {get_bm_gv_name_by_id(min_lop_bm[c_id_gd])} ({min_lop_bm['Tổng_lớp']} lớp — Năm học: {min_lop_bm['năm học']})
                                        """
                                    )

                        st.markdown(f"##### 📚 2. Bảng tổng hợp chi tiết môn học của {selected_bm}")
                        st.caption("Để biết môn đó có những GV nào dạy")
                        df_bm_summary = df_bm_filtered.groupby([c_sub]).agg(
                            Tổng_số_lớp=(c_cls, "nunique"),
                            Tổng_số_tiết=(c_per, "sum"),
                            Danh_sách_giảng_viên=("_full_name", lambda x: ", ".join(x.dropna().unique()))
                        ).reset_index()
                        
                        df_bm_summary = df_bm_summary.rename(columns={
                            c_sub: "Tên môn học",
                            "Tổng_số_lớp": "Tổng số lớp",
                            "Tổng_số_tiết": "Tổng số tiết",
                            "Danh_sách_giảng_viên": "Danh sách giảng viên"
                        })
    
                        st.dataframe(df_bm_summary, use_container_width=True, hide_index=False)

                        # ==========================================
                        # 🔍 3. BẢNG CHI TIẾT GIẢNG DẠY (TÙY CHỈNH THEO TIÊU CHÍ CHO BỘ MÔN)
                        # ==========================================
                        st.markdown(f"##### 🔍 3. Bảng chi tiết Giảng dạy theo tiêu chí ({selected_bm})")
                        with st.expander("📅 **(Bấm để mở/đóng tùy chọn tiêu chí động)**", expanded=True):
                            col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
                            with col_opt1:
                                opt_year = st.checkbox("Theo Năm học", value=True, key=f"chk_gd_year_bm_{selected_bm}")
                                opt_know = st.checkbox("Theo Khối kiến thức", value=False, key=f"chk_gd_know_bm_{selected_bm}")
                                opt_faculty = st.checkbox("Theo Khoa quản lý", value=True, key=f"chk_gd_fac_bm_{selected_bm}")
                            with col_opt2:
                                opt_prog = st.checkbox("Theo Chương trình", value=False, key=f"chk_gd_prog_bm_{selected_bm}")
                                opt_sess = st.checkbox("Theo Ca học", value=True, key=f"chk_gd_sess_bm_{selected_bm}")
                                opt_note = st.checkbox("Theo Kiêm chức", value=False, key=f"chk_gd_note_bm_{selected_bm}")
                            with col_opt3:
                                opt_subj = st.checkbox("Theo Môn học", value=False, key=f"chk_gd_subj_bm_{selected_bm}")
                                opt_loc = st.checkbox("Theo Địa điểm", value=False, key=f"chk_gd_loc_bm_{selected_bm}")
                                opt_dot = st.checkbox("Theo Đợt học", value=False, key=f"chk_gd_dot_bm_{selected_bm}")  
                            with col_opt4:
                                opt_lecturer = st.checkbox("Theo Giảng viên", value=False, key=f"chk_gd_lect_bm_{selected_bm}")
                                opt_term = st.checkbox("Theo Học kỳ", value=True, key=f"chk_gd_term_bm_{selected_bm}")

                            group_detail_keys_bm = []
                            if opt_year: group_detail_keys_bm.append("năm học")
                            if opt_prog and c_program and c_program in df_bm_filtered.columns: group_detail_keys_bm.append(c_program)
                            if opt_subj: group_detail_keys_bm.append(c_subject)
                            if opt_know and c_knowledge and c_knowledge in df_bm_filtered.columns: group_detail_keys_bm.append(c_knowledge)
                            if opt_sess and c_session and c_session in df_bm_filtered.columns: group_detail_keys_bm.append(c_session)
                            if opt_loc and c_location and c_location in df_bm_filtered.columns: group_detail_keys_bm.append(c_location)
                            if opt_term and c_term and c_term in df_bm_filtered.columns: group_detail_keys_bm.append(c_term)
                            if opt_dot and c_dot in df_bm_filtered.columns: group_detail_keys_bm.append(c_dot)  
                            if opt_faculty and c_faculty and c_faculty in df_bm_filtered.columns: group_detail_keys_bm.append(c_faculty)
                            if opt_note and c_note and c_note in df_bm_filtered.columns: group_detail_keys_bm.append(c_note)
                            if opt_lecturer: group_detail_keys_bm.append("_full_name")

                            if not group_detail_keys_bm: group_detail_keys_bm = ["năm học"]

                            df_bm_detail = df_bm_filtered.groupby(group_detail_keys_bm).agg({
                                tiet_col: "sum",
                                c_class: "nunique"
                            }).reset_index()

                            rename_detail_dict_bm = {
                                "năm học": "Năm học",
                                c_subject: "Tên môn học",
                                tiet_col: "Tổng số tiết",
                                c_class: "Số lượng lớp",
                                "_full_name": "Giảng viên"
                            }
                            if c_program: rename_detail_dict_bm[c_program] = "Chương trình"
                            if c_knowledge: rename_detail_dict_bm[c_knowledge] = "Khối kiến thức"
                            if c_session: rename_detail_dict_bm[c_session] = "Ca học"
                            if c_location: rename_detail_dict_bm[c_location] = "Địa điểm"
                            if c_term: rename_detail_dict_bm[c_term] = "Học kỳ"
                            if c_dot: rename_detail_dict_bm[c_dot] = "Đợt học"  
                            if c_faculty: rename_detail_dict_bm[c_faculty] = "Khoa quản lý"
                            if c_note: rename_detail_dict_bm[c_note] = "Kiêm chức"

                            df_bm_detail = df_bm_detail.rename(columns=rename_detail_dict_bm)

                            if not df_bm_detail.empty:
                                tot_tiet_bm_val = df_bm_detail["Tổng số tiết"].sum()
                                tot_lop_bm_val = df_bm_detail["Số lượng lớp"].sum()
                                total_row_bm = {}
                                for col_name in df_bm_detail.columns:
                                    if col_name == df_bm_detail.columns[0]: total_row_bm[col_name] = "**Tổng cộng**"
                                    elif col_name == "Tổng số tiết": total_row_bm[col_name] = tot_tiet_bm_val
                                    elif col_name == "Số lượng lớp": total_row_bm[col_name] = tot_lop_bm_val
                                    else: total_row_bm[col_name] = ""
                                df_bm_detail.loc[len(df_bm_detail)] = total_row_bm

                                st.dataframe(df_bm_detail, use_container_width=True)

                        # ==========================================
                        # 📊 4. BIỂU ĐỒ TRỰC QUAN KHỐI LƯỢNG GIẢNG DẠY (CẤP ĐỘ BỘ MÔN - TÍCH HỢP KÝ HIỆU TRỤC HOÀNH)
                        # ==========================================
                        if not df_bm_filtered.empty:
                            st.markdown(f"##### 📊 4. Biểu đồ trực quan khối lượng giảng dạy ({selected_bm})")
                            df_bm_plot_data = df_bm_filtered.copy()

                            reverse_rename_dict = {
                                c_subject: "Tên môn học",
                                "_full_name": "Giảng viên",
                                c_class: "Lớp",
                                c_term: "Học kỳ",
                                c_program: "Chương trình",
                                c_knowledge: "Khối kiến thức",
                                c_session: "Ca học",
                                c_location: "Địa điểm",
                                c_dot: "Đợt học",
                                c_faculty: "Khoa quản lý",
                                c_note: "Kiêm chức"
                            }

                            has_year_selected_bm = "năm học" in df_bm_plot_data.columns and len(selected_report_years) != 1
                            chart_criteria_cols_bm = [col for col in group_detail_keys_bm if col != "năm học"]

                            if has_year_selected_bm and chart_criteria_cols_bm:
                                st.markdown("###### 🌟 4.1 Phân tích theo từng năm học")
                                for actual_crit_col in chart_criteria_cols_bm:
                                    display_crit_name = reverse_rename_dict.get(actual_crit_col, actual_crit_col)
                                    st.markdown(f"####### 📌 Phân tích tiêu chí **{display_crit_name}** so sánh theo **Năm học**")
                                    
                                    df_crit_filtered_bm = df_bm_plot_data.copy()
                                    if actual_crit_col in [c_subject, "_full_name"]:
                                        unique_vals_crit = sorted(df_crit_filtered_bm[actual_crit_col].astype(str).unique())
                                        selected_vals_crit = st.multiselect(
                                            f"🎯 Lọc {display_crit_name} hiển thị trên biểu đồ ({selected_bm}):",
                                            options=unique_vals_crit,
                                            key=f"filter_bm_dyn_crit_{selected_bm}_{actual_crit_col}"
                                        )
                                        pass
                                    elif actual_crit_col == c_subject:
                                        st.markdown("📌 **Lọc nhanh môn học theo Bộ môn:**")
                                        selected_chart_bm_subj = st.radio(
                                            "Chọn bộ môn quản lý môn học:",
                                            options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                                            horizontal=True,
                                            key=f"radio_chart_filter_bm_subj_{actual_crit_col}_{report_level}"
                                        )
                                        if selected_chart_bm_subj != "Tất cả bộ môn" and "_norm_fac" in df_crit_filtered.columns:
                                            df_crit_filtered = df_crit_filtered[df_crit_filtered["_norm_fac"].astype(str).str.lower().str.contains(selected_chart_bm_subj.lower(), na=False)]
                                        if selected_vals_crit:
                                            df_crit_filtered_bm = df_crit_filtered_bm[df_crit_filtered_bm[actual_crit_col].astype(str).isin(selected_vals_crit)]

                                    if df_crit_filtered_bm.empty:
                                        st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho tiêu chí **{display_crit_name}**.")
                                        continue

                                    df_agg_yr_bm = df_crit_filtered_bm.groupby([actual_crit_col, "năm học"]).agg(
                                        Tổng_số_tiết=(tiet_col, "sum"),
                                        Số_lượng_lớp=(c_class, "nunique")
                                    ).reset_index()

                                    df_pivot_tiet_yr_bm = df_agg_yr_bm.pivot_table(index=actual_crit_col, columns="năm học", values="Tổng_số_tiết", aggfunc="sum").fillna(0)
                                    df_pivot_lop_yr_bm = df_agg_yr_bm.pivot_table(index=actual_crit_col, columns="năm học", values="Số_lượng_lớp", aggfunc="sum").fillna(0)

                                    # 🔤 TỰ ĐỘNG QUY ĐỔI KÝ HIỆU TRỤC HOÀNH NẾU TÊN QUÁ DÀI
                                    unique_labels_bm = df_pivot_tiet_yr_bm.index.astype(str).tolist()
                                    needs_mapping_bm = any(len(lbl) > 15 for lbl in unique_labels_bm)

                                    label_mapping_bm = {}
                                    if needs_mapping_bm:
                                        label_mapping_bm = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels_bm)}
                                        df_pivot_tiet_yr_bm.index = df_pivot_tiet_yr_bm.index.map(label_mapping_bm)
                                        df_pivot_lop_yr_bm.index = df_pivot_lop_yr_bm.index.map(label_mapping_bm)

                                    num_bars_bm = len(df_pivot_tiet_yr_bm)
                                    dyn_w_bm = min(max(5.0, num_bars_bm * 0.4), 9.0)
                                    f_size_bm = 7

                                    col_bm1, col_bm2 = st.columns(2)
                                    
                                    # Biểu đồ 1: Tổng số tiết theo năm học
                                    with col_bm1:
                                        fig_b1, ax_b1 = plt.subplots(figsize=(dyn_w_bm, 3.5))
                                        df_pivot_tiet_yr_bm.plot(kind="bar", stacked=False, ax=ax_b1, width=0.8, colormap="tab20")
                                        for p in ax_b1.patches:
                                            h = p.get_height()
                                            if h > 0:
                                                ax_b1.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                               ha='center', va='bottom', fontsize=f_size_bm, fontweight='bold',
                                                               rotation=45 if num_bars_bm > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                        ax_b1.set_xlabel("Ký hiệu" if needs_mapping_bm else display_crit_name, fontsize=9)
                                        ax_b1.set_ylabel("Tổng số tiết", fontsize=9)
                                        ax_b1.set_title(f"Tổng số tiết - {display_crit_name} ({selected_bm})", fontsize=10, fontweight="bold")
                                        ax_b1.tick_params(axis="x", rotation=45 if num_bars_bm > 4 else 0)
                                        ax_b1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax_b1.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig_b1, bbox_inches="tight")
                                        plt.close(fig_b1)

                                    # Biểu đồ 2: Số lượng lớp theo năm học
                                    with col_bm2:
                                        fig_b2, ax_b2 = plt.subplots(figsize=(dyn_w_bm, 3.5))
                                        df_pivot_lop_yr_bm.plot(kind="bar", stacked=False, ax=ax_b2, width=0.8, colormap="Accent")
                                        for p in ax_b2.patches:
                                            h = p.get_height()
                                            if h > 0:
                                                ax_b2.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                               ha='center', va='bottom', fontsize=f_size_bm, fontweight='bold',
                                                               rotation=45 if num_bars_bm > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                        ax_b2.set_xlabel("Ký hiệu" if needs_mapping_bm else display_crit_name, fontsize=9)
                                        ax_b2.set_ylabel("Số lượng lớp", fontsize=9)
                                        ax_b2.set_title(f"Số lượng lớp - {display_crit_name} ({selected_bm})", fontsize=10, fontweight="bold")
                                        ax_b2.tick_params(axis="x", rotation=45 if num_bars_bm > 4 else 0)
                                        ax_b2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax_b2.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig_b2, bbox_inches="tight")
                                        plt.close(fig_b2)

                                    # Hiển thị chú thích nếu có ký hiệu quy đổi
                                    if needs_mapping_bm:
                                        st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({display_crit_name}):**")
                                        with st.expander(f"📅 **(Bấm để xem chú thích chi tiết - {selected_bm})**", expanded=False):
                                            note_df_bm = pd.DataFrame(list(label_mapping_bm.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                            st.dataframe(note_df_bm, use_container_width=True)

                                # ==========================================
                                # 📊 4.2. PHÂN TÍCH THEO TỪNG HỌC KỲ (CẤP ĐỘ BỘ MÔN)
                                # ==========================================
                                st.markdown("---")
                                st.markdown(f"###### 📊 4.2. Phân tích theo từng học kỳ ({selected_bm})")
                                
                                # 🛠️ Khai báo biến criteria_options_bm để tránh lỗi NameError
                                criteria_options_bm = []
                                if c_subject in df_bm_plot_data.columns: criteria_options_bm.append("Tên môn học")
                                if "_full_name" in df_bm_plot_data.columns: criteria_options_bm.append("Giảng viên")
                                if c_class in df_bm_plot_data.columns: criteria_options_bm.append("Lớp")
                                if c_term in df_bm_plot_data.columns and c_term: criteria_options_bm.append("Học kỳ")
        
                                chart_criteria_cols_32_bm = [col for col in group_detail_keys_bm if col not in ["năm học", c_term]]
        
                                if criteria_options_bm and chart_criteria_cols_32_bm:
                                    for actual_crit_col in chart_criteria_cols_32_bm:
                                        display_crit_name = reverse_rename_dict.get(actual_crit_col, actual_crit_col)
                                        st.markdown(f"####### 📌 Phân tích tiêu chí **{display_crit_name}** theo **Học kỳ & Năm học**")
        
                                        df_crit_filtered_32_bm = df_bm_plot_data.copy()
        
                                        if actual_crit_col in [c_subject, "_full_name"]:
                                            unique_vals_crit = sorted(df_crit_filtered_32_bm[actual_crit_col].astype(str).unique())
                                            selected_vals_crit = st.multiselect(
                                                f"🎯 Lọc {display_crit_name} hiển thị trên biểu đồ phân tích ({selected_bm}):",
                                                options=unique_vals_crit,
                                                key=f"filter_bm_32_crit_{selected_bm}_{actual_crit_col}"
                                            )
                                            pass
                                        elif actual_crit_col == c_subject:
                                            st.markdown("📌 **Lọc nhanh môn học theo Bộ môn:**")
                                            selected_chart_bm_subj = st.radio(
                                                "Chọn bộ môn quản lý môn học:",
                                                options=["Tất cả bộ môn", "BM TCDN", "BM ĐTTC", "BM QFRM"],
                                                horizontal=True,
                                                key=f"radio_chart_filter_bm_subj_{actual_crit_col}_{report_level}"
                                            )
                                            if selected_chart_bm_subj != "Tất cả bộ môn" and "_norm_fac" in df_crit_filtered.columns:
                                                df_crit_filtered = df_crit_filtered[df_crit_filtered["_norm_fac"].astype(str).str.lower().str.contains(selected_chart_bm_subj.lower(), na=False)]
                                                                                        
                                            if selected_vals_crit:
                                                df_crit_filtered_32_bm = df_crit_filtered_32_bm[df_crit_filtered_32_bm[actual_crit_col].astype(str).isin(selected_vals_crit)]
        
                                        if df_crit_filtered_32_bm.empty or not c_term or c_term not in df_crit_filtered_32_bm.columns:
                                            st.warning(f"⚠️ Không đủ dữ liệu học kỳ hoặc không có bản ghi phù hợp cho tiêu chí **{display_crit_name}**.")
                                            continue
        
                                        df_crit_filtered_32_bm["_Học_kỳ_Năm_học"] = df_crit_filtered_32_bm[c_term].astype(str) + " (" + df_crit_filtered_32_bm["năm học"].astype(str) + ")"
        
                                        df_agg_term_yr_bm = df_crit_filtered_32_bm.groupby([actual_crit_col, "_Học_kỳ_Năm_học"]).agg(
                                            Tổng_số_tiết=(tiet_col, "sum"),
                                            Số_lượng_lớp=(c_class, "nunique")
                                        ).reset_index()
        
                                        df_pivot_tiet_term_bm = df_agg_term_yr_bm.pivot_table(index=actual_crit_col, columns="_Học_kỳ_Năm_học", values="Tổng_số_tiết", aggfunc="sum").fillna(0)
                                        df_pivot_lop_term_bm = df_agg_term_yr_bm.pivot_table(index=actual_crit_col, columns="_Học_kỳ_Năm_học", values="Số_lượng_lớp", aggfunc="sum").fillna(0)
        
                                        # 🔤 TỰ ĐỘNG QUY ĐỔI KÝ HIỆU TRỤC HOÀNH NẾU TÊN QUÁ DÀI
                                        unique_labels_term_bm = df_pivot_tiet_term_bm.index.astype(str).tolist()
                                        needs_mapping_term_bm = any(len(lbl) > 15 for lbl in unique_labels_term_bm)
        
                                        label_mapping_term_bm = {}
                                        if needs_mapping_term_bm:
                                            label_mapping_term_bm = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels_term_bm)}
                                            df_pivot_tiet_term_bm.index = df_pivot_tiet_term_bm.index.map(label_mapping_term_bm)
                                            df_pivot_lop_term_bm.index = df_pivot_lop_term_bm.index.map(label_mapping_term_bm)
        
                                        num_bars_term_bm = len(df_pivot_tiet_term_bm)
                                        dyn_w_term_bm = min(max(5.0, num_bars_term_bm * 0.4), 9.0)
                                        f_size_term_bm = 7
        
                                        col_t1_bm, col_t2_bm = st.columns(2)
        
                                        # Biểu đồ 1: Tổng số tiết theo Học kỳ & Năm học
                                        with col_t1_bm:
                                            fig_t1, ax_t1 = plt.subplots(figsize=(dyn_w_term_bm, 3.5))
                                            df_pivot_tiet_term_bm.plot(kind="bar", ax=ax_t1, width=0.8, colormap="tab20")
                                            for p in ax_t1.patches:
                                                h = p.get_height()
                                                if h > 0:
                                                    ax_t1.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                                   ha='center', va='bottom', fontsize=f_size_term_bm, fontweight='bold',
                                                                   rotation=45 if num_bars_term_bm > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                            ax_t1.set_xlabel("Ký hiệu" if needs_mapping_term_bm else display_crit_name, fontsize=9)
                                            ax_t1.set_ylabel("Tổng số tiết", fontsize=9)
                                            ax_t1.set_title(f"Tổng số tiết - {display_crit_name} theo Học kỳ ({selected_bm})", fontsize=10, fontweight="bold")
                                            ax_t1.tick_params(axis="x", rotation=45 if num_bars_term_bm > 4 else 0)
                                            #ax_t1.legend(title="Học kỳ (Năm học)", fontsize=7, title_fontsize=7, loc="upper right")
                                            # Cấu hình legend đặt bên dưới trục hoành
                                            ax_t1.legend(
                                                title="Học kỳ (Năm học)", 
                                                fontsize=7, 
                                                title_fontsize=7, 
                                                loc="upper center", 
                                                bbox_to_anchor=(0.5, -0.25),  # Đưa legend xuống dưới trục hoành
                                                ncol=3                        # Chia thành các cột ngang cho gọn
                                            )
                                            ax_t1.grid(axis="y", linestyle="--", alpha=0.5)
                                            st.pyplot(fig_t1, bbox_inches="tight")
                                            plt.close(fig_t1)
        
                                        # Biểu đồ 2: Số lượng lớp theo Học kỳ & Năm học
                                        with col_t2_bm:
                                            fig_t2, ax_t2 = plt.subplots(figsize=(dyn_w_term_bm, 3.5))
                                            df_pivot_lop_term_bm.plot(kind="bar", ax=ax_t2, width=0.8, colormap="Accent")
                                            for p in ax_t2.patches:
                                                h = p.get_height()
                                                if h > 0:
                                                    ax_t2.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h),
                                                                   ha='center', va='bottom', fontsize=f_size_term_bm, fontweight='bold',
                                                                   rotation=45 if num_bars_term_bm > 2 else 0, xytext=(0, 2), textcoords='offset points')
                                            ax_t2.set_xlabel("Ký hiệu" if needs_mapping_term_bm else display_crit_name, fontsize=9)
                                            ax_t2.set_ylabel("Số lượng lớp", fontsize=9)
                                            ax_t2.set_title(f"Số lượng lớp - {display_crit_name} theo Học kỳ ({selected_bm})", fontsize=10, fontweight="bold")
                                            ax_t2.tick_params(axis="x", rotation=45 if num_bars_term_bm > 4 else 0)
                                            #ax_t2.legend(title="Học kỳ (Năm học)", fontsize=7, title_fontsize=7, loc="upper right")
                                            # Cấu hình legend đặt bên dưới trục hoành
                                            ax_t2.legend(
                                                title="Học kỳ (Năm học)", 
                                                fontsize=7, 
                                                title_fontsize=7, 
                                                loc="upper center", 
                                                bbox_to_anchor=(0.5, -0.25),  # Đưa legend xuống dưới trục hoành
                                                ncol=3                        # Chia thành các cột ngang cho gọn
                                            )
                                            ax_t2.grid(axis="y", linestyle="--", alpha=0.5)
                                            st.pyplot(fig_t2, bbox_inches="tight")
                                            plt.close(fig_t2)
        
                                        if needs_mapping_term_bm:
                                            st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({display_crit_name}):**")
                                            with st.expander(f"📅 **(Bấm để xem chú thích học kỳ - {selected_bm})**", expanded=False):
                                                note_df_term_bm = pd.DataFrame(list(label_mapping_term_bm.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                                st.dataframe(note_df_term_bm, use_container_width=True)
                
                elif report_level == "(3) Từng giảng viên":
                    st.markdown("#### 👤 Báo cáo tổng hợp theo từng Giảng viên (Giảng dạy)")
                    
                    if df_gd_filtered.empty:
                        st.warning("⚠️ Không có dữ liệu giảng dạy cho năm học đã chọn.")
                    else:
                        df_gv_work_tab4 = df_gd_filtered.copy()
                        if c_sur_gd and c_name_gd and c_sur_gd in df_gv_work_tab4.columns and c_name_gd in df_gv_work_tab4.columns:
                            df_gv_work_tab4["_full_name"] = df_gv_work_tab4[c_sur_gd].astype(str).str.strip() + " " + df_gv_work_tab4[c_name_gd].astype(str).str.strip()
                        elif c_name_gd and c_name_gd in df_gv_work_tab4.columns:
                            df_gv_work_tab4["_full_name"] = df_gv_work_tab4[c_name_gd].astype(str).str.strip()
                        else:
                            df_gv_work_tab4["_full_name"] = "Không rõ"
                    
                        list_all_gv = sorted(df_gv_work_tab4["_full_name"].dropna().unique().tolist())
                        
                        if not list_all_gv or list_all_gv == ["Không rõ"]:
                            st.warning("⚠️ Không tìm thấy tên giảng viên hợp lệ trong dữ liệu.")
                        else:
                            # 🔒 PHÂN QUYỀN: 
                            # - Admin & Lãnh đạo khoa: Xem được toàn bộ giảng viên trong khoa.
                            # - Lãnh đạo bộ môn: Chỉ xem được danh sách giảng viên thuộc bộ môn của mình (bao gồm cả bản thân họ).
                            # - Giảng viên thường: Chỉ thấy và xem được thông tin của chính họ.
                            if "admin" in pos or "lãnh đạo khoa" in pos or "quản lý khoa" in pos:
                                allowed_gvs = list_all_gv
                            elif "lãnh đạo bộ môn" in pos:
                                # Lọc lấy danh sách ID hoặc tên giảng viên thuộc đúng bộ môn của lãnh đạo bộ môn này từ bảng user_df_raw
                                bm_name = u_faculty.strip().lower()
                                if not user_df_raw.empty and bm_name:
                                    bm_gv_ids = user_df_raw[user_df_raw["normalized_faculty"].str.lower().str.contains(bm_name)][u_id_col].apply(normalize_id).tolist()
                                    # Lọc các dòng trong bảng dữ liệu có ID thuộc bộ môn
                                    sub_bm_gv_df = df_gv_work_tab4[df_gv_work_tab4[c_id_gd].apply(normalize_id).isin(bm_gv_ids)] if c_id_gd else df_gv_work_tab4
                                    allowed_gvs = sorted(sub_bm_gv_df["_full_name"].dropna().unique().tolist())
                                else:
                                    allowed_gvs = list_all_gv
                            else:
                                # Giảng viên thường: chỉ thấy tên chính mình
                                my_name = current_user['fullname'].lower()
                                allowed_gvs = [g for g in list_all_gv if my_name in g.lower() or g.lower() in my_name]
                                if not allowed_gvs:
                                    allowed_gvs = [current_user['fullname']]

                            selected_gv = st.selectbox(
                                "📌 Chọn giảng viên muốn xem báo cáo:",
                                options=allowed_gvs,
                                key="selectbox_select_single_gv_tab4"
                            )
                            
                            st.markdown(f"##### 👤 Đang xem báo cáo chi tiết của Giảng viên: **{selected_gv}**")
                            
                            df_gv_data = df_gv_work_tab4[df_gv_work_tab4["_full_name"] == selected_gv].copy()
                          
                            if not df_gv_data.empty:
                                total_lop_gv = df_gv_data[c_cls].nunique()
                                total_tiet_gv = df_gv_data[c_per].sum()
                                total_mon_gv = df_gv_data[c_sub].nunique()
    
                                st.write(f"- **Tổng số môn đảm nhiệm:** {total_mon_gv} môn")
                                st.write(f"- **Tổng số lớp giảng dạy:** {total_lop_gv} lớp")
                                st.write(f"- **Tổng số tiết giảng dạy:** {total_tiet_gv:,.0f} tiết")

                                st.markdown(f"##### 📚 Bảng tổng hợp chi tiết các môn đã giảng của {selected_gv}")
                                df_gv_summary_sub = df_gv_data.groupby([c_sub, "năm học"]).agg(
                                    Tổng_số_lớp=(c_cls, "nunique"),
                                    Tổng_số_tiết=(c_per, "sum")
                                ).reset_index().rename(columns={
                                    c_sub: "Tên môn học",
                                    "năm học": "Năm học",
                                    "Tổng_số_lớp": "Số lượng lớp",
                                    "Tổng_số_tiết": "Tổng số tiết"
                                })
    
                                st.dataframe(df_gv_summary_sub, use_container_width=True)

        # ==========================================
        # 2. BÁO CÁO MẢNG NGHIÊN CỨU KHOA HỌC (NCKH)
        # ==========================================
        elif "Báo cáo Nghiên cứu khoa học (NCKH)" in report_category:
            st.markdown("### 🔬 CHI TIẾT BÁO CÁO NGHIÊN CỨU KHOA HỌC")
            if df_nckh_full is None or df_nckh_full.empty:
                st.warning("⚠️ Không có dữ liệu NCKH.")
            else:
                df_nckh_filtered = apply_year_filter(df_nckh_full)
                df_nckh_filtered.columns = [str(c).strip().lower() for c in df_nckh_filtered.columns]
    
                c_tiet_nckh = next((c for c in df_nckh_filtered.columns if any(x in c for x in ["tiết", "period", "sỐ tiết kê khai"])), df_nckh_filtered.columns[-1])
                df_nckh_filtered[c_tiet_nckh] = pd.to_numeric(df_nckh_filtered[c_tiet_nckh], errors="coerce").fillna(0)
    
                c_loai_hd = next((c for c in df_nckh_filtered.columns if "loại" in c), None)
                c_cap_do = next((c for c in df_nckh_filtered.columns if "cấp độ" in c), None)
                c_pl1 = next((c for c in df_nckh_filtered.columns if "phân loại cấp 1" in c), None)
                c_id_nckh = next((c for c in df_nckh_filtered.columns if c in ["id", "mã", "code", "gv"]), None)
                c_name_prod = next((c for c in df_nckh_filtered.columns if "tên sản phẩm" in c or "tên đề tài" in c or "subject" in c), df_nckh_filtered.columns[0])
    
                if report_level == "(1) Toàn khoa":
                    st.markdown("#### 🌐 Báo cáo tổng hợp Toàn khoa (Nghiên cứu khoa học)")
                    
                    df_temp_detail = df_nckh_filtered.copy()
                    df_temp_detail.columns = [str(c).strip() for c in df_temp_detail.columns]
    
                    tap_chi_col = next(
                        (
                            c for c in df_temp_detail.columns
                            if any(
                                x in c.lower()
                                for x in [
                                    "tạp chí", "tap chi", "hội thảo", "hoi thao", "sách", "sach"
                                ]
                            )
                        ),
                        None,
                    )
    
                    name_prod_col = next((c for c in df_temp_detail.columns if c.lower() in ["tên sản phẩm", "tên đề tài", "subject"]), None)
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
                    nam_hoc_col_target = next((c for c in df_temp_detail.columns if c.lower() in ["năm học", "year"]), "năm học")
    
                    group_keys_final = [nam_hoc_col_target, "Sản phẩm chuẩn hóa"]
                    if phan_loai_col:
                        group_keys_final.insert(0, phan_loai_col)
                    if loai_hd_col and loai_hd_col not in group_keys_final:
                        group_keys_final.insert(1, loai_hd_col)
    
                    agg_rules_detail = {
                        c_tiet_nckh: "first",
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
    
                    # --- LẤY SỐ LIỆU TỔNG QUAN TỪ DF_CLEAN_UNIFIED ĐÃ KHỬ TRÙNG LẶP ---
                    tot_tiet_nk = df_clean_unified[c_tiet_nckh].sum()
                    tot_sl_nk = len(df_clean_unified)
                    
                    if len(selected_report_years) == 1:
                        st.write(f"- **Tổng số sản phẩm NCKH toàn khoa:** {tot_sl_nk} sản phẩm")
                        st.write(f"- **Tổng số tiết NCKH toàn khoa:** {tot_tiet_nk:,.0f} tiết")
                    else:
                        label_nam_hoc_nk = f"({', '.join(selected_report_years)})" if selected_report_years else "(Tất cả các năm)"
                        st.write(f"- **Tổng số sản phẩm NCKH toàn khoa:** {tot_sl_nk} sản phẩm")
                        st.write(f"- **Tổng số tiết NCKH toàn khoa:** {tot_tiet_nk:,.0f} tiết")
                        
                        if nam_hoc_col_target in df_clean_unified.columns:
                            st.write("**Trong đó phân bổ theo năm học:**")
                            for yr_val, group_yr in df_clean_unified.groupby(nam_hoc_col_target):
                                tiet_yr_nk = group_yr[c_tiet_nckh].sum()
                                sl_yr_nk = len(group_yr)
                                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;+ Năm học **{yr_val}**: {sl_yr_nk} sản phẩm — {tiet_yr_nk:,.0f} tiết")

                    scope_option = st.radio(
                        "📌 Chọn phạm vi thống kê sản phẩm NCKH:",
                        options=["GV Khoa Tài chính thực hiện", "GV Khoa Tài chính làm Chủ nhiệm, Chủ biên đề tài, sách"],
                        horizontal=True,
                        key="radio_nckh_scope_selection"
                    )
                    st.caption("Với trường hợp GV Khoa Tài chính làm Chủ nhiệm, Chủ biên: thống kê số lượng sách, đề tài GV Khoa Tài chính khác vai trò được cộng vào mục Khác.")
    
                    def classify_nckh_match_table2(row):
                        loai_val = str(row.get(loai_hd_col, '')).strip() if loai_hd_col else ""
                        cap_val = str(row.get(cap_do_col, '')).strip() if cap_do_col else ""
                        pl1_val = str(row.get(phan_loai_col, '')).strip() if phan_loai_col else ""
                        effective_role_col = role_col_check if 'role_col_check' in locals() and role_col_check else next((c for c in row.index if any(x in str(c).lower() for x in ["vai trò", "role"])), None)
                        role_val = str(row.get(effective_role_col, '')).strip().lower() if effective_role_col else ""
                        
                        l_low = loai_val.lower()
                        c_low = cap_val.lower()
                        p_low = pl1_val.lower()
                        
                        is_leader = True
                        if scope_option == "GV Khoa Tài chính làm Chủ nhiệm, Chủ biên đề tài, sách":
                            leader_keywords = ["chủ nhiệm", "chủ biên"]
                            is_leader = any(kw in role_val for kw in leader_keywords)
    
                        if "đề tài" in l_low:
                            if not is_leader:
                                return "Khác"
                            if "bộ" in c_low or "bộ" in l_low:
                                return "Đề tài cấp Bộ"
                            elif "nhà nước" in c_low or "nhà nước" in l_low:
                                return "Đề tài cấp Nhà nước"
                            elif "tỉnh" in c_low or "thành phố" in c_low or "tỉnh" in l_low:
                                return "Đề tài cấp Tỉnh"
                            elif "quốc tế" in c_low or "quốc tế" in l_low:
                                return "Đề tài cấp quốc tế"
                            else:
                                return "Đề tài cấp cơ sở"
                                
                        if "bài báo" in l_low or "publication" in l_low or "journal" in l_low:
                            if "quốc tế" in c_low or "quốc tế" in l_low or "isi" in l_low or "scopus" in l_low:
                                return "Bài báo quốc tế"
                            else:
                                return "Bài báo trong nước"
                                
                        if "sách" in l_low or "biên soạn sách" in l_low or "giáo trình" in l_low or "tham khảo" in p_low or "chuyên khảo" in p_low:
                            if not is_leader:
                                return "Khác"
                            if "giáo trình" in p_low or "giáo trình" in l_low:
                                return "Sách giáo trình"
                            elif "chuyên khảo" in p_low:
                                return "Sách chuyên khảo"
                            else:
                                return "Sách tham khảo (TLTK)"
                                
                        if "sáng kiến" in l_low:
                            if not is_leader:
                                return "Khác"
                            if "cơ sở" in c_low or "trường" in c_low:
                                return "Sáng kiến (Cấp cơ sở)"
                            return "Sáng kiến"
                            
                        return "Khác"
    
                    df_scope_work = df_clean_unified.copy()
                    if not df_scope_work.empty:
                        df_scope_work["_Danh_muc_NCKH"] = df_scope_work.apply(classify_nckh_match_table2, axis=1)
    
                    if not df_scope_work.empty and nam_hoc_col_target in df_scope_work.columns:
                        df_matrix_final = df_scope_work.groupby(["_Danh_muc_NCKH", nam_hoc_col_target]).size().reset_index(name="Số lượng")
                        df_pivot = df_matrix_final.pivot_table(index="_Danh_muc_NCKH", columns=nam_hoc_col_target, values="Số lượng", aggfunc="sum").fillna(0)
                        
                        target_categories = [
                            "Đề tài cấp Nhà nước", "Đề tài cấp Bộ", "Đề tài cấp Tỉnh",
                            "Đề tài cấp quốc tế", "Đề tài cấp cơ sở", "Sáng kiến",
                            "Sáng kiến (Cấp cơ sở)", "Bài báo quốc tế", "Bài báo trong nước",
                            "Sách giáo trình", "Sách tham khảo (TLTK)", "Sách chuyên khảo", "Khác"
                        ]
                        
                        existing_cats = df_pivot.index.tolist()
                        all_cats_order = [c for c in target_categories if c in existing_cats] + [c for c in existing_cats if c not in target_categories]
                        
                        df_pivot = df_pivot.reindex(all_cats_order).fillna(0)
                        df_pivot["Tổng cộng"] = df_pivot.sum(axis=1)
                        df_pivot.loc["Tổng cộng chung"] = df_pivot.sum(axis=0)
    
                        df_pivot = df_pivot.astype(int)
                        st.dataframe(df_pivot, use_container_width=True)

                    # ==========================================
                    # 📈 BIỂU ĐỒ TRỰC QUAN ĐỘNG THEO DANH MỤC NCKH & NĂM HỌC
                    # ==========================================
                    st.markdown("##### 📈 Biểu đồ trực quan danh mục NCKH theo năm học")
                    
                    if not df_pivot.empty:
                        # Chuẩn bị dữ liệu từ bảng pivot NCKH (bỏ dòng tổng cộng chung nếu có để vẽ biểu đồ)
                        df_chart_source = df_pivot.drop(index=["Tổng cộng chung"], errors="ignore").copy()
                        if "Tổng cộng" in df_chart_source.columns:
                            df_chart_source = df_chart_source.drop(columns=["Tổng cộng"])

                        if not df_chart_source.empty:
                            # Lấy danh sách các danh mục (index của pivot) để làm tùy chọn selectedbox/multiselect
                            available_categories_chart = df_chart_source.index.tolist()

                            # Thanh chọn nhiều tiêu chí danh mục NCKH muốn vẽ biểu đồ
                            selected_chart_categories = st.multiselect(
                                "🎯 Chọn các danh mục NCKH hiển thị trên biểu đồ (Bỏ trống = Hiện toàn bộ):",
                                options=available_categories_chart,
                                default=available_categories_chart[:5] if len(available_categories_chart) >= 5 else available_categories_chart,
                                key="multiselect_nckh_chart_categories"
                            )

                            if selected_chart_categories:
                                df_chart_filtered = df_chart_source.loc[selected_chart_categories]
                            else:
                                df_chart_filtered = df_chart_source

                            if not df_chart_filtered.empty:
                                # Chuyển đổi dữ liệu về dạng dài (long format) hoặc transpose để vẽ biểu đồ cột theo năm học
                                # df_chart_filtered có index là Danh mục, columns là Năm học
                                df_plot_nckh_bar = df_chart_filtered.T  # Index lúc này là Năm học, columns là Danh mục

                                num_years_nckh = len(df_plot_nckh_bar)
                                dyn_w_nckh = min(max(7.0, num_years_nckh * 0.8), 12.0)
                                f_size_nckh = 8

                                fig_nk, ax_nk = plt.subplots(figsize=(dyn_w_nckh, 4.5))
                                df_plot_nckh_bar.plot(kind="bar", ax=ax_nk, width=0.8, colormap="tab20")

                                for p in ax_nk.patches:
                                    h = p.get_height()
                                    if h > 0:
                                        ax_nk.annotate(f"{int(h):,}",
                                                       (p.get_x() + p.get_width() / 2., h),
                                                       ha='center', va='bottom',
                                                       fontsize=f_size_nckh, fontweight='bold',
                                                       rotation=45 if num_years_nckh > 2 else 0,
                                                       xytext=(0, 2), textcoords='offset points')

                                ax_nk.set_xlabel("Năm học", fontsize=9)
                                ax_nk.set_ylabel("Số lượng sản phẩm", fontsize=9)
                                
                                scope_title_suffix = " (Thực hiện)" if scope_option == "GV Khoa Tài chính thực hiện" else " (Chủ nhiệm, Chủ biên)"
                                ax_nk.set_title(f"Biến động số lượng sản phẩm NCKH theo Năm học{scope_title_suffix}", fontsize=10, fontweight="bold")
                                
                                ax_nk.tick_params(axis="x", rotation=30)
                                ax_nk.legend(title="Danh mục NCKH", fontsize=8, title_fontsize=8, loc="upper left")
                                ax_nk.grid(axis="y", linestyle="--", alpha=0.5)

                                plt.tight_layout()
                                st.pyplot(fig_nk, bbox_inches="tight")
                                plt.close(fig_nk)
                            else:
                                st.warning("⚠️ Không có danh mục NCKH nào được chọn để vẽ biểu đồ.")
                        else:
                            st.warning("⚠️ Bảng dữ liệu thống kê danh mục NCKH hiện đang trống.")

                    # ==========================================
                    # 🔍 1. BẢNG CHI TIẾT NCKH TÙY CHỈNH
                    # ==========================================
                    st.markdown("##### 🔍 1. Bảng chi tiết NCKH tùy chỉnh theo tiêu chí")
    
                    cols_lower_all = {str(c).strip().lower(): c for c in df_clean_unified.columns}
                    col_ma_sp = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["mã sản phẩm", "ma san pham", "code"])), None)
                    col_tap_chi = next((c for c in df_clean_unified.columns if any(x in c.lower() for x in ["tạp chí", "tap chi", "hội thảo", "hoi thao", "sách", "sach"])), None)
                    col_phan_loai_2 = next((cols_lower_all[c] for c in cols_lower_all if "phân loại cấp 2" in c), None)
                    col_phan_loai_3 = next((cols_lower_all[c] for c in cols_lower_all if "phân loại cấp 3" in c), None)
                    col_isbn = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["isbn", "issn"])), None)
    
                    with st.expander("⚙️ **Chọn tiêu chí gom nhóm Bảng chi tiết (Bấm để mở/đóng)**", expanded=True):
                        col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
                        
                        with col_c1:
                            opt_y = st.checkbox("Năm học", value=True, key="chk_nckh_tk_year_v2")
                            opt_ma = st.checkbox("Mã sản phẩm", value=False, key="chk_nckh_tk_ma_v2")
                        with col_c2:
                            opt_loai = st.checkbox("Loại HĐ", value=True, key="chk_nckh_tk_loai_v2")
                            opt_issn = st.checkbox("Số ISBN / Số ISSN", value=False, key="chk_nckh_tk_issn_v2")
                        with col_c3:
                            opt_cap = st.checkbox("Cấp độ", value=True, key="chk_nckh_tk_cap_v2")
                            opt_role = st.checkbox("Vai trò", value=False, key="chk_nckh_tk_role_v2")
                        with col_c4:
                            opt_pl1 = st.checkbox("PL Cấp 1", value=False, key="chk_nckh_tk_pl1_v2")
                            opt_prod = st.checkbox("Tên sản phẩm", value=False, key="chk_nckh_tk_prod_v2")
                        with col_c5:
                            opt_pl2 = st.checkbox("PL Cấp 2", value=False, key="chk_nckh_tk_pl2_v2")
                            opt_pl3 = st.checkbox("PL Cấp 3", value=False, key="chk_nckh_tk_pl3_v2")
                        opt_tap = st.checkbox("Tên Tạp chí / Hội thảo, Sách", value=False, key="chk_nckh_tk_tap_v2")
    
                        group_detail_dynamic = []
                        if opt_y and nam_hoc_col_target in df_clean_unified.columns:
                            group_detail_dynamic.append(nam_hoc_col_target)
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
                            group_detail_dynamic = [nam_hoc_col_target]
    
                        agg_dyn_dict = {
                            c_tiet_nckh: ["sum", "count"],
                            "_full_name": lambda x: ", ".join(x.dropna().unique()),
                        }
                        if name_prod_col and name_prod_col in df_clean_unified.columns:
                            agg_dyn_dict[name_prod_col] = lambda x: " / ".join(x.dropna().unique())
                        if id_col_check and id_col_check in df_clean_unified.columns:
                            agg_dyn_dict[id_col_check] = lambda x: " / ".join(x.dropna().unique())
                        if role_col_check and role_col_check not in group_detail_dynamic:
                            agg_dyn_dict[role_col_check] = lambda x: " & ".join(x.dropna().unique())
    
                        group_detail_dynamic = list(dict.fromkeys(group_detail_dynamic))
                        safe_agg_dyn_dict = {k: v for k, v in agg_dyn_dict.items() if k not in group_detail_dynamic}
    
                        df_nckh_detail = df_clean_unified.groupby(group_detail_dynamic, dropna=False).agg(safe_agg_dyn_dict).reset_index()
                        df_nckh_detail.columns = [col[0] if col[1] == "" else f"{col[0]}_{col[1]}" for col in df_nckh_detail.columns]
    
                        rename_nckh_dict = {
                            f"{c_tiet_nckh}_sum": "Tổng số tiết",
                            f"{c_tiet_nckh}_count": "Số lượng",
                            "_full_name": "Danh sách thành viên"
                        }
                        if role_col_check:
                            rename_nckh_dict[role_col_check] = "Các vai trò"
    
                        df_nckh_detail = df_nckh_detail.rename(columns=rename_nckh_dict)
                        
                        for col_drop in ["_clean_prod_name", "_clean_id", "_clean_key", "Sản phẩm chuẩn hóa", "_source_table", "_Danh_muc_NCKH"]:
                            if col_drop in df_nckh_detail.columns:
                                df_nckh_detail = df_nckh_detail.drop(columns=[col_drop])
    
                        front_cols = [c for c in group_detail_dynamic if c in df_nckh_detail.columns]
                        middle_cols = [c for c in ["Số lượng", "Tổng số tiết"] if c in df_nckh_detail.columns]
                        end_cols = [c for c in df_nckh_detail.columns if c not in front_cols + middle_cols]
                        
                        df_nckh_detail = df_nckh_detail[front_cols + middle_cols + end_cols]
    
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
                    # 📈 2. THỐNG KÊ TỔ HỢP VÀ VẼ BIỂU ĐỒ ĐỘNG
                    # ==========================================
                    #st.markdown("##### 📈 2. Thống kê số lượng & tổng số tiết")
                    
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
                    if opt_y and nam_hoc_col_target in df_clean_unified.columns:
                        group_stat_keys.append(nam_hoc_col_target)
    
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
                            Số_lượng=(c_tiet_nckh, "count"),
                            Tổng_số_tiết=(c_tiet_nckh, "sum"),
                            Thành_viên=("_full_name", lambda x: ", ".join(x.dropna().unique()))
                        ).reset_index()
    
                        rename_col_dict = {
                            nam_hoc_col_target: "Năm học",
                            "_Tổ_hợp_tiêu_chí": "Tổ hợp tiêu chí (" + " + ".join(active_stat_names) + ")" if active_stat_names else "Nội dung",
                            "Số_lượng": "Số lượng",
                            "Tổng_số_tiết": "Số tiết"
                        }
                        df_grouped_stat = df_grouped_stat.rename(columns=rename_col_dict)
    
                        final_rows = []
                        has_year_col = "Năm học" in df_grouped_stat.columns
    
                        if has_year_col:
                            years = df_grouped_stat["Năm học"].unique()
                            for yr in sorted(years):
                                df_yr = df_grouped_stat[df_grouped_stat["Năm học"] == yr]
                                for _, row in df_yr.iterrows():
                                    final_rows.append(row.to_dict())
                                
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
    
                        total_all_row = {col: "" for col in df_grouped_stat.columns}
                        first_col = df_grouped_stat.columns[0]
                        total_all_row[first_col] = "**Tổng cộng chung**" if not has_year_col else "**Tổng cộng tất cả**"
                        total_all_row["Số lượng"] = df_grouped_stat["Số lượng"].sum()
                        total_all_row["Số tiết"] = df_grouped_stat["Số tiết"].sum()
                        final_rows.append(total_all_row)
    
                        df_final_stat_display = pd.DataFrame(final_rows)
    
                        #with st.expander("⚙️ **Bảng tổng hợp số lượng & số tiết (Bấm để mở/đóng)**", expanded=True):
                            #st.info(f"💡 Đang thống kê theo các tiêu chí đã chọn: **{' + '.join(active_stat_names)}**")
                            #st.dataframe(df_final_stat_display, use_container_width=True)
    
                        # ==========================================
                        # 📊 3. BIỂU ĐỒ TRỰC QUAN ĐỘNG
                        # ==========================================
                        if not df_grouped_stat.empty:
                            st.markdown("##### 📊 2. Biểu đồ trực quan động NCKH theo tiêu chí bảng 1")
                            
                            df_plot_nckh = df_grouped_stat.copy()
                            if "Năm học" in df_plot_nckh.columns:
                                df_plot_nckh = df_plot_nckh[~df_plot_nckh["Năm học"].astype(str).str.contains("Tổng cộng", na=False)]
    
                            col_tinh_chi_name = [c for c in df_plot_nckh.columns if c not in ["Năm học", "Số lượng", "Số tiết", "Thành_viên"]][0]
                            display_name_chart = "Tổ hợp tiêu chí" if not active_stat_names else " + ".join(active_stat_names)
    
                            if not df_plot_nckh.empty:
                                # Lấy danh sách toàn bộ các giá trị duy nhất từ cột tiêu chí
                                unique_vals_nckh = sorted(df_plot_nckh[col_tinh_chi_name].astype(str).unique())
                                
                                # Mặc định chọn sẵn 2 giá trị đầu tiên (nếu có từ 2 giá trị trở lên, ngược lại lấy tất cả)
                                default_selected_nckh = unique_vals_nckh[:2] if len(unique_vals_nckh) >= 2 else unique_vals_nckh
    
                                selected_vals_nckh = st.multiselect(
                                    f"🎯 Lọc {display_name_chart} hiển thị trên biểu đồ (Bỏ trống = Hiện toàn bộ):",
                                    options=unique_vals_nckh,
                                    default=default_selected_nckh,  # 👈 Thêm tham số này để mặc định chọn 2 giá trị đầu
                                    key="filter_nckh_toankhoa_dynamic_stat_v3"
                                )
                                
                                if selected_vals_nckh:
                                    df_plot_nckh = df_plot_nckh[df_plot_nckh[col_tinh_chi_name].astype(str).isin(selected_vals_nckh)]
    
                                if not df_plot_nckh.empty:
                                    col_chart1, col_chart2 = st.columns(2)
                                    
                                    has_year_nckh = "Năm học" in df_plot_nckh.columns and opt_y
                                    
                                    if has_year_nckh:
                                        df_pivot_qty = df_plot_nckh.pivot_table(index=col_tinh_chi_name, columns="Năm học", values="Số lượng", aggfunc="sum").fillna(0)
                                        df_pivot_tiet = df_plot_nckh.pivot_table(index=col_tinh_chi_name, columns="Năm học", values="Số tiết", aggfunc="sum").fillna(0)
                                        is_grouped_years = True
                                    else:
                                        df_pivot_qty = df_plot_nckh.groupby(col_tinh_chi_name)[["Số lượng"]].sum()
                                        df_pivot_tiet = df_plot_nckh.groupby(col_tinh_chi_name)[["Số tiết"]].sum()
                                        is_grouped_years = False
                                    
                                    unique_labels = df_pivot_qty.index.astype(str).tolist()
                                    needs_mapping = any(len(lbl) > 15 for lbl in unique_labels)
                                    
                                    label_mapping = {}
                                    if needs_mapping:
                                        label_mapping = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels)}
                                        df_pivot_qty.index = df_pivot_qty.index.map(label_mapping)
                                        df_pivot_tiet.index = df_pivot_tiet.index.map(label_mapping)
                                    
                                    num_bars_nckh = len(df_pivot_qty)
                                    dyn_w = max(7.0, num_bars_nckh * 0.6)
                                    f_size = 6 if num_bars_nckh > 15 else (7 if num_bars_nckh > 10 else 8)
                                    
                                    # --- BIỂU ĐỒ SỐ LƯỢNG ---
                                    with col_chart1:
                                        fig1, ax1 = plt.subplots(figsize=(dyn_w, 4.0))
                                        df_pivot_qty.plot(kind="bar", stacked=False, ax=ax1, width=0.8, colormap="tab20")
                                        
                                        for p in ax1.patches:
                                            h = p.get_height()
                                            if h > 0:
                                                ax1.annotate(f"{int(h):,}",
                                                               (p.get_x() + p.get_width() / 2., h),
                                                               ha='center', va='bottom',
                                                               fontsize=f_size, fontweight='bold',
                                                               rotation=45 if num_bars_nckh > 2 else 0,
                                                               xytext=(0, 2), textcoords='offset points')
                                                
                                        ax1.set_xlabel("Ký hiệu" if needs_mapping else display_name_chart, fontsize=9)
                                        ax1.set_ylabel("Số lượng sản phẩm", fontsize=9)
                                        ax1.set_title(f"So sánh Số lượng theo {display_name_chart}", fontsize=10, fontweight="bold")
                                        ax1.tick_params(axis="x", rotation=45 if num_bars_nckh > 4 else 0)
                                        if is_grouped_years:
                                            ax1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax1.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig1, bbox_inches="tight")
                                    
                                    # --- BIỂU ĐỒ SỐ TIẾT ---
                                    with col_chart2:
                                        fig2, ax2 = plt.subplots(figsize=(dyn_w, 4.0))
                                        df_pivot_tiet.plot(kind="bar", stacked=False, ax=ax2, width=0.8, colormap="Accent")
                                        
                                        for p in ax2.patches:
                                            h = p.get_height()
                                            if h > 0:
                                                ax2.annotate(f"{int(h):,}",
                                                               (p.get_x() + p.get_width() / 2., h),
                                                               ha='center', va='bottom',
                                                               fontsize=f_size, fontweight='bold',
                                                               rotation=45 if num_bars_nckh > 2 else 0,
                                                               xytext=(0, 2), textcoords='offset points')
                                                
                                        ax2.set_xlabel("Ký hiệu" if needs_mapping else display_name_chart, fontsize=9)
                                        ax2.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
                                        ax2.set_title(f"So sánh Số tiết theo {display_name_chart}", fontsize=10, fontweight="bold")
                                        ax2.tick_params(axis="x", rotation=45 if num_bars_nckh > 4 else 0)
                                        if is_grouped_years:
                                            ax2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax2.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig2, bbox_inches="tight")
                                    
                                    if needs_mapping:
                                        st.markdown(f"**📝 Chú thích ký hiệu trục hoành cho ({display_name_chart}):**")
                                        with st.expander("📅 **(Bấm để xem chú thích chi tiết)**", expanded=False):
                                            note_df = pd.DataFrame(list(label_mapping.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                            st.dataframe(note_df, use_container_width=True)

                        # ==========================================
                        # 📈 3. BIỂU ĐỒ TRỰC QUAN ĐỘNG NCKH TOÀN KHOA
                        # ==========================================
                        if not df_grouped_stat.empty:
                         
                            # 📊 3.1. BIỂU ĐỒ BÓC TÁCH CHI TIẾT SO SÁNH THEO CÁC NĂM HỌC
                            has_year_selected = opt_y and nam_hoc_col_target in df_clean_unified.columns and len(selected_report_years) != 1
                            other_criteria_cols = [name for is_chk, _, name in stat_options_mapping if is_chk and name != "Năm học"]
                            
                            if has_year_selected and other_criteria_cols and 'df_plot_data' in locals():
                                st.markdown("#### 🌟 3.1 Biểu đồ bóc tách chi tiết so sánh theo Các năm học")
                                
                                for other_col in other_criteria_cols:
                                    st.markdown(f"##### 📌 Phân tích tiêu chí **{other_col}** so sánh theo **Năm học**")
                                    
                                    df_other_filtered = df_plot_data.copy() if 'df_plot_data' in locals() else df_grouped_stat.copy()
                                    if other_col in ["Tên sản phẩm", "Tên Tạp chí / Hội thảo, Sách", "Loại HĐ", "Cấp độ"]:
                                        unique_vals_other = sorted(df_other_filtered[other_col].astype(str).unique()) if other_col in df_other_filtered.columns else []
                                        if unique_vals_other:
                                            selected_vals_other = st.multiselect(
                                                f"🎯 Lọc {other_col} hiển thị trên biểu đồ so sánh (Bỏ trống = Hiện toàn bộ):",
                                                options=unique_vals_other,
                                                key=f"filter_other_nckh_{other_col}"
                                            )
                                            if selected_vals_other:
                                                df_other_filtered = df_other_filtered[df_other_filtered[other_col].astype(str).isin(selected_vals_other)]
                                    
                                    if df_other_filtered.empty:
                                        st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho tiêu chí **{other_col}**.")
                                        continue
                                    
                                    plot_yr_base = other_col if other_col in df_other_filtered.columns else col_tinh_chi_name
                                    
                                    df_pivot_tiet_yr = df_other_filtered.pivot_table(index=plot_yr_base, columns="Năm học", values="Số tiết", aggfunc="sum").fillna(0)
                                    df_pivot_qty_yr = df_other_filtered.pivot_table(index=plot_yr_base, columns="Năm học", values="Số lượng", aggfunc="sum").fillna(0)
                                    
                                    unique_labels_yr = df_pivot_tiet_yr.index.astype(str).tolist()
                                    needs_mapping_yr = any(len(lbl) > 15 for lbl in unique_labels_yr)
                                    
                                    label_mapping_yr = {}
                                    if needs_mapping_yr:
                                        label_mapping_yr = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels_yr)}
                                        df_pivot_tiet_yr.index = df_pivot_tiet_yr.index.map(label_mapping_yr)
                                        df_pivot_qty_yr.index = df_pivot_qty_yr.index.map(label_mapping_yr)
                                    
                                    num_bars_yr = len(df_pivot_tiet_yr)
                                    dyn_w_yr = max(7.0, num_bars_yr * 0.6)
                                    f_size_yr = 6 if num_bars_yr > 15 else (7 if num_bars_yr > 10 else 8)
                                    
                                    col_y1, col_y2 = st.columns(2)
                                    
                                    with col_y1:
                                        fig_y1, ax_y1 = plt.subplots(figsize=(dyn_w_yr, 4.0))
                                        df_pivot_tiet_yr.plot(kind="bar", ax=ax_y1, width=0.8, colormap="tab20")
                                        
                                        for p in ax_y1.patches:
                                            h = p.get_height()
                                            if h > 0:
                                                ax_y1.annotate(f"{int(h):,}",
                                                               (p.get_x() + p.get_width() / 2., h),
                                                               ha='center', va='bottom',
                                                               fontsize=f_size_yr, fontweight='bold',
                                                               rotation=45 if num_bars_yr > 2 else 0,
                                                               xytext=(0, 2), textcoords='offset points')
                                        
                                        ax_y1.set_xlabel("Ký hiệu" if needs_mapping_yr else other_col, fontsize=9)
                                        ax_y1.set_ylabel("Tổng số tiết", fontsize=9)
                                        ax_y1.set_title(f"So sánh Tổng số tiết - {other_col} qua các Năm học", fontsize=10, fontweight="bold")
                                        ax_y1.tick_params(axis="x", rotation=45 if num_bars_yr > 4 else 0)
                                        ax_y1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax_y1.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig_y1, bbox_inches="tight")
                                        plt.close(fig_y1)
                                    
                                    with col_y2:
                                        fig_y2, ax_y2 = plt.subplots(figsize=(dyn_w_yr, 4.0))
                                        df_pivot_qty_yr.plot(kind="bar", ax=ax_y2, width=0.8, colormap="Accent")
                                        
                                        for p in ax_y2.patches:
                                            h = p.get_height()
                                            if h > 0:
                                                ax_y2.annotate(f"{int(h):,}",
                                                               (p.get_x() + p.get_width() / 2., h),
                                                               ha='center', va='bottom',
                                                               fontsize=f_size_yr, fontweight='bold',
                                                               rotation=45 if num_bars_yr > 2 else 0,
                                                               xytext=(0, 2), textcoords='offset points')
                                        
                                        ax_y2.set_xlabel("Ký hiệu" if needs_mapping_yr else other_col, fontsize=9)
                                        ax_y2.set_ylabel("Số lượng sản phẩm", fontsize=9)
                                        ax_y2.set_title(f"So sánh Số lượng - {other_col} qua các Năm học", fontsize=10, fontweight="bold")
                                        ax_y2.tick_params(axis="x", rotation=45 if num_bars_yr > 4 else 0)
                                        ax_y2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax_y2.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig_y2, bbox_inches="tight")
                                        plt.close(fig_y2)
                                    
                                    if needs_mapping_yr:
                                        st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({other_col}):**")
                                        with st.expander(f"📅 **(Bấm để xem chú thích chi tiết)**", expanded=False):
                                            note_df_yr = pd.DataFrame(list(label_mapping_yr.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                            st.dataframe(note_df_yr, use_container_width=True)
    
                elif report_level == "(2) Từng bộ môn":
                    st.markdown("#### 🏢 Báo cáo tổng hợp NCKH theo từng Bộ môn")
                    
                    # 🔒 Nếu là Lãnh đạo bộ môn, tự động khóa chặt vào bộ môn của họ, không cho chọn bộ môn khác
                    if "lãnh đạo bộ môn" in pos:
                        selected_bm_nk = u_faculty if u_faculty else "BM TCDN"
                        st.info(f"📌 Đang hiển thị dữ liệu của Bộ môn do bạn quản lý: **{selected_bm_nk}**")
                    else:
                        bms = ["BM TCDN", "BM ĐTTC", "BM QFRM"]
                        selected_bm_nk = st.radio(
                            "📌 Chọn bộ môn muốn xem báo cáo NCKH:",
                            options=bms,
                            horizontal=True,
                            key="radio_select_single_bm_nckh_tab4"
                        )
                    
                    st.markdown(f"##### 📌 Bộ môn quản lý: **{selected_bm_nk}**")
    
                    gv_bm_ids = []
                    if not user_df_raw.empty:
                        gv_bm_ids = user_df_raw[user_df_raw["normalized_faculty"] == selected_bm_nk][u_id_col].apply(normalize_id).tolist()
    
                    if c_id_nckh and gv_bm_ids and not df_nckh_filtered.empty:
                        df_bm_nc = df_nckh_filtered[df_nckh_filtered[c_id_nckh].apply(normalize_id).isin(gv_bm_ids)].copy()
                        tiet_bm = df_bm_nc[c_tiet_nckh].sum()
                        sl_bm = len(df_bm_nc)
                        
                        st.write(f"- **Tổng số sản phẩm NCKH thực hiện:** {sl_bm} sản phẩm")
                        st.write(f"- **Tổng số tiết NCKH thực hiện:** {tiet_bm:,.0f} tiết")
                        
                        if "năm học" in df_bm_nc.columns:
                            st.write("  - **Trong đó phân bổ theo năm học:**")
                            for yr_val, group_yr in df_bm_nc.groupby("năm học"):
                                tiet_yr_bm = group_yr[c_tiet_nckh].sum()
                                sl_yr_bm = len(group_yr)
                                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;+ Năm học **{yr_val}**: {sl_yr_bm} sản phẩm — {tiet_yr_bm:,.0f} tiết")
    
                        if not df_bm_nc.empty:
                            # 📊 THỐNG KÊ SỐ LƯỢNG THEO LOẠI HOẠT ĐỘNG (CẤP BỘ MÔN)
                            sub_df_bm = df_bm_nc.copy()
                            sub_df_bm.columns = [str(c).strip().lower() for c in sub_df_bm.columns]
                            
                            col_loai_hd_bm = next((c for c in sub_df_bm.columns if "loại" in c or "hoạt động" in c), None)
                            
                            if col_loai_hd_bm:
                                df_count_loai_bm = sub_df_bm.groupby(col_loai_hd_bm, as_index=False).size()
                                
                                st.markdown("- **Thống kê số lượng theo loại hoạt động:**")
                                summary_str_list_bm = []
                                for _, r_loai in df_count_loai_bm.iterrows():
                                    ten_loai = r_loai[col_loai_hd_bm]
                                    so_luong = int(r_loai['size'])
                                    sl_str = f"{so_luong:02d}"
                                    summary_str_list_bm.append(f"&nbsp;&nbsp;&nbsp;&nbsp;• **{ten_loai}**: {sl_str}")
                                
                                st.markdown("<br>".join(summary_str_list_bm), unsafe_allow_html=True)
                            
                            st.markdown(f"##### 📋 Bảng chi tiết sản phẩm NCKH của bộ môn {selected_bm_nk}")
                            st.dataframe(df_bm_nc, use_container_width=True)
                    else:
                        st.warning(f"Chưa có dữ liệu NCKH do bộ môn {selected_bm_nk} thực hiện trong năm học đã chọn.")
    
                elif report_level == "(3) Từng giảng viên":
                    st.markdown("#### 👤 Thống kê NCKH theo từng Giảng viên & Danh sách sản phẩm")
                    if c_id_nckh and not df_nckh_filtered.empty:
                        df_nckh_filtered["_id_norm"] = df_nckh_filtered[c_id_nckh].apply(normalize_id)
                        
                        gv_nckh_rows = []
                        for gvid in [x for x in df_nckh_filtered["_id_norm"].unique() if x != ""]:
                            sub_nc = df_nckh_filtered[df_nckh_filtered["_id_norm"] == str(gvid)]
                            sur, nam = "", ""
                            if not user_df_raw.empty:
                                matched_u = user_df_raw[user_df_raw[u_id_col].apply(normalize_id) == str(gvid)]
                                if not matched_u.empty:
                                    sur = matched_u.iloc[0].get(u_sur_col, "")
                                    nam = matched_u.iloc[0].get(u_name_col, "")
    
                            full_gv_name = f"{sur} {nam}".strip() if (sur or nam) else gvid
                            danh_sach_sp = ", ".join(sub_nc[c_name_prod].dropna().unique().astype(str))
                            
                            gv_nckh_rows.append({
                                "full_name": full_gv_name,
                                "id": gvid,
                                "Tổng số sản phẩm NCKH": len(sub_nc),
                                "Danh sách sản phẩm NCKH": danh_sach_sp,
                                "Tổng số tiết thực hiện": sub_nc[c_tiet_nckh].sum(),
                                "sub_df": sub_nc
                            })
    
                        if gv_nckh_rows:
                            # Khai báo chuẩn list_all_gv cho phần NCKH
                            list_all_gv = sorted([item["full_name"] for item in gv_nckh_rows])
                            
                            # 🔒 PHÂN QUYỀN CHUẨN XÁC CHO NCKH:
                            if "admin" in pos or "lãnh đạo khoa" in pos or "quản lý khoa" in pos:
                                allowed_gvs = list_all_gv
                            elif "lãnh đạo bộ môn" in pos:
                                bm_name = u_faculty.strip().lower()
                                if not user_df_raw.empty and bm_name:
                                    bm_gv_ids = user_df_raw[user_df_raw["normalized_faculty"].str.lower().str.contains(bm_name)][u_id_col].apply(normalize_id).tolist()
                                    sub_bm_gv_rows = [item for item in gv_nckh_rows if str(item["id"]) in bm_gv_ids]
                                    allowed_gvs = sorted([item["full_name"] for item in sub_bm_gv_rows])
                                    if not allowed_gvs:
                                        allowed_gvs = list_all_gv
                                else:
                                    allowed_gvs = list_all_gv
                            else:
                                my_name = current_user['fullname'].lower()
                                allowed_gvs = [g for g in list_all_gv if my_name in g.lower() or g.lower() in my_name]
                                if not allowed_gvs:
                                    allowed_gvs = [current_user['fullname']]

                            selected_gv_nk = st.selectbox(
                                "📌 Chọn giảng viên muốn xem báo cáo NCKH:",
                                options=allowed_gvs,
                                key="selectbox_select_single_gv_nckh_tab4"
                            )
                            
                            st.markdown(f"##### 👤 Đang xem báo cáo NCKH của Giảng viên: **{selected_gv_nk}**")
                            
                            selected_info = next((item for item in gv_nckh_rows if item["full_name"] == selected_gv_nk), None)
                            if selected_info:
                                st.write(f"- **Tổng số sản phẩm NCKH:** {selected_info['Tổng số sản phẩm NCKH']} sản phẩm")
                                st.write(f"- **Tổng số tiết NCKH thực hiện:** {selected_info['Tổng số tiết thực hiện']:,.0f} tiết")
                                
                                # 📊 TỔNG HỢP VÀ ĐẾM SỐ LƯỢNG THEO CỘT LOẠI HOẠT ĐỘNG
                                sub_df_gv = selected_info["sub_df"].copy()
                                sub_df_gv.columns = [str(c).strip().lower() for c in sub_df_gv.columns]
                                
                                col_loai_hd = next((c for c in sub_df_gv.columns if "loại" in c or "hoạt động" in c), None)
                                
                                if col_loai_hd:
                                    df_count_loai = sub_df_gv.groupby(col_loai_hd, as_index=False).size()
                                    
                                    st.markdown("- **Thống kê số lượng theo loại hoạt động:**")
                                    summary_str_list = []
                                    for _, r_loai in df_count_loai.iterrows():
                                        ten_loai = r_loai[col_loai_hd]
                                        so_luong = int(r_loai['size'])
                                        sl_str = f"{so_luong:02d}"
                                        summary_str_list.append(f"&nbsp;&nbsp;&nbsp;&nbsp;• **{ten_loai}**: {sl_str}")
                                    
                                    st.markdown("<br>".join(summary_str_list), unsafe_allow_html=True)
                                else:
                                    st.markdown(f"- **Danh sách các sản phẩm:** {selected_info['Danh sách sản phẩm NCKH']}")
                                
                                st.markdown("##### 📋 Bảng chi tiết sản phẩm NCKH theo năm học")
                                st.dataframe(selected_info["sub_df"], use_container_width=True)

        # ==========================================
        # 3. BÁO CÁO MẢNG OTHER (CÔNG TÁC KHÁC)
        # ==========================================
        elif "Báo cáo Công tác khác (Other)" in report_category:
            st.markdown("### 📌 CHI TIẾT BÁO CÁO CÔNG TÁC KHÁC (OTHER)")
            if df_other_full is None or df_other_full.empty:
                st.warning("⚠️ Không có dữ liệu công tác khác.")
            else:
                df_other_filtered = apply_year_filter(df_other_full)
                df_other_filtered.columns = [str(c).strip().lower() for c in df_other_filtered.columns]
    
                c_tiet_oth = next((c for c in df_other_filtered.columns if any(x in c for x in ["tiết", "period", "sỐ tiết kê khai"])), df_other_filtered.columns[-1])
                df_other_filtered[c_tiet_oth] = pd.to_numeric(df_other_filtered[c_tiet_oth], errors="coerce").fillna(0)
    
                c_loai_oth = next((c for c in df_other_filtered.columns if "loại" in c), None)
                c_cap_oth = next((c for c in df_other_filtered.columns if "cấp độ" in c), None)
                c_pl1_oth = next((c for c in df_other_filtered.columns if "phân loại cấp 1" in c), None)
                c_id_oth = next((c for c in df_other_filtered.columns if c in ["id", "mã", "code", "gv"]), None)
                c_name_oth = next((c for c in df_other_filtered.columns if "tên sản phẩm" in c or "tên công việc" in c or "subject" in c), df_other_filtered.columns[0])
    
                if report_level == "(1) Toàn khoa":
                    st.markdown("#### 🌐 Tổng số tiết Công tác khác toàn khoa")
                    tot_tiet_o = df_other_filtered[c_tiet_oth].sum()
                    st.metric("Tổng số tiết Công tác khác Toàn khoa", f"{tot_tiet_o:,.0f} tiết")
    
                    group_stat_oth = [c for c in [c_loai_oth, c_cap_oth, c_pl1_oth] if c]
                    if group_stat_oth:
                        df_stat_oth = df_other_filtered.groupby(group_stat_oth).agg(
                            Số_lượng=(c_tiet_oth, "count"),
                            Tổng_số_tiết=(c_tiet_oth, "sum")
                        ).reset_index()
                        st.markdown("##### 📌 Thống kê theo Loại hoạt động + Cấp độ + Phân loại cấp 1 (Other)")
                        st.dataframe(df_stat_oth, use_container_width=True, hide_index=True)
    
                elif report_level == "(2) Từng bộ môn":
                    st.markdown("#### 🏢 Thống kê Công tác khác theo từng Bộ môn")
                    bms = ["BM TCDN", "BM ĐTTC", "BM QFRM"]
                    for bm in bms:
                        st.markdown(f"##### 📌 Bộ môn: **{bm}**")
                        gv_bm_ids = []
                        if not user_df_raw.empty:
                            gv_bm_ids = user_df_raw[user_df_raw["normalized_faculty"] == bm][u_id_col].apply(normalize_id).tolist()
                        if c_id_oth and gv_bm_ids and not df_other_filtered.empty:
                            df_bm_ot = df_other_filtered[df_other_filtered[c_id_oth].apply(normalize_id).isin(gv_bm_ids)]
                            tiet_bm_o = df_bm_ot[c_tiet_oth].sum()
                            st.write(f"- **Tổng số tiết Công tác khác:** {tiet_bm_o:,.0f} tiết")
                        st.markdown("---")
    
                elif report_level == "(3) Từng giảng viên":
                    st.markdown("#### 👤 Thống kê Công tác khác theo từng Giảng viên & Danh sách công việc")
                    if c_id_oth and not df_other_filtered.empty:
                        df_other_filtered["_id_norm"] = df_other_filtered[c_id_oth].apply(normalize_id)
                        gv_oth_rows = []
                        for gvid in [x for x in df_other_filtered["_id_norm"].unique() if x != ""]:
                            sub_ot = df_other_filtered[df_other_filtered["_id_norm"] == str(gvid)]
                            sur, nam = "", ""
                            if not user_df_raw.empty:
                                matched_u = user_df_raw[user_df_raw[u_id_col].apply(normalize_id) == str(gvid)]
                                if not matched_u.empty:
                                    sur = matched_u.iloc[0].get(u_sur_col, "")
                                    nam = matched_u.iloc[0].get(u_name_col, "")
    
                            danh_sach_cv = ", ".join(sub_ot[c_name_oth].dropna().unique().astype(str))
                            gv_oth_rows.append({
                                "id": gvid,
                                "surname": sur,
                                "name": nam,
                                "Tổng số công việc": len(sub_ot),
                                "Danh sách công việc": danh_sach_cv,
                                "Tổng số tiết thực hiện": sub_ot[c_tiet_oth].sum()
                            })
                        st.dataframe(pd.DataFrame(gv_oth_rows), use_container_width=True)

    # ==========================================================
    # PHÂN HỆ 2: QUẢN LÝ SV
    # ==========================================================
    elif dashboard_mode == "🎓 Quản lý SV":
        st.markdown("#### 📊 BÁO CÁO THỐNG KÊ SINH VIÊN TỐT NGHIỆP")
        st.caption("💡 Thống kê tổng quan tình trạng sinh viên, xếp loại tốt nghiệp, phân bố theo chuyên ngành, lớp và năm học dựa trên Ngày ký QĐ TN.")

        if filtered_df_sv is None or filtered_df_sv.empty:
            st.warning("⚠️ Không có dữ liệu sinh viên hoặc bạn không có quyền xem dữ liệu này.")
        else:
            df_sv_tab1 = filtered_df_sv.copy()
            df_sv_tab1.columns = [str(c).strip() for c in df_sv_tab1.columns]

            c_so_qd = next((c for c in df_sv_tab1.columns if "số qđ tn" in c.lower() or "số qđ" in c.lower()), df_sv_tab1.columns[0])
            c_ngay_qd = next((c for c in df_sv_tab1.columns if "ngày ký qđ" in c.lower() or "ngày ký" in c.lower()), None)
            c_mssv = next((c for c in df_sv_tab1.columns if "mssv" in c or "mã sinh viên" in c.lower()), df_sv_tab1.columns[1])
            c_hoten = next((c for c in df_sv_tab1.columns if "họ tên" in c.lower() or "hoten" in c.lower()), df_sv_tab1.columns[0])
            c_tinhtrang = next((c for c in df_sv_tab1.columns if "tình trạng" in c.lower()), None)
            c_xeploai = next((c for c in df_sv_tab1.columns if "xếp loại tn" in c.lower() or "xếp loại" in c.lower()), None)
            c_chuyennganh = next((c for c in df_sv_tab1.columns if "chuyên ngành" in c.lower()), None)
            c_lopsv = next((c for c in df_sv_tab1.columns if "lớp sv" in c.lower() or "lớp" in c.lower()), None)
            c_khoahoc = next((c for c in df_sv_tab1.columns if "khóa học" in c.lower() or "khóa" in c.lower()), None)
            c_donvi = next((c for c in df_sv_tab1.columns if "đơn vị" in c.lower()), None)
            c_nganh = next((c for c in df_sv_tab1.columns if "ngành" in c.lower()), None)

            if c_ngay_qd:
                df_sv_tab1["Năm học"] = df_sv_tab1[c_ngay_qd].apply(quy_doi_nam_hoc_sv)
            else:
                df_sv_tab1["Năm học"] = "Chưa xác định"

            if "admin" in pos or "lãnh đạo khoa" in pos or "quản lý khoa" in pos:
                report_level_sv = st.radio(
                    "🎯 Chọn cấp độ báo cáo sinh viên:",
                    options=[
                        "(1) Toàn khoa", 
                        "(2) Từng chuyên ngành", 
                        "(3) Từng lớp"
                    ],
                    horizontal=False,
                    key="radio_report_level_sv_qlsv"
                )
            elif "lãnh đạo bộ môn" in pos:
                report_level_sv = st.radio(
                    "🎯 Chọn cấp độ báo cáo sinh viên:",
                    options=[
                        "(2) Từng chuyên ngành", 
                        "(3) Từng lớp"
                    ],
                    horizontal=False,
                    key="radio_report_level_sv_qlsv"
                )
                st.info(f"📌 Chế độ hiển thị sinh viên theo bộ môn phụ trách: **{u_faculty}**")
            else:
                report_level = "(3) Từng lớp"
                st.info(f"📌 Chế độ hiển thị cá nhân cho Giảng viên: **{current_user['fullname']}**")

            all_sv_years = sorted(df_sv_tab1["Năm học"].dropna().unique().tolist(), reverse=True)
            selected_sv_years = st.multiselect(
                "📅 Lọc theo năm học (Dựa theo Ngày ký QĐ TN) — Bỏ trống = Lấy tất cả:",
                options=all_sv_years,
                default=all_sv_years[:3] if len(all_sv_years) >= 3 else all_sv_years,
                key="multiselect_sv_dash_years_qlsv"
            )

            def apply_sv_year_filter(df):
                if df is None or df.empty or not selected_sv_years:
                    return df
                if "Năm học" in df.columns:
                    return df[df["Năm học"].isin(selected_sv_years)]
                return df

            df_sv_filtered_base = apply_sv_year_filter(df_sv_tab1)
            target_col_cn = c_chuyennganh if c_chuyennganh and c_chuyennganh in df_sv_tab1.columns else c_donvi

            if report_level_sv == "(1) Toàn khoa":
                df_sv_filtered = df_sv_filtered_base.copy()
                st.markdown("#### 🌐 Báo cáo tổng hợp (Sinh viên tốt nghiệp)")

            elif report_level_sv == "(2) Từng chuyên ngành":
                if target_col_cn:
                    list_cn = sorted(df_sv_filtered_base[target_col_cn].dropna().unique().tolist())
                    selected_cn = st.selectbox("📌 Chọn Chuyên ngành muốn xem báo cáo:", options=list_cn, key="sb_sel_cn_qlsv")
                    df_sv_filtered = df_sv_filtered_base[df_sv_filtered_base[target_col_cn] == selected_cn].copy()
                    st.markdown(f"#### 🏢 Báo cáo tổng hợp theo Chuyên ngành: **{selected_cn}**")
                else:
                    df_sv_filtered = df_sv_filtered_base.copy()
                    st.warning("⚠️ Không tìm thấy cột chuyên ngành trong dữ liệu sinh viên.")

            elif report_level_sv == "(3) Từng lớp":
                if c_lopsv and c_lopsv in df_sv_filtered_base.columns:
                    list_lop = sorted(df_sv_filtered_base[c_lopsv].dropna().unique().tolist())
                    selected_lop = st.selectbox("📌 Chọn Lớp muốn xem báo cáo:", options=list_lop, key="sb_sel_lop_qlsv")
                    df_sv_filtered = df_sv_filtered_base[df_sv_filtered_base[c_lopsv] == selected_lop].copy()
                    st.markdown(f"#### 🏫 Báo cáo tổng hợp theo Lớp SV: **{selected_lop}**")
                else:
                    df_sv_filtered = df_sv_filtered_base.copy()
                    st.warning("⚠️ Không tìm thấy cột lớp SV trong dữ liệu sinh viên.")

            total_sv_tk = len(df_sv_filtered)
            st.markdown(f"- **Tổng số sinh viên (theo bộ lọc hiện tại):** **{total_sv_tk:,}** sinh viên")

            if c_tinhtrang:
                df_tt_tk = df_sv_filtered.groupby(c_tinhtrang).agg(
                    Số_lượng=(c_mssv, "count")
                ).reset_index().sort_values("Số_lượng", ascending=False)
                
                tong_so_tt = df_tt_tk["Số_lượng"].sum()
                df_tt_tk["Tỷ lệ (%)"] = df_tt_tk["Số_lượng"].apply(lambda x: round((x / tong_so_tt) * 100, 2) if tong_so_tt > 0 else 0)
                df_tt_tk.columns = ["Tình trạng sinh viên", "Số lượng", "Tỷ lệ (%)"]
                
                tong_row_tt = pd.DataFrame([{"Tình trạng sinh viên": "📊 TỔNG CỘNG", "Số lượng": tong_so_tt, "Tỷ lệ (%)": 100.0}])
                df_tt_tk = pd.concat([df_tt_tk, tong_row_tt], ignore_index=True)

                st.markdown("##### 📌 Thống kê theo Tình trạng sinh viên")
                st.dataframe(df_tt_tk, use_container_width=True, hide_index=True)

            if c_tinhtrang and c_xeploai:
                df_sv_filtered["_tt_lower"] = df_sv_filtered[c_tinhtrang].astype(str).str.lower().str.strip()
                df_tn_tk = df_sv_filtered[df_sv_filtered["_tt_lower"].str.contains("tốt nghiệp", na=False)].copy()

                if not df_tn_tk.empty:
                    df_tn_tk[c_xeploai] = df_tn_tk[c_xeploai].astype(str).str.strip()
                    df_tn_tk_valid = df_tn_tk[
                        (df_tn_tk[c_xeploai] != "") & 
                        (df_tn_tk[c_xeploai].str.lower() != "nan") & 
                        (df_tn_tk[c_xeploai].str.lower() != "chưa xếp loại")
                    ]

                    if not df_tn_tk_valid.empty:
                        df_xl_tk = df_tn_tk_valid.groupby(c_xeploai).agg(
                            Số_lượng=(c_mssv, "count")
                        ).reset_index().sort_values("Số_lượng", ascending=False)
                        
                        tong_so_xl = df_xl_tk["Số_lượng"].sum()
                        df_xl_tk["Tỷ lệ (%)"] = df_xl_tk["Số_lượng"].apply(lambda x: round((x / tong_so_xl) * 100, 2) if tong_so_xl > 0 else 0)
                        df_xl_tk.columns = ["Xếp loại tốt nghiệp", "Số lượng", "Tỷ lệ (%)"]
                        
                        tong_row_xl = pd.DataFrame([{"Xếp loại tốt nghiệp": "📊 TỔNG CỘNG", "Số lượng": tong_so_xl, "Tỷ lệ (%)": 100.0}])
                        df_xl_tk = pd.concat([df_xl_tk, tong_row_xl], ignore_index=True)

                        st.markdown("##### 🎓 Thống kê Xếp loại Tốt nghiệp (Tổng quan)")
                        st.dataframe(df_xl_tk, use_container_width=True, hide_index=True)

                        if "Năm học" in df_tn_tk_valid.columns:
                            df_pivot_xl = df_tn_tk_valid.pivot_table(
                                index=c_xeploai, 
                                columns="Năm học", 
                                values=c_mssv, 
                                aggfunc="count", 
                                fill_value=0
                            )
                            
                            sorted_years = sorted([c for c in df_pivot_xl.columns if c != "Năm học"])
                            df_pivot_xl = df_pivot_xl[sorted_years]
                            
                            for i in range(1, len(sorted_years)):
                                prev_col = sorted_years[i-1]
                                curr_col = sorted_years[i]
                                pct_change = ((df_pivot_xl[curr_col] - df_pivot_xl[prev_col]) / df_pivot_xl[prev_col].replace(0, np.nan)) * 100
                                df_pivot_xl[f"Tăng/Giảm ({curr_col})"] = pct_change.round(2).fillna(0).apply(lambda x: f"+{x}%" if x > 0 else f"{x}%")

                            df_pivot_xl = df_pivot_xl.reset_index()
                            df_pivot_xl.rename(columns={c_xeploai: "Xếp loại tốt nghiệp"}, inplace=True)

                            sum_row = {"Xếp loại tốt nghiệp": "📊 TỔNG CỘNG"}
                            for col in sorted_years:
                                sum_row[col] = df_pivot_xl[col].sum()
                            
                            df_pivot_xl = pd.concat([df_pivot_xl, pd.DataFrame([sum_row])], ignore_index=True)

                            st.markdown("##### 📅 Thống kê Xếp loại Tốt nghiệp theo từng Năm học")
                            st.dataframe(df_pivot_xl, use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Đã tìm thấy sinh viên tốt nghiệp nhưng cột Xếp loại TN đang bị trống.")
                else:
                    st.info("ℹ️ Không tìm thấy sinh viên nào có tình trạng là 'Tốt nghiệp' trong phạm vi lựa chọn này.")

            st.markdown("##### 📅 Bảng tổng hợp dữ liệu động theo Tiêu chí")
            st.caption("💡 Tích chọn các tiêu chí bên dưới để nhóm dữ liệu thống kê và trực quan hóa biểu đồ động:")
            
            with st.expander("📅 **(Bấm để mở/đóng tùy chọn tiêu chí động)**", expanded=True):
                target_criteria = [
                    "Năm học", "Giới tính", "Tình trạng", "Bậc đào tạo", 
                    "Loại hình đào tạo", "Khóa học", "Xếp loại TN", 
                    "Tên Ngành", "Tên chuyên ngành", "Lớp SV"
                ]
                
                available_criteria = [c for c in target_criteria if c in df_sv_filtered.columns]
                
                cols_checkbox = st.columns(3)
                selected_group_cols = []
                
                for i, col_name in enumerate(available_criteria):
                    with cols_checkbox[i % 3]:
                        default_checked = True if col_name in ["Năm học", "Xếp loại TN"] else False
                        if st.checkbox(f"📁 {col_name}", value=default_checked, key=f"chk_group_tab1_qlsv_{report_level_sv}_{col_name}"):
                            selected_group_cols.append(col_name)

            if selected_group_cols:
                df_dynamic_summary = df_sv_filtered.groupby(selected_group_cols).agg(
                    Số_lượng=(c_mssv, "count")
                ).reset_index()

                if "Năm học" in selected_group_cols:
                    df_dynamic_summary = df_dynamic_summary.sort_values(by=["Năm học"] + selected_group_cols[:1], ascending=[False, True])
                else:
                    df_dynamic_summary = df_dynamic_summary.sort_values(by="Số_lượng", ascending=False)

                tong_so_dynamic = df_dynamic_summary["Số_lượng"].sum()
                df_dynamic_summary["Tỷ lệ (%)"] = df_dynamic_summary["Số_lượng"].apply(lambda x: round((x / tong_so_dynamic) * 100, 2) if tong_so_dynamic > 0 else 0)

                if "Năm học" in selected_group_cols and len(selected_group_cols) == 1:
                    df_dynamic_summary = df_dynamic_summary.sort_values("Năm học", ascending=True)
                    df_dynamic_summary["Biến động số lượng"] = df_dynamic_summary["Số_lượng"].diff()
                    
                    def format_tang_giam(val):
                        if pd.isna(val) or val == 0:
                            return "0"
                        sign = "+" if val > 0 else ""
                        return f"{sign}{int(val)}"

                    df_dynamic_summary["Tăng/Giảm so với năm trước"] = df_dynamic_summary["Biến động số lượng"].apply(format_tang_giam)
                    df_dynamic_summary = df_dynamic_summary.sort_values("Năm học", ascending=False).reset_index(drop=True)
                    
                    display_columns = selected_group_cols + ["Số_lượng", "Tỷ lệ (%)", "Tăng/Giảm so với năm trước"]
                    df_final_show = df_dynamic_summary[display_columns].copy()
                    df_final_show.columns = selected_group_cols + ["Số lượng", "Tỷ lệ (%)", "Tăng/Giảm so với năm trước"]
                else:
                    display_columns = selected_group_cols + ["Số_lượng", "Tỷ lệ (%)"]
                    df_final_show = df_dynamic_summary[display_columns].copy()
                    df_final_show.columns = selected_group_cols + ["Số lượng", "Tỷ lệ (%)"]

                st.dataframe(df_final_show, use_container_width=True)

                st.markdown("##### 📈 Biểu đồ trực quan hóa dữ liệu động")
                try:
                    if selected_group_cols:
                        dim_cols_for_chart = [c for c in selected_group_cols if c != "Năm học"]
                        
                        if "Năm học" in selected_group_cols and dim_cols_for_chart:
                            for dim in dim_cols_for_chart:
                                st.markdown(f"###### 📊 Biểu đồ diễn biến **{dim}** theo Năm học")
                                
                                df_pivot_chart = df_sv_filtered.pivot_table(
                                    index="Năm học",
                                    columns=dim,
                                    values=c_mssv,
                                    aggfunc="count",
                                    fill_value=0
                                ).sort_index()
                                
                                fig, ax = plt.subplots(figsize=(max(8, len(df_pivot_chart) * 0.8), 4.8))
                                df_pivot_chart.plot(kind="bar", ax=ax, rot=30, width=0.8, colormap="tab10")
                                
                                ax.set_title(f"Biến động {dim} theo Năm học", fontsize=11, fontweight="bold", pad=15)
                                ax.set_xlabel("Năm học", fontsize=9, labelpad=8)
                                ax.set_ylabel("Số lượng sinh viên", fontsize=9, labelpad=8)
                                ax.grid(axis="y", linestyle="--", alpha=0.7)
                                ax.legend(title=dim, loc="upper left", frameon=True, facecolor="white", framealpha=0.8, fontsize=8, title_fontsize=9)
                                
                                for container in ax.containers:
                                    ax.bar_label(container, fmt='%d', padding=2, fontsize=7, fontweight='bold')

                                plt.tight_layout()
                                st.pyplot(fig, bbox_inches="tight")
                                plt.close(fig)

                        elif dim_cols_for_chart and "Năm học" not in selected_group_cols:
                            for dim in dim_cols_for_chart:
                                st.markdown(f"###### 📊 Biểu đồ phân bố theo: **{dim}**")
                                
                                df_dim_chart = df_sv_filtered.groupby(dim).agg(
                                    Số_lượng=(c_mssv, "count")
                                ).reset_index().sort_values("Số_lượng", ascending=False)
                                
                                if not df_dim_chart.empty:
                                    unique_labels = df_dim_chart[dim].astype(str).tolist()
                                    prefix_code = "M" if "ngành" in dim.lower() else ("L" if "lớp" in dim.lower() else "ID")
                                    label_mapping = {lbl: f"{prefix_code}{i+1}" for i, lbl in enumerate(unique_labels)}
                                    
                                    df_dim_chart["Ký hiệu"] = df_dim_chart[dim].map(label_mapping)
                                    
                                    fig, ax = plt.subplots(figsize=(max(6, len(df_dim_chart) * 0.6), 4.5))
                                    bars = ax.bar(df_dim_chart["Ký hiệu"].astype(str), df_dim_chart["Số_lượng"], color="#4C72B0", width=0.6)
                                    
                                    for bar in bars:
                                        h = bar.get_height()
                                        if h > 0:
                                            ax.annotate(f"{int(h)}", 
                                                        (bar.get_x() + bar.get_width() / 2., h),
                                                        ha='center', va='bottom', fontsize=8, fontweight='bold',
                                                        xytext=(0, 2), textcoords='offset points')
                                            
                                    ax.set_xlabel(f"Ký hiệu ({dim})", fontsize=9)
                                    ax.set_ylabel("Số lượng sinh viên", fontsize=9)
                                    ax.set_title(f"Phân bố số lượng theo {dim}", fontsize=10, fontweight="bold", pad=15)
                                    ax.tick_params(axis="x", rotation=30)
                                    ax.grid(axis="y", linestyle="--", alpha=0.5)
                                    
                                    plt.tight_layout()
                                    st.pyplot(fig, bbox_inches="tight")
                                    plt.close(fig)
                                    
                                    st.markdown(f"**📝 Chú thích ký hiệu trục hoành ({dim}):**")
                                    with st.expander(f"📅 **(Bấm để mở/đóng chú thích {dim})**", expanded=True):
                                        note_df = pd.DataFrame(list(label_mapping.items()), columns=["Ký hiệu", f"Tên đầy đủ ({dim})"])
                                        st.dataframe(note_df, use_container_width=True, hide_index=True)

                        elif selected_group_cols == ["Năm học"]:
                            st.markdown("###### 📈 Biểu đồ tổng số lượng sinh viên theo Năm học")
                            
                            df_year_chart = df_sv_filtered.groupby("Năm học").agg(
                                Số_lượng=(c_mssv, "count")
                            ).reset_index().sort_values("Năm học")
                            
                            fig, ax = plt.subplots(figsize=(max(6, len(df_year_chart) * 0.8), 4.2))
                            bars = ax.bar(df_year_chart["Năm học"].astype(str), df_year_chart["Số_lượng"], color="#2ca02c", width=0.55)
                            
                            ax.set_title("Tổng số lượng sinh viên qua các Năm học", fontsize=11, fontweight="bold", pad=15)
                            ax.set_xlabel("Năm học", fontsize=9, labelpad=8)
                            ax.set_ylabel("Số lượng sinh viên", fontsize=9, labelpad=8)
                            ax.tick_params(axis="x", rotation=30)
                            ax.grid(axis="y", linestyle="--", alpha=0.7)
                            
                            ax.bar_label(bars, fmt='%d', padding=3, fontsize=9, fontweight='bold')

                            plt.tight_layout()
                            st.pyplot(fig, bbox_inches="tight")
                            plt.close(fig)
                            
                    else:
                        st.info("ℹ️ Vui lòng tích chọn ít nhất một tiêu chí ở bảng động bên trên để hiển thị biểu đồ.")
                except Exception as chart_err:
                    st.caption(f"Không thể vẽ biểu đồ Matplotlib với các nhóm đã chọn: {chart_err}")
            else:
                st.info("👆 Vui lòng tích chọn ít nhất một tiêu chí ở các hộp kiểm bên trên để hiển thị bảng và biểu đồ.")

# ----------------------------------------------------------
# TAB 2: TRA CỨU CÔNG VIỆC & SINH VIÊN NÂNG CAO
# ----------------------------------------------------------
with tab2:
    search_scope = st.radio(
        "📂 Chọn phạm vi / hạng mục cần tìm kiếm:",
        options=[
            "🌐 Tất cả các bảng",
            "📚 GD (Giảng dạy)",
            "🔬 NCKH (Nghiên cứu)",
            "📌 Other (Khác)",
            "🎓 SV (Sinh viên)",
        ],
        horizontal=True,
    )

    keyword_input = (
        st.text_input(
            "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,). Có thể gõ theo MSSV, Họ tên, Lớp, Tình trạng, Xếp loại... Ví dụ: Nguyễn Văn, Giỏi"
        )
        .strip()
        .lower()
    )
    st.caption("💡 Mẹo: Có thể tìm kiếm đồng thời nhiều điều kiện bằng cách dùng dấu phẩy `,` hoặc dấu kết hợp `&`.")
    
    df1 = st.session_state.get("df1")
    df2 = st.session_state.get("df2")
    detail_dfs = st.session_state.get("filtered_detail_dfs", {})
    
    # Lấy dữ liệu sinh viên đã qua phân quyền cố vấn để tra cứu
    df_sv_search_source = filtered_df_sv if filtered_df_sv is not None and not filtered_df_sv.empty else read_gsheet(LINK_SV)

    found_records = []

    if keyword_input:
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
        elif "SV (Sinh viên)" in search_scope:
            if df_sv_search_source is not None:
                target_search_dict["SV"] = df_sv_search_source
        else: # "🌐 Tất cả các bảng"
            target_search_dict = detail_dfs.copy()
            if df_sv_search_source is not None:
                target_search_dict["SV"] = df_sv_search_source

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
                if name != "SV":
                    if "code" in match_df.columns and df1 is not None and "code" in df1.columns:
                        match_df = match_df.merge(
                            df1.drop_duplicates(subset=["code"]), on="code", how="left"
                        )
                    if "category" in match_df.columns and df2 is not None and "category" in df2.columns:
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
                f"✅ Tìm thấy kết quả phù hợp từ {len(found_records)} nhóm bảng dữ liệu"
            )
        else:
            st.warning("❌ Không tìm thấy dữ liệu phù hợp trong phạm vi đã chọn.")
    else:
        st.info("👆 Chọn phạm vi và nhập từ khóa để bắt đầu tra cứu công việc hoặc sinh viên.")

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

    # Hiển thị kết quả tìm kiếm chi tiết theo từng bảng
    if found_records:
        st.markdown("#### 📂 KẾT QUẢ TÌM KIẾM CHI TIẾT")
        for name, rec_df in found_records:
            display_label_name = "Sinh viên (SV)" if name == "SV" else f"Bảng công việc gốc ({name})"
            st.markdown(f"##### 📘 Nhóm kết quả từ: **{display_label_name}** — {len(rec_df)} dòng")
            with st.expander(f"📅 **(Bấm để mở/đóng xem bảng {name})**", expanded=True):
                show_df = rec_df.drop(columns=["_source_table"], errors="ignore")
                st.dataframe(show_df, use_container_width=True)
    else:
        if keyword_input:
            st.info("ℹ️ Không có bản ghi nào khớp với từ khóa tìm kiếm trên các bảng.")

# ----------------------------------------------------------
# TAB 3: DỮ LIỆU GỐC THEO PHÂN QUYỀN
# ----------------------------------------------------------
if tab3 is not None:
    with tab3:
        st.markdown("#### 📂 Dữ liệu mô tả (df1 & df2)")
        col1, col2 = st.columns(2)
        
        with col1:
          if "df1" not in st.session_state or st.session_state["df1"] is None:
            st.session_state["df1"] = read_gsheet(links["df1"])
          if st.session_state["df1"] is not None:
            st.success("✅ Đã tải df1 (Year - Term - Code)!")
            with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                st.dataframe(st.session_state["df1"], height=400, use_container_width=True)
        
        with col2:
          if "df2" not in st.session_state or st.session_state["df2"] is None:
            st.session_state["df2"] = read_gsheet(links["df2"])
          if st.session_state["df2"] is not None:
            st.success("✅ Đã tải df2 (Category - Description)!")
            with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                st.dataframe(st.session_state["df2"], height=400, use_container_width=True)
        
        st.divider()
        
        st.markdown("#### 📘 Dữ liệu các nhóm công việc GD, NCKH, Other & Sinh viên (Đã phân quyền)")
        detail_dfs = st.session_state.get("filtered_detail_dfs", {})
    
        if detail_dfs:
          selected_group_view = st.radio(
              "Chọn nhóm công việc / dữ liệu muốn xem:",
              options=["GD (Giảng dạy)", "NCKH (Nghiên cứu)", "Other (Khác)", "SV (Sinh viên)"],
              horizontal=True,
              key="radio_group_view_qlcv"
          )
          key_mapping_view = {
              "GD (Giảng dạy)": "GD",
              "NCKH (Nghiên cứu)": "NCKH",
              "Other (Khác)": "Other",
          }
          if selected_group_view == "SV (Sinh viên)":
              st.success("✅ Đang hiển thị dữ liệu nhóm: Sinh viên (QLSV)")
              with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                  st.dataframe(filtered_df_sv, height=450, use_container_width=True)
          else:
              chosen_key_view = key_mapping_view[selected_group_view]
              if chosen_key_view in detail_dfs:
                st.success(f"✅ Đang hiển thị dữ liệu nhóm: {selected_group_view}")
                with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                    st.dataframe(detail_dfs[chosen_key_view], height=450, use_container_width=True)
              else:
                st.warning(f"⚠️ Nhóm {selected_group_view} hiện chưa có dữ liệu hoặc bạn không có quyền xem.")
        else:
          st.error("❌ Không thể tải dữ liệu chi tiết từ Google Sheets.")

# ----------------------------------------------------------
# TAB 4: QUẢN TRỊ ADMIN
# ----------------------------------------------------------
if tab4 is not None:
    with tab4:
        st.markdown("#### 🛠️ Quản lý Hệ thống")
        
        if "admin" not in pos:
            st.error("⛔ Bạn không có quyền truy cập trang quản trị hệ thống này. Khu vực này chỉ dành cho tài khoản có quyền Admin.")
        else:
            st.success("✅ Đã xác thực quyền Quản trị viên hệ thống.")
            
            reset_mode = st.radio(
                "📂 Chọn chế độ thao tác quản lý:",
                options=["🔑 Reset mật khẩu từng người", "🔄 Reset toàn bộ mật khẩu"],
                horizontal=True,
                key="radio_admin_reset_mode"
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
                    
                    chosen_user_label = st.selectbox("Chọn tài khoản cần reset mật khẩu:", user_table_df["_display_name"].tolist(), key="sb_admin_reset_user")
                    selected_row = user_table_df[user_table_df["_display_name"] == chosen_user_label]
                    
                    if not selected_row.empty:
                        target_id = str(selected_row.iloc[0][id_c]).strip()
                        st.info(f"📌 Tài khoản đang chọn: **{chosen_user_label}** (Mật khẩu mặc định sau khi reset sẽ trùng với ID: **{target_id}**)")
                        
                        if st.button("🔄 Thực hiện Reset Mật khẩu về ID", use_container_width=True, key="btn_admin_reset_single"):
                            update_password(target_id, target_id, LINK_USER, "1")
                            st.cache_data.clear()
                            st.success(f"✅ Đã reset mật khẩu thành công cho ID: **{target_id}**. Mật khẩu mới hiện là: `{target_id}`")
                else:
                    st.error("❌ Không tải được danh sách từ bảng User.")
                    
            else:
                st.markdown("##### 🔄 Reset mật khẩu toàn bộ hệ thống về mặc định (Trùng với ID của từng người)")
                st.warning("⚠️ Thao tác này sẽ đặt lại mật khẩu của **tất cả** các tài khoản trên hệ thống về trùng với mã ID tương ứng của từng người và bắt buộc họ phải đổi lại mật khẩu trong lần đăng nhập tới.")
                
                if st.button("🚨 Xác nhận Reset toàn bộ hệ thống về mặc định", use_container_width=True, key="btn_admin_reset_all"):
                    user_user_db = read_gsheet(LINK_USER)
                    if user_user_db is not None and not user_user_db.empty:
                        user_user_db.columns = [str(c).strip().lower() for c in user_user_db.columns]
                        
                        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                        creds_dict = get_creds()
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                        client = gspread.authorize(creds)
                        sheet = client.open_by_url(LINK_USER).sheet1
                        all_rows = sheet.get_all_values()
                        
                        for idx, row in enumerate(all_rows):
                            if idx == 0: continue
                            row_id = str(row[0]).strip()
                            if row_id:
                                sheet.update_cell(idx + 1, 5, f"'{row_id}")
                                sheet.update_cell(idx + 1, 6, "1")
                                
                        st.cache_data.clear()
                        st.success("✅ Đã reset thành công mật khẩu cho toàn bộ hệ thống về trùng với ID tương ứng!")
                    else:
                        st.error("❌ Không thể đọc dữ liệu để thực hiện reset toàn bộ.")
                        
            st.divider()
            st.markdown("##### 📋 Danh sách tài khoản người dùng hiện tại (Google Sheet Link User)")
            st.caption("Đường dẫn liên kết trực tiếp: `https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/edit?gid=745357874#gid=745357874`")
            if user_table_df is not None and not user_table_df.empty:
                with st.expander("📅 **(Bấm để mở/đóng xem bảng thông tin User)**", expanded=True):
                    st.dataframe(user_table_df, use_container_width=True)
            else:
                st.warning("⚠️ Không thể tải dữ liệu bảng User.")
