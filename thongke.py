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
            "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,). Ví dụ: Quản lý danh mục đầu tư hoặc Toán cao cấp"
        )
        .strip()
        .lower()
    )
    st.caption("💡 Mẹo: Để xem thông tin toàn khoa theo từng nội dung, gõ GD hoặc NCKH")
    
    df1 = st.session_state.get("df1")
    df2 = st.session_state.get("df2")
    detail_dfs = st.session_state.get("detail_dfs", {})

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

                # Nếu chọn "🌐 Tất cả các bảng", hiển thị danh sách các bảng gốc ban đầu
                if search_scope == "🌐 Tất cả các bảng":
                    for name, rec_df in found_records:
                        st.markdown(
                            f"#### 📘 Nhóm kết quả tìm thấy từ bảng dữ liệu gốc: **{name}** —"
                            f" {len(rec_df)} dòng"
                        )
                        with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                            st.dataframe(rec_df, use_container_width=True)
                else:
                    for name, rec_df in found_records:
                        st.markdown(
                            f"#### 📘 Nhóm kết quả tìm thấy từ bảng dữ liệu gốc: **{name}** —"
                            f" {len(rec_df)} dòng"
                        )
                        with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                            st.dataframe(rec_df, use_container_width=True)
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

    if not total_rec_df.empty:
        st.markdown("#### 📈 THỐNG KÊ VÀ XỬ LÝ DỮ LIỆU ĐẶC THÙ")

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
            total_rec_df["Năm học hiển thị"] = total_rec_df[time_col_target].apply(
                quy_doi_nam_hoc
            )

            all_years = sorted(
                total_rec_df["Năm học hiển thị"].dropna().unique().tolist(),
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
                    total_rec_df["Năm học hiển thị"].isin(selected_years)
                ]

                if total_rec_df.empty:
                    st.warning("❌ Không có dữ liệu cho năm học đã chọn.")
                else:
                    # PHÂN NHÁNH XỬ LÝ DỰA TRÊN PHẠM VI (SEARCH_SCOPE) HOẶC _SOURCE_TABLE
                    is_only_gd = (
                        ("GD" in search_scope) or 
                        ("_source_table" in total_rec_df.columns and (total_rec_df["_source_table"] == "GD").all())
                    )
                    is_only_nckh = (
                        ("NCKH" in search_scope) or 
                        ("_source_table" in total_rec_df.columns and (total_rec_df["_source_table"] == "NCKH").all())
                    )
                    is_only_other = (
                        ("Other" in search_scope) or 
                        ("_source_table" in total_rec_df.columns and (total_rec_df["_source_table"] == "Other").all())
                    )

                    # NẾU LÀ TẤT CẢ CÁC BẢNG -> HIỂN THỊ TỪNG PHẦN GỌN GÀNG THEO YÊU CẦU
                    if search_scope == "🌐 Tất cả các bảng":
                        st.markdown("---")
                        st.markdown("### 📊 TỔNG HỢP NỘI DUNG: GIẢNG DẠY (GD)")
                        df_gd_all = total_rec_df[total_rec_df["_source_table"] == "GD"].copy() if "_source_table" in total_rec_df.columns else total_rec_df.copy()
                        if not df_gd_all.empty:
                            df_clean = df_gd_all.drop_duplicates().copy()
                            df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]
                            if "term_x" in df_clean.columns:
                                df_clean["term"] = df_clean["term_x"]
                            
                            time_col_actual = next((c for c in df_clean.columns if any(x in c for x in ["năm học", "year", "đợt", "term"])), None)
                            df_clean["năm học hiển thị"] = df_clean[time_col_actual].apply(quy_doi_nam_hoc) if time_col_actual else "Chưa xác định"
                            tiet_col = next((c for c in df_clean.columns if any(x in c for x in ["tiết", "period"])), list(df_clean.columns)[-1])
                            df_clean[tiet_col] = pd.to_numeric(df_clean[tiet_col], errors="coerce").fillna(0)
                            c_class = "class" if "class" in df_clean.columns else df_clean.columns[0]
                            c_subject = "subject" if "subject" in df_clean.columns else df_clean.columns[0]

                            df_after = df_clean.groupby("năm học hiển thị").agg(**{
                                "Tổng số tiết thực hiện": (tiet_col, "sum"),
                                "Số lượng lớp": (c_class, "nunique"),
                                "Số lượng môn học": (c_subject, "nunique")
                            }).reset_index().sort_values("năm học hiển thị").rename(columns={"năm học hiển thị": "Năm học hiển thị"})
                            st.dataframe(df_after, use_container_width=True)
                        else:
                            st.info("ℹ️ Không có dữ liệu Giảng dạy.")

                        st.markdown("---")
                        st.markdown("### 📊 TỔNG HỢP NỘI DUNG: NGHIÊN CỨU KHOA HỌC (NCKH)")
                        df_nckh_all = total_rec_df[total_rec_df["_source_table"] == "NCKH"].copy() if "_source_table" in total_rec_df.columns else pd.DataFrame()
                        if not df_nckh_all.empty:
                            df_temp_detail = df_nckh_all.copy()
                            df_temp_detail.columns = [str(c).strip() for c in df_temp_detail.columns]
                            
                            name_prod_col = next((c for c in df_temp_detail.columns if c.lower() in ["tên sản phẩm"]), None)
                            id_col_check = next((c for c in df_temp_detail.columns if c.lower() in ["mã sản phẩm", "code"]), None)
                            role_col_check = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["vai trò", "role"])), None)

                            if name_prod_col and not df_temp_detail.empty:
                                df_temp_detail["_clean_prod_name"] = df_temp_detail[name_prod_col].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
                            else:
                                df_temp_detail["_clean_prod_name"] = "sản phẩm chung"

                            if id_col_check and id_col_check in df_temp_detail.columns:
                                df_temp_detail["_clean_id"] = df_temp_detail[id_col_check].astype(str).str.lower().str.replace(r"\s+", "", regex=True).str.strip()
                                df_temp_detail["_clean_key"] = df_temp_detail["_clean_prod_name"] + " | " + df_temp_detail["_clean_id"]
                            else:
                                df_temp_detail["_clean_key"] = df_temp_detail["_clean_prod_name"]

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
                            group_keys_final = ["Năm học hiển thị", "Sản phẩm chuẩn hóa"]
                            if role_col_check and role_col_check in df_temp_detail.columns:
                                group_keys_final.append(role_col_check)

                            agg_rules_detail = {tiet_col_target: "first"}
                            df_clean_unified = df_temp_detail.groupby(group_keys_final, dropna=False).agg(agg_rules_detail).reset_index()

                            df_after_nckh = df_clean_unified.groupby("Năm học hiển thị").agg(**{
                                "Số lượng sản phẩm độc lập": (tiet_col_target, "count"),
                                "Tổng số tiết thực hiện": (tiet_col_target, "sum")
                            }).reset_index().sort_values("Năm học hiển thị")
                            st.dataframe(df_after_nckh, use_container_width=True)
                        else:
                            st.info("ℹ️ Không có dữ liệu Nghiên cứu khoa học.")

                        st.markdown("---")
                        st.markdown("### 📊 TỔNG HỢP NỘI DUNG: CÔNG TÁC KHÁC (OTHER)")
                        df_other_all = total_rec_df[total_rec_df["_source_table"] == "Other"].copy() if "_source_table" in total_rec_df.columns else pd.DataFrame()
                        if not df_other_all.empty:
                            st.dataframe(df_other_all, use_container_width=True)
                        else:
                            st.info("ℹ️ Không có dữ liệu Công tác khác.")

                    # NẾU CHỌN RIÊNG GD
                    elif is_only_gd:
                        df_clean = total_rec_df.drop_duplicates().copy()
                        df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]
                        if "term_x" in df_clean.columns:
                            df_clean["term"] = df_clean["term_x"]

                        code_col_actual = next((c for c in df_clean.columns if "code" in c), None)
                        df_clean["_dot_hoc"] = df_clean[code_col_actual].astype(str).str.upper().apply(
                            lambda x: "Đợt 1" if "D1" in x or "ĐỢT 1" in x else ("Đợt 2" if "D2" in x or "ĐỢT 2" in x else "Khác")
                        ) if code_col_actual else "Không rõ"

                        time_col_actual = next((c for c in df_clean.columns if any(x in c for x in ["năm học", "year", "đợt", "term"])), None)
                        df_clean["năm học hiển thị"] = df_clean[time_col_actual].apply(quy_doi_nam_hoc) if time_col_actual else "Chưa xác định"

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
                        df_clean["_full_name"] = df_clean[surname_col].astype(str) + " " + df_clean[name_col].astype(str) if name_col and surname_col else (df_clean[name_col].astype(str) if name_col else "Không rõ")

                        # Bảng 1: Tổng hợp Giảng dạy theo Năm học
                        df_after = df_clean.groupby("năm học hiển thị").agg(**{
                            "Tổng số tiết thực hiện": (tiet_col, "sum"),
                            "Số lượng lớp": (c_class, "nunique"),
                            "Số lượng môn học": (c_subject, "nunique")
                        }).reset_index().sort_values("năm học hiển thị").rename(columns={"năm học hiển thị": "Năm học hiển thị"})

                        st.markdown("##### 🧹 1. Bảng tổng hợp Giảng dạy theo Năm học")
                        tot_lop = df_after["Số lượng lớp"].sum()
                        tot_tiet = df_after["Tổng số tiết thực hiện"].sum()
                        df_after_disp = df_after.copy()
                        df_after_disp.loc[len(df_after_disp)] = ["**Tổng cộng**", tot_tiet, tot_lop, float('nan')]
                        df_after_disp = df_after_disp[["Năm học hiển thị", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]]
                        st.dataframe(df_after_disp, use_container_width=True)

                        # Bảng tổng hợp theo Giảng viên
                        st.markdown("##### 👥 Bảng tổng hợp khối lượng giảng dạy theo từng Giảng viên")
                        available_years_gd = sorted(df_clean["năm học hiển thị"].dropna().unique().tolist(), reverse=True)
                        selected_years_gv = st.multiselect(
                            "📅 Chọn năm học hiển thị cho bảng giảng viên (Bỏ trống = Chọn tất cả):",
                            options=available_years_gd,
                            default=available_years_gd,
                            key="multiselect_gv_years"
                        )
                        df_gv_filtered = df_clean[df_clean["năm học hiển thị"].isin(selected_years_gv)] if selected_years_gv else df_clean.copy()

                        if not df_gv_filtered.empty:
                            df_gv_summary = df_gv_filtered.groupby(["_full_name", "năm học hiển thị"]).agg(
                                Số_lượng_môn=(c_subject, "nunique"),
                                Tổng_số_lớp=(c_class, "nunique"),
                                Tổng_số_tiết=(tiet_col, "sum")
                            ).reset_index().rename(columns={"_full_name": "Giảng viên", "năm học hiển thị": "Năm học", "Số_lượng_môn": "Số lượng môn đã giảng", "Tổng_số_lớp": "Tổng số lớp", "Tổng_số_tiết": "Tổng số tiết"})

                            list_gv_final = []
                            for gv, group in df_gv_summary.groupby("Giảng viên"):
                                list_gv_final.append(group)
                                if len(selected_years_gv) >= 2 and len(group) > 1:
                                    df_gv_single = df_gv_filtered[df_gv_filtered["_full_name"] == gv]
                                    total_row_gv = pd.DataFrame({
                                        "Giảng viên": [f"**Tổng cộng ({gv})**"],
                                        "Năm học": [""],
                                        "Số lượng môn đã giảng": [df_gv_single[c_subject].nunique()],
                                        "Tổng số lớp": [df_gv_single[c_class].nunique()],
                                        "Tổng số tiết": [df_gv_single[tiet_col].sum()]
                                    })
                                    list_gv_final.append(total_row_gv)

                            df_gv_display = pd.concat(list_gv_final, ignore_index=True)
                            total_row_all = pd.DataFrame({
                                "Giảng viên": ["**Tổng cộng toàn khoa**"],
                                "Năm học": [""],
                                "Số lượng môn đã giảng": [df_gv_filtered[c_subject].nunique()],
                                "Tổng số lớp": [df_gv_filtered[c_class].nunique()],
                                "Tổng số tiết": [df_gv_filtered[tiet_col].sum()]
                            })
                            df_gv_display = pd.concat([df_gv_display, total_row_all], ignore_index=True)
                            with st.expander("📅 **(Bấm để mở/đóng xem tổng hợp khối lượng giảng viên)**", expanded=True):
                                st.dataframe(df_gv_display, use_container_width=True, hide_index=True)

                    # NẾU CHỌN RIÊNG NCKH
                    elif is_only_nckh:
                        df_temp_detail = total_rec_df.copy()
                        df_temp_detail.columns = [str(c).strip() for c in df_temp_detail.columns]

                        tap_chi_col = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["tạp chí", "tap chi", "hội thảo", "hoi thao", "sách", "sach"])), None)
                        name_prod_col = next((c for c in df_temp_detail.columns if c.lower() in ["tên sản phẩm"]), None)
                        id_col_check = next((c for c in df_temp_detail.columns if c.lower() in ["mã sản phẩm", "code"]), None)
                        name_col_check = next((c for c in df_temp_detail.columns if c.lower() == "name"), None)
                        surname_col_check = next((c for c in df_temp_detail.columns if c.lower() == "surname"), None)
                        role_col_check = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["vai trò", "role"])), None)

                        phan_loai_col = next((c for c in df_temp_detail.columns if "phân loại cấp 1" in c.lower()), None)
                        phan_loai_2 = next((c for c in df_temp_detail.columns if "phân loại cấp 2" in c.lower()), None)
                        phan_loai_3 = next((c for c in df_temp_detail.columns if "phân loại cấp 3" in c.lower()), None)
                        col_isbn_init = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["isbn", "issn"])), None)

                        df_temp_detail["_clean_prod_name"] = df_temp_detail[name_prod_col].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip() if name_prod_col else "sản phẩm chung"
                        if id_col_check and id_col_check in df_temp_detail.columns:
                            df_temp_detail["_clean_id"] = df_temp_detail[id_col_check].astype(str).str.lower().str.replace(r"\s+", "", regex=True).str.strip()
                            df_temp_detail["_clean_key"] = df_temp_detail["_clean_prod_name"] + " | " + df_temp_detail["_clean_id"]
                        else:
                            df_temp_detail["_clean_key"] = df_temp_detail["_clean_prod_name"]

                        df_temp_detail["_full_name"] = (df_temp_detail[surname_col_check].astype(str) + " " + df_temp_detail[name_col_check].astype(str)) if name_col_check and surname_col_check else (df_temp_detail[name_col_check].astype(str) if name_col_check else "Không rõ")

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

                        group_keys_final = ["Năm học hiển thị", "Sản phẩm chuẩn hóa"]
                        if phan_loai_col:
                            group_keys_final.insert(0, phan_loai_col)
                        if loai_hd_col and loai_hd_col not in group_keys_final:
                            group_keys_final.insert(1, loai_hd_col)

                        agg_rules_detail = {tiet_col_target: "first", "_full_name": lambda x: ", ".join(x.dropna().unique())}
                        if cap_do_col: agg_rules_detail[cap_do_col] = "first"
                        if name_prod_col: agg_rules_detail[name_prod_col] = lambda x: " / ".join(x.dropna().unique())
                        if id_col_check: agg_rules_detail[id_col_check] = lambda x: " / ".join(x.dropna().unique())
                        if role_col_check: agg_rules_detail[role_col_check] = lambda x: " & ".join(x.dropna().unique())

                        if tap_chi_col: agg_rules_detail[tap_chi_col] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                        if phan_loai_2: agg_rules_detail[phan_loai_2] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                        if phan_loai_3: agg_rules_detail[phan_loai_3] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())
                        if col_isbn_init: agg_rules_detail[col_isbn_init] = lambda x: " / ".join(pd.Series(x).dropna().astype(str).unique())

                        df_clean_unified = df_temp_detail.groupby(group_keys_final, dropna=False).agg(agg_rules_detail).reset_index()

                        st.markdown("##### 🧹 2.1 Bảng thống kê SAU KHI trừ trùng lặp")
                        df_after = df_clean_unified.groupby("Năm học hiển thị").agg(**{
                            "Số lượng sản phẩm độc lập": (tiet_col_target, "count"),
                            "Tổng số tiết thực hiện": (tiet_col_target, "sum")
                        }).reset_index().sort_values("Năm học hiển thị")
                        st.dataframe(df_after, use_container_width=True)

                    # NẾU CHỌN RIÊNG OTHER
                    elif is_only_other:
                        st.markdown("##### 📌 Bảng dữ liệu công tác khác (Other)")
                        st.dataframe(total_rec_df, use_container_width=True)

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
