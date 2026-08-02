#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 20:50:24 2025
📋 Ứng dụng Quản lý Công việc (QLCV) - Bản hoàn chỉnh đầy đủ tính năng & Phân quyền
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
# ⚙️ CẤU HÌNH APPS & LINK USER
# ==========================================================
st.set_page_config(page_title="📋 Ứng dụng QLCV - Phân quyền đầy đủ", layout="wide")

LINK_USER = "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=745357874"

links = {
    "df1": "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=2080729380",
    "df2": "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=0",
    "GD": "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1431418978",
    "NCKH": "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1814822744",
    "Other": "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1443108898",
}

# ==========================================================
# 🛠️ CÁC HÀM HỖ TRỢ XÁC THỰC & ĐỌC DỮ LIỆU
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
            return None
        df.columns = [str(c).strip().replace("\xa0", "").lower() for c in df.columns]
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Lỗi đọc Google Sheet từ link: {e}")
        return None

def check_login(user_db, user_id, password):
    if user_db is None:
        return False, None, None
    df = user_db.copy()
    
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

st.sidebar.title("👤 Thông tin tài khoản")
st.sidebar.success(f"**{current_user['fullname']}**\n\n📌 Chức vụ: **{pos.title()}**\n\n🏫 Đơn vị: **{u_faculty if u_faculty else 'Khoa'}**")
if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.must_change = "0"
    st.rerun()

st.title("📋 Ứng dụng Quản lý Công việc (QLCV)")
st.write(f"Hệ thống tổng hợp thông tin công việc — Đang phân quyền theo cấp bậc: **{pos.title()}**")

# ==========================================================
# 🛡️ HÀM LỌC DỮ LIỆU THEO PHÂN QUYỀN CHUYÊN SÂU
# ==========================================================
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
    
    # Admin & Lãnh đạo khoa: Toàn quyền xem đầy đủ
    if "admin" in position or "lãnh đạo khoa" in position:
        return df_filtered.copy()
    
    # Lãnh đạo bộ môn: Xem theo cá nhân hoặc bộ môn
    if "lãnh đạo bộ môn" in position:
        mask = pd.Series(False, index=df_filtered.index)
        if id_col:
            mask |= df_filtered[id_col].astype(str).str.strip() == uid
        if fac_col and fac and fac.lower() != "tất cả":
            mask |= df_filtered[fac_col].astype(str).str.lower().str.contains(fac.lower(), na=False)
        if mask.any():
            return df_filtered[mask].copy()
        
    # Giảng viên: Chỉ xem dữ liệu cá nhân khớp ID
    if id_col:
        return df_filtered[df_filtered[id_col].astype(str).str.strip() == uid].copy()
    
    return df_filtered.head(0)

# ==========================================================
# 🧩 TẢI DỮ LIỆU GỐC & ÁP DỤNG PHÂN QUYỀN
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

# Áp dụng bộ lọc phân quyền vào toàn bộ dữ liệu hệ thống
raw_detail_dfs = st.session_state.get("detail_dfs", {})
filtered_detail_dfs = {}
for k, df in raw_detail_dfs.items():
    filtered_detail_dfs[k] = filter_dataframe_by_permission(df, current_user)

st.session_state["filtered_detail_dfs"] = filtered_detail_dfs

# ==========================================================
# 📑 GIAO DIỆN 2 TAB CHÍNH (GIỮ NGUYÊN 100% LUỒNG CŨ)
# ==========================================================
tab1, tab2 = st.tabs(["🔍 1. Tra cứu công việc nâng cao", "📂 2. Dữ liệu gốc theo phân quyền"])

