#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 20:50:24 2025
📋 Ứng dụng Quản lý Công việc (QLCV) - Tích hợp phân quyền chi tiết
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
st.set_page_config(page_title="📋 Ứng dụng QLCV - Phân quyền", layout="wide")

# Link bảng User chứa thông tin phân quyền (id, faculty, surname, name, password, must_change, position)
LINK_USER = "https://docs.google.com/spreadsheets/d/1F_w2yXvD66m0DeSmUrn-mFYcHwr2VKL6JYS6-bdATtQ/export?format=csv&gid=1406726171"

# ==========================================================
# 🔗 CÁC LINK DỮ LIỆU ĐÃ CHUẨN HÓA EXPORT CSV
# ==========================================================
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
        df.columns = [str(c).strip().replace("\xa0", "") for c in df.columns]
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Lỗi đọc Google Sheet từ link: {e}")
        return None

def check_login(user_db, user_id, password):
    if user_db is None:
        return False, None
    df = user_db.copy()
    
    # Tìm cột ID linh hoạt
    id_col = next((c for c in df.columns if c.lower() in ["id", "mã", "mssv"]), df.columns[0])
    pass_col = next((c for c in df.columns if "pass" in c.lower()), "password")
    change_col = next((c for c in df.columns if "must" in c.lower()), "must_change")
    
    df[id_col] = df[id_col].apply(normalize_id)
    row = df[df[id_col] == normalize_id(user_id)]

    if row.empty:
        return False, None

    real_pass = str(row.iloc[0].get(pass_col, ""))
    must_change = str(row.iloc[0].get(change_col, "0"))
    position = str(row.iloc[0].get("position", "giảng viên"))
    faculty = str(row.iloc[0].get("faculty", ""))
    surname = str(row.iloc[0].get("surname", ""))
    name = str(row.iloc[0].get("name", ""))

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
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = get_creds()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    all_data = sheet.get_all_values()
    
    found = False
    for i, row_values in enumerate(all_data):
        if i == 0: continue
        if normalize_id(row_values[0]) == normalize_id(user_id):
            # Cột 5 (Index 4): password, Cột 6 (Index 5): must_change (hoặc điều chỉnh theo thứ tự cột thực tế)
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
# 🔐 QUẢN LÝ PHÂN QUYỀN ĐĂNG NHẬP GIAO DIỆN
# ==========================================================
# ==========================================================
# 🔐 GIAO DIỆN SIDEBAR & PHÂN QUYỀN ĐĂNG NHẬP
# ==========================================================
st.sidebar.title("🔐 Hệ thống Phân quyền")

# Chọn vai trò giả lập hoặc đăng nhập hệ thống
role_options = ["👨‍🏫 Giảng viên", "🔍 Lãnh đạo bộ môn", "⭐ Lãnh đạo khoa", "🛠️ Admin"]
selected_role_ui = st.sidebar.radio("Chọn vai trò truy cập:", role_options)

st.sidebar.markdown("---")

# Mô phỏng thông tin user tương ứng với vai trò được chọn trên sidebar để test nhanh, 
# hoặc bạn có thể kết hợp với bảng user_db từ Google Sheets.
user_db = read_gsheet(LINK_USER)

if "Admin" in selected_role_ui:
    current_user = {"id": "admin", "position": "admin", "faculty": "Tất cả", "fullname": "Quản trị viên hệ thống"}
    # Yêu cầu nhập mật khẩu bảo vệ cho Admin/Giảng viên quản lý
    pwd = st.sidebar.text_input("Nhập mật khẩu quản lý:", type="password")
    if pwd != "010626@#Lanh@#":
        if pwd != "": 
            st.sidebar.error("❌ Sai mật khẩu")
        else: 
            st.info("🔑 Vui lòng nhập mật khẩu quản lý ở menu bên trái.")
        st.stop()
    st.sidebar.success("✅ Đã xác thực Admin")

