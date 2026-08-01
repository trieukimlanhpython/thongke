#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 20:50:24 2025
📋 Ứng dụng Quản lý Công việc (QLCV)
streamlit run "/Users/trieukimlanh/Library/CloudStorage/GoogleDrive-trieukimlanh@gmail.com/My Drive/Từ OneDrive/Spyder/app_QLCV/thongke.py"
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

# ==========================================================
# ⚙️ CẤU HÌNH APPS
# ==========================================================
st.set_page_config(page_title="📋 Ứng dụng QLCV", layout="wide")
st.title("📋 Ứng dụng Quản lý Công việc")
st.write(
    "Đây là ứng dụng nhằm tổng hợp thông tin công việc từ giảng dạy, nghiên cứu khoa học và công tác khác."
)

# ==========================================================
# 🔄 NÚT CẬP NHẬT / LÀM MỚI DỮ LIỆU (REFRESH CACHE)
# ==========================================================
col_refresh1, col_refresh2 = st.columns([4, 1])
with col_refresh2:
  if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
    st.cache_data.clear()

    keys_to_reset = ["df1", "df2", "detail_dfs", "selected_years_stat"]
    for k in keys_to_reset:
      if k in st.session_state:
        del st.session_state[k]

    status_placeholder = st.empty()
    status_placeholder.success("✅ Updated!")
    time.sleep(2)
    status_placeholder.empty()
    st.rerun()

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
# 🧩 HÀM ĐỌC GOOGLE SHEET (ĐÃ CẢI TIẾN & BẮT LỖI CHI TIẾT)
# ==========================================================
@st.cache_data(ttl=600)
def read_gsheet(link):
  try:
    df = pd.read_csv(link)
    if df.empty:
      st.warning(f"⚠️ File CSV tải về từ link đang trống (0 dòng): {link}")
      return None
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.select_dtypes(include=["object"]).columns:
      df[col] = df[col].fillna("").astype(str)

    return df
  except Exception as e:
    st.error(f"❌ Lỗi đọc Google Sheet từ link `{link}`: {e}")
    return None

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
# 🧮 LƯU TRỮ VÀ KHỞI TẠO DỮ LIỆU VÀO SESSION STATE AN TOÀN
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

# ==========================================================
# 📑 TẠO GIAO DIỆN 2 TAB CHÍNH
# ==========================================================
tab1, tab2 = st.tabs([
    "🔍 1. Tra cứu công việc nâng cao", 
    "📂 2. Dữ liệu gốc"
])