with tab1:
    col_refresh1, col_refresh2 = st.columns([4, 1])
    with col_refresh1:
        st.header("🔍 Tra cứu công việc nâng cao")

    search_scope = st.radio(
        "📂 Chọn phạm vi / hạng mục cần tìm kiếm:",
        options=["🌐 Tất cả các bảng", "📚 GD (Giảng dạy)", "🔬 NCKH (Nghiên cứu)", "📌 Other (Khác)"],
        horizontal=True,
    )

    keyword_input = st.text_input("🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)").strip().lower()
    st.caption("💡 Mẹo: Để xem thông tin theo từng nội dung, gõ GD hoặc NCKH")
    
    df1 = st.session_state.get("df1")
    df2 = st.session_state.get("df2")
    target_dfs = st.session_state.get("filtered_detail_dfs", {})

    found_records = []

    if keyword_input:
        if df1 is None or df1.empty or df2 is None or df2.empty or not target_dfs:
            st.warning("⚠️ Vui lòng đảm bảo đã tải đủ df1, df2 và các bảng công việc.")
        else:
            raw_keywords = [k.strip() for k in re.split(r"[&,]", keyword_input) if k.strip()]
            
            expanded_keywords = []
            for kw in raw_keywords:
                synonyms = [kw]
                if any(k in kw for k in ["sách tham khảo", "sck", "tltk", "sách"]):
                    for s in ["sách tham khảo", "sck", "tltk", "sách"]:
                        if s not in synonyms: synonyms.append(s)
                elif "bài báo" in kw and "khoa học" not in kw:
                    synonyms.append("bài báo khoa học")
                elif "đề tài" in kw:
                    synonyms.append("đề tài")
                expanded_keywords.append(synonyms)

            target_search_dict = {}
            if "GD" in search_scope and "GD" in target_dfs:
                target_search_dict["GD"] = target_dfs["GD"]
            elif "NCKH" in search_scope and "NCKH" in target_dfs:
                target_search_dict["NCKH"] = target_dfs["NCKH"]
            elif "Other" in search_scope and "Other" in target_dfs:
                target_search_dict["Other"] = target_dfs["Other"]
            else:
                target_search_dict = target_dfs

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
                                mask_kw |= df_temp[c].str.lower().str.contains(kw, case=False, na=False)
                            mask_syn |= mask_kw
                        mask &= mask_syn
                else:
                    mask = pd.Series(False, index=df_temp.index)

                match_df = df_temp[mask].copy()
                if not match_df.empty:
                    if "code" in match_df.columns and "code" in df1.columns:
                        match_df = match_df.merge(df1.drop_duplicates(subset=["code"]), on="code", how="left")
                    if "category" in match_df.columns and "category" in df2.columns:
                        match_df = match_df.merge(df2.drop_duplicates(subset=["category"]), on="category", how="left")
                    match_df = match_df.drop_duplicates()
                    match_df["_source_table"] = name
                    found_records.append((name, match_df))

            if found_records:
                st.success(f"✅ Tìm thấy kết quả phù hợp từ {len(found_records)} nhóm bảng")
            else:
                st.warning("❌ Không tìm thấy dữ liệu phù hợp trong phạm vi quyền hạn của bạn.")
    else:
        st.info("👆 Chọn phạm vi và nhập từ khóa để bắt đầu tìm kiếm và thống kê.")

    with col_refresh2:
        if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
            st.cache_data.clear()
            for k in ["df1", "df2", "detail_dfs", "filtered_detail_dfs", "selected_years_stat"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    st.divider()

    # XỬ LÝ HIỂN THỊ KẾT QUẢ VÀ ĐỒ THỊ BAN ĐẦU
    if search_scope == "🌐 Tất cả các bảng":
        if found_records:
            st.markdown("#### 📂 KẾT QUẢ TÌM KIẾM DỮ LIỆU TỪ CÁC BẢNG")
            for name, rec_df in found_records:
                st.markdown(f"##### 📘 Nhóm kết quả từ bảng: **{name}** — {len(rec_df)} dòng")
                with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                    st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("ℹ️ Nhập từ khóa để hiển thị kết quả tìm kiếm.")
    else:
        valid_dfs = [df for name, df in found_records if not df.empty] if found_records else [df for df in target_dfs.values() if df is not None and not df.empty]
        total_rec_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()

        if not total_rec_df.empty:
            st.markdown("#### 📈 THỐNG KÊ VÀ PHÂN TÍCH DỮ LIỆU")
            tiet_col_target = next((c for c in total_rec_df.columns if any(x in c.lower() for x in ["sỐ tiết kê khai", "tiết", "period"])), None)
            time_col_target = next((c for c in total_rec_df.columns if any(x in c.lower() for x in ["đợt kê khai", "năm học", "year"])), None)

            if tiet_col_target and time_col_target:
                total_rec_df[tiet_col_target] = pd.to_numeric(total_rec_df[tiet_col_target], errors="coerce").fillna(0)
                total_rec_df["Năm học"] = total_rec_df[time_col_target].apply(quy_doi_nam_hoc)

                all_years = sorted(total_rec_df["Năm học"].dropna().unique().tolist(), reverse=True)
            
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
                        if st.button("1 năm gần nhất", use_container_width=True): set_quick_selection(1); st.rerun()
                    with col_btn2:
                        if st.button("3 năm gần nhất", use_container_width=True): set_quick_selection(3); st.rerun()
                    with col_btn3:
                        if st.button("5 năm gần nhất", use_container_width=True): set_quick_selection(5); st.rerun()
                    with col_btn4:
                        if st.button("Tất cả (Max)", use_container_width=True): set_quick_selection("all"); st.rerun()
            
                    selected_years = []
                    grid_cols = st.columns(2)
                    for i, year in enumerate(all_years):
                        chk_key = f"chk_year_{year}"
                        if chk_key not in st.session_state:
                            st.session_state[chk_key] = (year in st.session_state["selected_years_stat"])
                        with grid_cols[i % 2]:
                            if st.checkbox(str(year), key=chk_key):
                                selected_years.append(year)
                    st.session_state["selected_years_stat"] = selected_years

                if not selected_years:
                    st.warning("⚠️ Vui lòng tích chọn ít nhất một năm học.")
                else:
                    total_rec_df = total_rec_df[total_rec_df["Năm học"].isin(selected_years)]
                    if total_rec_df.empty:
                        st.warning("❌ Không có dữ liệu cho năm học đã chọn.")
                    else:
                        is_only_gd = ("_source_table" in total_rec_df.columns and (total_rec_df["_source_table"] == "GD").all())
                        
                        if is_only_gd:
                            # KHỐI GIẢNG DẠY (Giữ nguyên toàn bộ logic chuẩn ban đầu)
                            df_clean = total_rec_df.drop_duplicates().copy()
                            df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]
                            if "term_x" in df_clean.columns: df_clean["term"] = df_clean["term_x"]
                            
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
                            
                            name_col = "name" if "name" in df_clean.columns else None
                            surname_col = "surname" if "surname" in df_clean.columns else None
                            if name_col:
                                df_clean["_full_name"] = df_clean[surname_col].astype(str) + " " + df_clean[name_col].astype(str) if surname_col else df_clean[name_col].astype(str)
                            else:
                                df_clean["_full_name"] = "Không rõ"

                            # Bảng tổng hợp GD theo năm
                            df_after = df_clean.groupby("năm học").agg({
                                tiet_col: "sum",
                                c_class: "nunique",
                                c_subject: "nunique"
                            }).reset_index().sort_values("năm học")
                            df_after = df_after.rename(columns={"năm học": "Năm học", tiet_col: "Tổng số tiết thực hiện", c_class: "Số lượng lớp", c_subject: "Số lượng môn học"})
                            
                            st.markdown("##### 🧹 1. Bảng tổng hợp Giảng dạy theo Năm học")
                            tot_lop, tot_tiet = df_after["Số lượng lớp"].sum(), df_after["Tổng số tiết thực hiện"].sum()
                            df_after.loc[len(df_after)] = ["**Tổng cộng**", tot_tiet, tot_lop, float('nan')]
                            st.dataframe(df_after[["Năm học", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]], use_container_width=True)
                        else:
                            st.dataframe(total_rec_df, use_container_width=True)

with tab2:
    st.markdown("#### 📂 Dữ liệu gốc được phân quyền theo tài khoản")
    detail_dfs = st.session_state.get("filtered_detail_dfs", {})
    if detail_dfs:
        selected_group_view = st.radio("Chọn nhóm công việc muốn xem:", options=["GD (Giảng dạy)", "NCKH (Nghiên cứu)", "Other (Khác)"], horizontal=True)
        key_mapping_view = {"GD (Giảng dạy)": "GD", "NCKH (Nghiên cứu)": "NCKH", "Other (Khác)": "Other"}
        chosen_key_view = key_mapping_view[selected_group_view]
        if chosen_key_view in detail_dfs:
            st.success(f"✅ Đang hiển thị dữ liệu phân quyền nhóm: {selected_group_view}")
            st.dataframe(detail_dfs[chosen_key_view], height=450, use_container_width=True)
        else:
            st.warning("⚠️ Không có dữ liệu.")
    else:
        st.error("❌ Không thể tải dữ liệu chi tiết.")