elif "Lãnh đạo khoa" in selected_role_ui:
    current_user = {"id": "ldk01", "position": "lãnh đạo khoa", "faculty": "Tất cả", "fullname": "Lãnh đạo Khoa"}
    st.sidebar.success("✅ Đã xác thực Lãnh đạo Khoa")

elif "Lãnh đạo bộ môn" in selected_role_ui:
    # Cho phép chọn bộ môn quản lý nếu cần
    dept = st.sidebar.selectbox("Chọn bộ môn:", ["Tài chính", "Ngân hàng", "Kế toán - Kiểm toán"])
    current_user = {"id": "ldbm01", "position": "lãnh đạo bộ môn", "faculty": dept, "fullname": f"Trưởng bộ môn {dept}"}
    st.sidebar.success(f"✅ Đã xác thực Lãnh đạo BM ({dept})")

else:  # Giảng viên
    # Lấy danh sách giảng viên từ user_db nếu có để chọn nhanh
    gv_list = []
    if user_db is not None and not user_db.empty:
        # Lọc các dòng có position là giảng viên
        gv_df = user_db[user_db["position"].str.lower().str.contains("giảng viên", na=False)]
        gv_list = (gv_df["surname"].astype(str) + " " + gv_df["name"].astype(str)).tolist()
    
    if not gv_list:
        gv_list = ["Triệu Kim Lanh"] # Giá trị mặc định nếu chưa load được sheet user
        
    chosen_gv = st.sidebar.selectbox("Chọn Giảng viên:", gv_list)
    
    # Tìm ID tương ứng của giảng viên trong user_db
    matched_id = "gv_default"
    if user_db is not None and not user_db.empty:
        found_row = user_db[(user_db["surname"] + " " + user_db["name"]).str.contains(chosen_gv, na=False)]
        if not found_row.empty:
            matched_id = found_row.iloc[0].get("id", "gv_default")

    current_user = {"id": matched_id, "position": "giảng viên", "faculty": "", "fullname": chosen_gv}
    st.sidebar.success(f"✅ Đang xem với tư cách: {chosen_gv}")

# Nút làm mới dữ liệu chung trên sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Làm mới bộ nhớ cache", use_container_width=True):
    st.cache_data.clear()
    for k in ["df1", "df2", "detail_dfs", "filtered_detail_dfs"]:
        if k in st.session_state:
            del st.session_state[k]
    st.success("Đã làm mới dữ liệu thành công!")
    st.rerun()

# Xử lý bắt buộc đổi mật khẩu nếu must_change == "1"
if str(st.session_state.must_change) == "1":
    st.warning("⚠️ Bạn phải đổi mật khẩu trong lần đăng nhập đầu tiên.")
    new_p = st.text_input("Mật khẩu mới:", type="password")
    if st.button("Xác nhận đổi mật khẩu"):
        if new_p:
            update_password(st.session_state.user_info["id"], new_p, LINK_USER, "0")
            st.session_state.must_change = "0"
            st.cache_data.clear()
            st.success("✅ Đổi mật khẩu thành công! Đang tải lại...")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Vui lòng nhập mật khẩu mới.")
    st.stop()

# Thông tin user hiện tại
current_user = st.session_state.user_info
pos = current_user["position"]
u_id = current_user["id"]
u_faculty = current_user["faculty"]

st.sidebar.success(f"👤 Chào: **{current_user['fullname']}**\n\n📌 Chức vụ: **{pos.title()}**")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.must_change = "0"
    st.rerun()

st.title("📋 Ứng dụng Quản lý Công việc (QLCV)")
st.write(f"Hệ thống tổng hợp thông tin công việc (Giảng dạy, NCKH, Khác) — Phân quyền theo cấp bậc: **{pos.title()}**")

# ==========================================================
# 🧩 KHỞI TẠO VÀ LỌC DỮ LIỆU THEO QUYỀN HẠN
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