# ----------------------------------------------------------
# TAB 1: TRA CỨU CÔNG VIỆC NÂNG CAO & THỐNG KÊ
# ----------------------------------------------------------
with tab1:
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

    keyword_input = (
        st.text_input(
            "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)"
        )
        .strip()
        .lower()
    )
    # 🌟 Bổ sung dòng mô tả thứ hai ở đây
    st.caption("💡 Mẹo: Để xem thông tin toàn khoa theo từng nội dung, gõ GD hoặc NCKH")
    
    df1 = st.session_state.get("df1")
    df2 = st.session_state.get("df2")
    detail_dfs = st.session_state.get("detail_dfs", {})

    found_records = []

    if keyword_input:
        if df1 is None or df1.empty or df2 is None or df2.empty or not detail_dfs:
            st.warning("⚠️ Vui lòng đảm bảo đã tải đủ df1, df2 và các bảng công việc.")
        else:
            # 1. Tách từ khóa chuẩn xác theo dấu phẩy hoặc dấu & (Giữ nguyên cụm từ người dùng gõ)
            raw_keywords = [
                k.strip() for k in re.split(r"[&,]", keyword_input) if k.strip()
            ]

            # 2. Xử lý từ đồng nghĩa thông minh cho toàn vẹn cụm từ
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
                                # Kiểm tra xem cột có chứa chính xác cụm từ khóa (không bị tách nhỏ)
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
    if found_records:
        valid_dfs = [df for name, df in found_records if not df.empty]
        total_rec_df = (
            pd.concat(valid_dfs, ignore_index=True)
            if valid_dfs
            else pd.DataFrame()
        )
    else:
        total_rec_df = pd.DataFrame()

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

    # NẾU CHỌN "🌐 TẤT CẢ CÁC BẢNG" -> CHỈ HIỂN THỊ CÁC BẢNG GỐC, KHÔNG VẼ ĐỒ THỊ HAY THỐNG KÊ GÌ KHÁC
    if search_scope == "🌐 Tất cả các bảng":
        if found_records:
            st.markdown("#### 📂 KẾT QUẢ TÌM KIẾM DỮ LIỆU TỪ CÁC BẢNG")
            for name, rec_df in found_records:
                st.markdown(f"##### 📘 Nhóm kết quả từ bảng dữ liệu gốc: **{name}** — {len(rec_df)} dòng")
                with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                    st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("ℹ️ Nhập từ khóa để hiển thị kết quả tìm kiếm.")

    # NẾU CHỌN TỪNG MỤC RIÊNG LẺ (GD, NCKH, OTHER) -> GIỮ NGUYÊN LUỒNG THỐNG KÊ VÀ ĐỒ THỊ NHƯ CŨ
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
                                             
                                            for p in ax2.patches if 'ax2' in locals() else ax_y2.patches:
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
                            # 🔬 XỬ LÝ RIÊNG CHO KHỐI NCKH
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
                            
                            st.markdown("##### 📋 1. Bảng thống kê TRƯỚC khi trừ trùng lặp")
                            with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                                df_before = total_rec_df.groupby("Năm học").agg(**{
                                    "Tổng số dòng kê khai": (tiet_col_target, "count"),
                                    "Tổng số tiết": (tiet_col_target, "sum")
                                }).reset_index().sort_values("Năm học")
            
                                tot_d_b = df_before["Tổng số dòng kê khai"].sum()
                                tot_t_b = df_before["Tổng số tiết"].sum()
                                df_before_disp = df_before.copy()
                                df_before_disp.loc[len(df_before_disp)] = ["**Tổng cộng**", tot_d_b, tot_t_b]
                                st.dataframe(df_before_disp, use_container_width=True)

                            st.markdown("##### 🧹 2.1 Bảng thống kê SAU KHI trừ trùng lặp")
                           
                            # Nhận diện các cột phân loại cấp 1, loại hoạt động và cấp độ từ df_clean_unified
                            pl1_col = next((c for c in df_clean_unified.columns if "phân loại cấp 1" in c.lower()), None)
                            loai_hd_col = next((c for c in df_clean_unified.columns if any(x in c.lower() for x in ["loại hoạt động", "loại"])), None)
                            cap_do_col = next((c for c in df_clean_unified.columns if c.lower() == "cấp độ" or "cấp độ" in c.lower() or "cấp" in c.lower()), None)

                            # Hàm phân loại chi tiết được nới rộng từ khóa để bắt chuẩn xác 100%
                            def phan_loai_chi_tiet_nckh(row):
                                pl1_val = str(row.get(pl1_col, "")).lower() if pl1_col else ""
                                loai_val = str(row.get(loai_hd_col, "")).lower() if loai_hd_col else ""
                                cap_val = str(row.get(cap_do_col, "")).lower() if cap_do_col else ""
                                
                                # Gộp toàn bộ thông tin của dòng để quét từ khóa diện rộng
                                text_val = f"{pl1_val} | {loai_val} | {cap_val}"

                                # 1. Giáo trình mới
                                gt_moi = 1 if ("giáo trình" in text_val and "mới" in text_val) else 0
                                
                                # 2. Sách chuyên khảo
                                sach_ck = 1 if ("chuyên khảo" in text_val) else 0
                                
                                # 3. Sách tham khảo / TLTK / HD học tập
                                sach_tltk = 1 if any(x in text_val for x in ["sách tham khảo", "tltk", "hướng dẫn học tập"]) else 0
                                
                                # 4 & 5. Nhận diện Bài báo trong nước và quốc tế
                                # Kiểm tra xem dòng có phải là bài báo hay không (quét cả loại hoạt động lẫn phân loại cấp 1)
                                la_bai_bao = any(x in text_val for x in ["bài báo", "journal", "proceeding", "hội nghị", "hội thảo"])
                                
                                # Bài báo trong nước: Là bài báo và có từ khóa trong nước / quốc gia / bộ / cơ sở / trường
                                bb_vn = 1 if (la_bai_bao and any(x in text_val for x in ["trong nước", "quốc gia", "địa phương", "bộ", "cơ sở", "trường"])) and not any(x in text_val for x in ["quốc tế", "isi", "scopus", "scie", "ssci", "wos"]) else 0
                                
                                # Bài báo quốc tế: Là bài báo và có từ khóa quốc tế / ISI / Scopus / Scie...
                                bb_qt = 1 if (la_bai_bao and any(x in text_val for x in ["quốc tế", "isi", "scopus", "scie", "ssci", "wos", " international"])) else 0

                                return pd.Series([gt_moi, sach_ck, sach_tltk, bb_vn, bb_qt])

                            df_clean_unified[["_gt_moi", "_sach_ck", "_sach_tltk", "_bb_vn", "_bb_qt"]] = df_clean_unified.apply(phan_loai_chi_tiet_nckh, axis=1)

                            # Tổng hợp Bảng 2.1 dựa trên dữ liệu chuẩn đã trừ trùng lặp (Dùng "Năm học hiển thị" chuẩn của app)
                            df_after = df_clean_unified.groupby("Năm học").agg(**{
                                "Số lượng sản phẩm": (tiet_col_target, "count"),
                                "Tổng số tiết": (tiet_col_target, "sum"),
                                "Giáo trình mới": ("_gt_moi", "sum"),
                                "Sách chuyên khảo": ("_sach_ck", "sum"),
                                "Sách tham khảo": ("_sach_tltk", "sum"),
                                "Bài báo trong nước": ("_bb_vn", "sum"),
                                "Bài báo quốc tế": ("_bb_qt", "sum"),
                            }).reset_index().sort_values("Năm học")

                            tot_sp_a = df_after["Số lượng sản phẩm"].sum()
                            tot_t_a = df_after["Tổng số tiết"].sum()
                            tot_gt_moi = df_after["Giáo trình mới"].sum()
                            tot_sach_ck = df_after["Sách chuyên khảo"].sum()
                            tot_sach_tltk = df_after["Sách tham khảo"].sum()
                            tot_bb_vn = df_after["Bài báo trong nước"].sum()
                            tot_bb_qt = df_after["Bài báo quốc tế"].sum()

                            df_after_disp = df_after.copy()
                            df_after_disp.loc[len(df_after_disp)] = [
                                "**Tổng cộng**", 
                                tot_sp_a, 
                                tot_t_a, 
                                tot_gt_moi, 
                                tot_sach_ck, 
                                tot_sach_tltk, 
                                tot_bb_vn, 
                                tot_bb_qt
                            ]
                            st.dataframe(df_after_disp, use_container_width=True)

                            st.markdown("##### 🔍 2.3 Bảng chi tiết NCKH tùy chỉnh theo tiêu chí")

                            cols_lower_all = {str(c).strip().lower(): c for c in df_clean_unified.columns}
                            col_ma_sp = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["mã sản phẩm", "ma san pham", "code"])), None)
                            
                            col_tap_chi = next(
                                (
                                    c for c in df_clean_unified.columns
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
                            col_phan_loai_2 = next((cols_lower_all[c] for c in cols_lower_all if "phân loại cấp 2" in c), None)
                            col_phan_loai_3 = next((cols_lower_all[c] for c in cols_lower_all if "phân loại cấp 3" in c), None)
                            col_isbn = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["isbn", "issn"])), None)

                            with st.expander("⚙️ **Chọn tiêu chí gom nhóm (Bấm để mở/đóng)**", expanded=False):
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

                            # 🌟 Lọc bỏ các cột trùng lặp tên trong danh sách group_detail_dynamic để tránh lỗi duplicate index
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
                            # 📊 3. BIỂU ĐỒ TRỰC QUAN ĐỘNG CHO NCKH
                            # ==========================================
                            first_col_nckh = df_nckh_detail.columns[0]
                            df_plot_nckh = df_nckh_detail[df_nckh_detail[first_col_nckh] != "**Tổng cộng**"].copy()
                             
                            if not df_plot_nckh.empty:
                                st.markdown("##### 📊 3. Biểu đồ trực quan theo các tiêu chí đã chọn (Dựa trên dữ liệu đã trừ trùng lặp)")
                                
                                has_year_nckh = "Năm học" in df_nckh_detail.columns
                                
                                allowed_mapping = []
                                if opt_y and has_year_nckh:
                                    allowed_mapping.append(("Năm học", "Năm học"))
                                if opt_cap and cap_do_col and cap_do_col in df_nckh_detail.columns:
                                    allowed_mapping.append((cap_do_col, "Cấp độ"))
                                if opt_loai and loai_hd_col and loai_hd_col in df_nckh_detail.columns:
                                    allowed_mapping.append((loai_hd_col, "Loại HĐ"))
                                if opt_role and role_col_check and role_col_check in df_nckh_detail.columns:
                                    allowed_mapping.append((role_col_check, "Vai trò"))
                                if opt_pl1 and phan_loai_col and phan_loai_col in df_nckh_detail.columns:
                                    allowed_mapping.append((phan_loai_col, "PL Cấp 1"))
                                
                                for col_name, display_name in allowed_mapping:
                                    if col_name not in df_plot_nckh.columns:
                                        continue
                                     
                                    st.markdown(f"###### 📌 Phân tích theo tiêu chí: **{display_name}**")
                                     
                                    df_nckh_filtered = df_plot_nckh.copy()
                                    unique_vals_nckh = sorted(df_plot_nckh[col_name].astype(str).unique())
                                    selected_vals_nckh = st.multiselect(
                                        f"🎯 Lọc {display_name} hiển thị trên biểu đồ (Bỏ trống = Hiện toàn bộ):",
                                        options=unique_vals_nckh,
                                        key=f"filter_nckh_{col_name}"
                                    )
                                    if selected_vals_nckh:
                                        df_nckh_filtered = df_nckh_filtered[df_nckh_filtered[col_name].astype(str).isin(selected_vals_nckh)]
                                     
                                    if df_nckh_filtered.empty:
                                        st.warning(f"⚠️ Không có dữ liệu phù hợp với bộ lọc cho tiêu chí **{display_name}**.")
                                        continue
                                     
                                    col_chart1, col_chart2 = st.columns(2)
                                     
                                    if col_name != "Năm học" and has_year_nckh:
                                        df_pivot_qty = df_nckh_filtered.pivot_table(index=col_name, columns="Năm học", values="Số lượng", aggfunc="sum").fillna(0)
                                        df_pivot_tiet = df_nckh_filtered.pivot_table(index=col_name, columns="Năm học", values="Tổng số tiết", aggfunc="sum").fillna(0)
                                        is_grouped_years = True
                                    else:
                                        df_pivot_qty = df_nckh_filtered.groupby(col_name)[["Số lượng"]].sum()
                                        df_pivot_tiet = df_nckh_filtered.groupby(col_name)[["Tổng số tiết"]].sum()
                                        is_grouped_years = False
                                     
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
                                                           xytext=(0, 2),
                                                           textcoords='offset points')
                                         
                                        ax1.set_xlabel("Ký hiệu" if needs_mapping else display_name, fontsize=9)
                                        ax1.set_ylabel("Số lượng sản phẩm", fontsize=9)
                                        ax1.set_title(f"So sánh Số lượng theo {display_name} qua các Năm", fontsize=10, fontweight="bold")
                                        ax1.tick_params(axis="x", rotation=45 if num_bars_nckh > 8 else 0)
                                        if is_grouped_years:
                                            ax1.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax1.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig1, bbox_inches="tight")
                                     
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
                                                           xytext=(0, 2),
                                                           textcoords='offset points')
                                         
                                        ax2.set_xlabel("Ký hiệu" if needs_mapping else display_name, fontsize=9)
                                        ax2.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
                                        ax2.set_title(f"So sánh Tổng số tiết theo {display_name} qua các Năm", fontsize=10, fontweight="bold")
                                        ax2.tick_params(axis="x", rotation=45 if num_bars_nckh > 8 else 0)
                                        if is_grouped_years:
                                            ax2.legend(title="Năm học", fontsize=8, title_fontsize=8)
                                        ax2.grid(axis="y", linestyle="--", alpha=0.5)
                                        st.pyplot(fig2, bbox_inches="tight")
                                     
                                    if needs_mapping:
                                        st.markdown(f"**📝 Chú thích ký hiệu trục hoành cho ({display_name}):**")
                                        with st.expander(f"📅 **(Bấm để mở/đóng)**", expanded=True):
                                            note_df = pd.DataFrame(list(label_mapping.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                            st.dataframe(note_df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Không tìm thấy cột 'SỐ TIẾT KÊ KHAI' hoặc cột thời gian phù hợp để vẽ biểu đồ.")
        else:
            st.info("ℹ️ Nhập từ khóa để hiển thị kết quả phân tích.")

# ----------------------------------------------------------
# TAB 2: DỮ LIỆU GỐC (GỘP TỪ DỮ LIỆU CÁC NHÓM CÔNG VIỆC & DỮ LIỆU MÔ TẢ)
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
    
    st.markdown("#### 📘 Dữ liệu các nhóm công việc GD, NCKH, Other")
    detail_dfs = st.session_state.get("detail_dfs", {})

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
        st.warning(f"⚠️ Nhóm {selected_group_view} hiện chưa có dữ liệu.")
    else:
      st.error("❌ Không thể tải dữ liệu chi tiết từ Google Sheets.")