# --- HÀM LỌC DỮ LIỆU THEO PHÂN QUYỀN ---
def filter_dataframe_by_permission(df, user_info):
    if df is None or df.empty:
        return df
    
    position = user_info["position"]
    uid = user_info["id"]
    fac = user_info["faculty"]
    
    # 1. Admin & Lãnh đạo khoa: Xem toàn bộ dữ liệu
    if "admin" in position or "lãnh đạo khoa" in position:
        return df.copy()
    
    df_filtered = df.copy()
    
    # Tìm cột ID hoặc Giảng viên trong bảng chi tiết
    id_col = next((c for c in df_filtered.columns if c.lower() in ["id", "mã", "mssv", "code_gv", "gv"]), None)
    fac_col = next((c for c in df_filtered.columns if "faculty" in c.lower() or "khoa" in c.lower() or "bộ môn" in c.lower()), None)
    
    # 2. Lãnh đạo bộ môn: Được xem theo id hoặc khớp faculty/bộ môn
    if "lãnh đạo bộ môn" in position:
        mask = pd.Series(False, index=df_filtered.index)
        if id_col:
            mask |= df_filtered[id_col].apply(normalize_id) == normalize_id(uid)
        if fac_col and fac:
            mask |= df_filtered[fac_col].str.lower().str.contains(fac.lower(), na=False)
        # Nếu không tìm thấy cột lọc phù hợp, mặc định lọc theo ID cá nhân để đảm bảo bảo mật
        if not id_col and not fac_col:
            pass
        else:
            return df_filtered[mask].copy()

    # 3. Giảng viên: Chỉ được xem đúng dữ liệu có ID khớp với mình
    if id_col:
        return df_filtered[df_filtered[id_col].apply(normalize_id) == normalize_id(uid)].copy()
    
    return df_filtered.head(0) # Trả về rỗng nếu không khớp quyền bảo mật

# Áp dụng bộ lọc phân quyền vào các bảng chi tiết
raw_detail_dfs = st.session_state.get("detail_dfs", {})
filtered_detail_dfs = {}
for k, df in raw_detail_dfs.items():
    filtered_detail_dfs[k] = filter_dataframe_by_permission(df, current_user)

st.session_state["filtered_detail_dfs"] = filtered_detail_dfs

# ==========================================================
# 📑 TẠO GIAO DIỆN CÁC TAB CHÍNH
# ==========================================================
tab1, tab2 = st.tabs([
    "🔍 1. Tra cứu công việc nâng cao", 
    "📂 2. Dữ liệu gốc theo phân quyền"
])

with tab1:
    col_refresh1, col_refresh2 = st.columns([4, 1])
    with col_refresh1:
        st.header("🔍 Tra cứu công việc nâng cao")

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

    keyword_input = st.text_input("🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)").strip().lower()
    st.caption("💡 Mẹo: Dữ liệu hiển thị đã tự động giới hạn theo quyền hạn tài khoản của bạn.")
    
    df1 = st.session_state.get("df1")
    df2 = st.session_state.get("df2")
    target_dfs = st.session_state.get("filtered_detail_dfs", {})

    found_records = []

    if keyword_input:
        target_search_dict = {}
        if "GD" in search_scope and "GD" in target_dfs:
            target_search_dict["GD"] = target_dfs["GD"]
        elif "NCKH" in search_scope and "NCKH" in target_dfs:
            target_search_dict["NCKH"] = target_dfs["NCKH"]
        elif "Other" in search_scope and "Other" in target_dfs:
            target_search_dict["Other"] = target_dfs["Other"]
        else:
            target_search_dict = target_dfs

        raw_keywords = [k.strip() for k in re.split(r"[&,]", keyword_input) if k.strip()]
        
        for name, df in target_search_dict.items():
            if df is None or df.empty:
                continue
            df_temp = df.copy()
            df_temp.columns = [str(c).strip() for c in df_temp.columns]
            
            mask = pd.Series(True, index=df_temp.index)
            for kw in raw_keywords:
                mask_kw = pd.Series(False, index=df_temp.index)
                for c in df_temp.columns:
                    mask_kw |= df_temp[c].str.lower().str.contains(kw, case=False, na=False)
                mask &= mask_kw
            
            match_df = df_temp[mask].copy()
            if not match_df.empty:
                match_df["_source_table"] = name
                found_records.append((name, match_df))

        if found_records:
            st.success(f"✅ Tìm thấy kết quả phù hợp từ {len(found_records)} nhóm bảng.")
        else:
            st.warning("❌ Không tìm thấy dữ liệu phù hợp hoặc bạn không có quyền truy cập.")
    else:
        st.info("👆 Nhập từ khóa để bắt đầu tra cứu trong phạm vi dữ liệu được phép.")

    with col_refresh2:
        if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
            st.cache_data.clear()
            for k in ["df1", "df2", "detail_dfs", "filtered_detail_dfs"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    st.divider()

    if search_scope == "🌐 Tất cả các bảng":
        if found_records:
            st.markdown("#### 📂 KẾT QUẢ TÌM KIẾM")
            for name, rec_df in found_records:
                st.markdown(f"##### 📘 Nhóm kết quả từ bảng: **{name}** — {len(rec_df)} dòng")
                with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                    st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("ℹ️ Nhập từ khóa để hiển thị kết quả.")
    else:
        # Gom các bảng hợp lệ để thống kê theo phân quyền
        valid_dfs = [df for name, df in found_records if not df.empty] if found_records else [df for df in target_dfs.values() if df is not None and not df.empty]
        total_rec_df = pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()

        if not total_rec_df.empty:
            st.markdown("#### 📈 THỐNG KÊ VÀ PHÂN TÍCH THEO QUYỀN HẠN")
            # Logic thống kê, vẽ biểu đồ chi tiết giữ nguyên theo cấu trúc chuẩn của app
            tiet_col_target = next((c for c in total_rec_df.columns if any(x in c.lower() for x in ["sỐ tiết kê khai", "tiết", "period"])), None)
            time_col_target = next((c for c in total_rec_df.columns if any(x in c.lower() for x in ["đợt kê khai", "năm học", "year"])), None)

            if tiet_col_target and time_col_target:
                total_rec_df[tiet_col_target] = pd.to_numeric(total_rec_df[tiet_col_target], errors="coerce").fillna(0)
                total_rec_df["Năm học"] = total_rec_df[time_col_target].apply(quy_doi_nam_hoc)
                
                st.dataframe(total_rec_df, use_container_width=True)
            else:
                st.dataframe(total_rec_df, use_container_width=True)
        else:
            st.warning("⚠️ Không có dữ liệu nào khả dụng với quyền hiện tại của bạn.")

with tab2:
    st.markdown("#### 📂 Dữ liệu gốc được phân quyền theo tài khoản")
    detail_dfs = st.session_state.get("filtered_detail_dfs", {})
    
    if detail_dfs:
        selected_group_view = st.radio(
            "Chọn nhóm công việc muốn xem:",
            options=["GD (Giảng dạy)", "NCKH (Nghiên cứu)", "Other (Khác)"],
            horizontal=True,
            key="radio_group_view"
        )
        key_mapping_view = {"GD (Giảng dạy)": "GD", "NCKH (Nghiên cứu)": "NCKH", "Other (Khác)": "Other"}
        chosen_key_view = key_mapping_view[selected_group_view]
        
        if chosen_key_view in detail_dfs:
            df_show = detail_dfs[chosen_key_view]
            st.success(f"✅ Đang hiển thị dữ liệu phân quyền nhóm: {selected_group_view} ({len(df_show)} dòng)")
            with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                st.dataframe(df_show, height=450, use_container_width=True)
        else:
            st.warning("⚠️ Không có dữ liệu hoặc bạn không có quyền xem nhóm này.")
    else:
        st.error("❌ Không thể tải dữ liệu chi tiết.")
