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
# 📑 TẠO GIAO DIỆN 3 TAB CHÍNH
# ==========================================================
tab1, tab2, tab3 = st.tabs([
    "🔍 1. Tra cứu công việc nâng cao", 
    "📘 2. Dữ liệu các nhóm công việc", 
    "📂 3. Dữ liệu mô tả"
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
            "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)\nVí dụ: Quản lý danh mục đầu tư hoặc Toán cao cấp"
        )
        .strip()
        .lower()
    )

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

          for name, rec_df in found_records:
            st.markdown(
                f"#### 📘 Nhóm kết quả tìm thấy từ bảng dữ liệu gốc: **{name}** —"
                f" {len(rec_df)} dòng"
            )
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
    
                        # 🌟 Quét và chuẩn hóa chuẩn xác cột term (bao gồm cả trường hợp term_x, term_y hoặc viết hoa)
                        term_actual_col = next((c for c in df_clean.columns if "term" in c), None)
                        if term_actual_col:
                            df_clean["term"] = df_clean[term_actual_col].astype(str).str.strip()
                        else:
                            df_clean["term"] = "Không rõ"
    
                        time_col_actual = next((c for c in df_clean.columns if any(x in c for x in ["năm học", "year", "đợt"])), None)
                        if "năm học hiển thị" not in df_clean.columns and time_col_actual:
                            df_clean["năm học hiển thị"] = df_clean[time_col_actual].apply(quy_doi_nam_hoc)
                        elif "năm học hiển thị" not in df_clean.columns:
                            df_clean["năm học hiển thị"] = "Chưa xác định"
    
                        tiet_col = next((c for c in df_clean.columns if any(x in c for x in ["tiết", "period"])), list(df_clean.columns)[-1])
                        df_clean[tiet_col] = pd.to_numeric(df_clean[tiet_col], errors="coerce").fillna(0)
    
                        c_class = "class" if "class" in df_clean.columns else df_clean.columns[0]
                        c_subject = "subject" if "subject" in df_clean.columns else ("short_name" if "short_name" in df_clean.columns else df_clean.columns[0])
                        c_program = "program" if "program" in df_clean.columns else None
                        c_knowledge = "knowledge" if "knowledge" in df_clean.columns else None
                        c_session = "session" if "session" in df_clean.columns else None
                        c_location = "location" if "location" in df_clean.columns else None
                        c_term = "term"  # 🌟 Gán trực tiếp khóa term đã được chuẩn hóa
                        c_faculty = "faculty" if "faculty" in df_clean.columns else None
                        c_note = "note" if "note" in df_clean.columns else None
    
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
                        df_after = df_clean.groupby("năm học hiển thị").agg(**{
                            "Tổng số tiết thực hiện": (tiet_col, "sum"),
                            "Số lượng lớp": (c_class, "nunique"),
                            "Số lượng môn học": (c_subject, "nunique")
                        }).reset_index().sort_values("năm học hiển thị")
                        
                        df_after = df_after.rename(columns={"năm học hiển thị": "Năm học hiển thị"})
    
                        st.markdown("##### 🧹 1. Bảng tổng hợp Giảng dạy theo Năm học")
                        tot_lop = df_after["Số lượng lớp"].sum()
                        tot_tiet = df_after["Tổng số tiết thực hiện"].sum()
    
                        df_after_disp = df_after.copy()
                        df_after_disp.loc[len(df_after_disp)] = ["**Tổng cộng**", tot_tiet, tot_lop, float('nan')]
                        df_after_disp = df_after_disp[["Năm học hiển thị", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]]
                        st.dataframe(df_after_disp, use_container_width=True)
    
                        # ==========================================
                        # 🔍 2. BẢNG CHI TIẾT GIẢNG DẠY (TÙY CHỈNH TIÊU CHÍ)
                        # ==========================================
                        st.markdown("##### 🔍 2. Bảng chi tiết Giảng dạy (Tùy chỉnh theo tiêu chí)")
    
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
                        with col_opt4:
                            opt_lecturer = st.checkbox("Theo Giảng viên", value=True, key="chk_gd_lect")
                            opt_term = st.checkbox("Theo Học kỳ", value=False, key="chk_gd_term")  # 🌟 Kích hoạt checkbox Học kỳ
    
                        group_detail_keys = []
                        if opt_year:
                            group_detail_keys.append("năm học hiển thị")
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
                        if opt_term and c_term in df_clean.columns:
                            group_detail_keys.append(c_term)  # 🌟 Đưa term vào khóa gom nhóm
                        if opt_faculty and c_faculty and c_faculty in df_clean.columns:
                            group_detail_keys.append(c_faculty)
                        if opt_note and c_note and c_note in df_clean.columns:
                            group_detail_keys.append(c_note)
                        if opt_lecturer:
                            group_detail_keys.append("_full_name")
    
                        if not group_detail_keys:
                            group_detail_keys = ["năm học hiển thị"]
    
                        agg_detail_dict = {
                            tiet_col: "sum",
                            c_class: "nunique"
                        }
    
                        df_gd_detail = df_clean.groupby(group_detail_keys).agg(agg_detail_dict).reset_index()
    
                        rename_detail_dict = {
                            "năm học hiển thị": "Năm học",
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
                            rename_detail_dict[c_term] = "Học kỳ"  # 🌟 Đổi tên hiển thị Học kỳ
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
                        # 📊 3. BIỂU ĐỒ TRỰC QUAN ĐỘNG (HỖ TRỢ BÓC TÁCH THEO TỪNG NĂM HỌC KHI CHỌN ĐỒNG THỜI)
                        # ==========================================
                        first_col_name = df_gd_detail.columns[0]
                        df_plot_data = df_gd_detail[df_gd_detail[first_col_name] != "**Tổng cộng**"].copy()
                        
                        if not df_plot_data.empty:
                            st.markdown("##### 📊 3. Biểu đồ trực quan Giảng dạy (Tự động vẽ theo các tiêu chí đã chọn)")
                            
                            metrics_cols = ["Tổng số tiết", "Số lượng lớp"]
                            active_criteria_cols = [c for c in df_gd_detail.columns if c not in metrics_cols and c != "**Tổng cộng**"]
    
                            has_short_name = "short_name" in [c.lower() for c in df_clean.columns]
                            short_name_col_actual = next((c for c in df_clean.columns if c.lower() == "short_name"), None)
    
                            # Kiểm tra xem người dùng có chọn đồng thời "Năm học" và các tiêu chí phụ khác không
                            has_year_selected = "Năm học" in active_criteria_cols
                            other_criteria_cols = [c for c in active_criteria_cols if c != "Năm học"]
    
                            # 🌟 TRƯỜNG HỢP 1: CHỈ CHỌN MỘT TIÊU CHÍ HOẶC KHÔNG CÓ NĂM HỌC ĐI KÈM
                            for crit_col in active_criteria_cols:
                                st.markdown(f"###### 📌 Phân tích theo tiêu chí: **{crit_col}**")
                                col_c1, col_c2 = st.columns(2)
    
                                if crit_col == "Tên môn học" and has_short_name and short_name_col_actual:
                                    df_plot_mapped = df_plot_data.copy()
                                    mapping_dict = df_clean[[c_subject, short_name_col_actual]].drop_duplicates().set_index(c_subject)[short_name_col_actual].to_dict()
                                    df_plot_mapped["Trục_X_Vẽ"] = df_plot_mapped[crit_col].map(mapping_dict).fillna(df_plot_mapped[crit_col])
                                    plot_base_col = "Trục_X_Vẽ"
                                else:
                                    plot_base_col = crit_col
    
                                df_grouped_crit = df_plot_data.groupby(plot_base_col)[metrics_cols].sum().reset_index()
    
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
    
                                st.markdown("---")
    
                            # 🌟 TRƯỜNG HỢP 2: VẼ BỔ SUNG BIỂU ĐỒ CHI TIẾT THEO TỪNG NĂM HỌC KHI CHỌN ĐỒNG THỜI NHIỀU TIÊU CHÍ
                            if has_year_selected and other_criteria_cols:
                                st.markdown("---")
                                st.markdown("#### 🌟 3.1 Biểu đồ bóc tách chi tiết theo Từng năm học cho các tiêu chí khác")
    
                                for other_col in other_criteria_cols:
                                    st.markdown(f"##### 📌 Phân tích tiêu chí **{other_col}** bóc tách theo **Năm học**")
                                    
                                    # Lấy danh sách các năm học có sẵn trong dữ liệu
                                    list_years = sorted(df_plot_data["Năm học"].astype(str).unique())
    
                                    for yr in list_years:
                                        st.markdown(###### Năm học: **{yr}**")
                                        df_yr_sub = df_plot_data[df_plot_data["Năm học"].astype(str) == yr]
    
                                        if df_yr_sub.empty:
                                            continue
    
                                        col_y1, col_y2 = st.columns(2)
    
                                        if other_col == "Tên môn học" and has_short_name and short_name_col_actual:
                                            df_yr_mapped = df_yr_sub.copy()
                                            mapping_dict = df_clean[[c_subject, short_name_col_actual]].drop_duplicates().set_index(c_subject)[short_name_col_actual].to_dict()
                                            df_yr_mapped["Trục_X_Vẽ"] = df_yr_mapped[other_col].map(mapping_dict).fillna(df_yr_mapped[other_col])
                                            plot_yr_base = "Trục_X_Vẽ"
                                        else:
                                            plot_yr_base = other_col
    
                                        df_yr_grouped = df_yr_sub.groupby(plot_yr_base)[metrics_cols].sum().reset_index()
                                        
                                        num_bars_yr = len(df_yr_grouped)
                                        dyn_w_yr = max(6.0, num_bars_yr * 0.4)
                                        f_size_yr = 6 if num_bars_yr > 15 else (7 if num_bars_yr > 10 else 8)
    
                                        # Biểu đồ tiết theo năm học
                                        with col_y1:
                                            fig_y1, ax_y1 = plt.subplots(figsize=(dyn_w_yr, 3.5))
                                            bars_y1 = ax_y1.bar(df_yr_grouped[plot_yr_base].astype(str), df_yr_grouped["Tổng số tiết"], color="#3274A1")
                                            for bar in bars_y1:
                                                h = bar.get_height()
                                                ax_y1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=f_size_yr, fontweight="bold")
                                            
                                            ax_y1.set_xlabel(other_col, fontsize=9)
                                            ax_y1.set_ylabel("Tổng số tiết", fontsize=9)
                                            ax_y1.set_title(f"Tổng số tiết - {other_col} (Năm học: {yr})", fontsize=10, fontweight="bold")
                                            ax_y1.tick_params(axis="x", rotation=45 if num_bars_yr > 8 else 0)
                                            st.pyplot(fig_y1, bbox_inches="tight")
    
                                        # Biểu đồ lớp theo năm học
                                        with col_y2:
                                            fig_y2, ax_y2 = plt.subplots(figsize=(dyn_w_yr, 3.5))
                                            bars_y2 = ax_y2.bar(df_yr_grouped[plot_yr_base].astype(str), df_yr_grouped["Số lượng lớp"], color="#E1812C")
                                            for bar in bars_y2:
                                                h = bar.get_height()
                                                ax_y2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=f_size_yr, fontweight="bold")
                                            
                                            ax_y2.set_xlabel(other_col, fontsize=9)
                                            ax_y2.set_ylabel("Số lượng lớp", fontsize=9)
                                            ax_y2.set_title(f"Số lượng lớp - {other_col} (Năm học: {yr})", fontsize=10, fontweight="bold")
                                            ax_y2.tick_params(axis="x", rotation=45 if num_bars_yr > 8 else 0)
                                            st.pyplot(fig_y2, bbox_inches="tight")
    
                                        st.markdown("---")

                    else:
                        df_temp_detail = total_rec_df.copy()
                        df_temp_detail.columns = [str(c).strip() for c in df_temp_detail.columns]

                        name_prod_col = next((c for c in df_temp_detail.columns if c.lower() in ["tên sản phẩm"]), None)
                        id_col_check = next((c for c in df_temp_detail.columns if c.lower() in ["mã sản phẩm", "code"]), None)
                        name_col_check = next((c for c in df_temp_detail.columns if c.lower() == "name"), None)
                        surname_col_check = next((c for c in df_temp_detail.columns if c.lower() == "surname"), None)
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

                        phan_loai_col = next((c for c in df_temp_detail.columns if "phân loại cấp 1" in c.lower()), None)
                        loai_hd_col = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["loại hoạt động", "loại"])), None)
                        cap_do_col = next((c for c in df_temp_detail.columns if c.lower() == "cấp độ" or "cấp độ" in c.lower()), None)
                        phan_loai_2 = next((c for c in df_temp_detail.columns if "phân loại cấp 2" in c.lower()), None)
                        phan_loai_3 = next((c for c in df_temp_detail.columns if "phân loại cấp 3" in c.lower()), None)

                        group_keys_final = ["Năm học hiển thị", "Sản phẩm chuẩn hóa"]
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

                        df_clean_unified = df_temp_detail.groupby(group_keys_final, dropna=False).agg(agg_rules_detail).reset_index()
                        
                        st.markdown("##### 📋 1. Bảng thống kê TRƯỚC khi trừ trùng lặp")
                        with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                            df_before = total_rec_df.groupby("Năm học hiển thị").agg(**{
                                "Tổng số dòng kê khai": (tiet_col_target, "count"),
                                "Tổng số tiết": (tiet_col_target, "sum")
                            }).reset_index().sort_values("Năm học hiển thị")
        
                            tot_d_b = df_before["Tổng số dòng kê khai"].sum()
                            tot_t_b = df_before["Tổng số tiết"].sum()
                            df_before_disp = df_before.copy()
                            df_before_disp.loc[len(df_before_disp)] = ["**Tổng cộng**", tot_d_b, tot_t_b]
                            st.dataframe(df_before_disp, use_container_width=True)

                        st.markdown("##### 🧹 2.1 Bảng thống kê SAU KHI trừ trùng lặp")
                        df_after = df_clean_unified.groupby("Năm học hiển thị").agg(**{
                            "Số lượng sản phẩm độc lập": (tiet_col_target, "count"),
                            "Tổng số tiết thực hiện": (tiet_col_target, "sum")
                        }).reset_index().sort_values("Năm học hiển thị")

                        tot_sp_a = df_after["Số lượng sản phẩm độc lập"].sum()
                        tot_t_a = df_after["Tổng số tiết thực hiện"].sum()
                        df_after_disp = df_after.copy()
                        df_after_disp.loc[len(df_after_disp)] = ["**Tổng cộng**", tot_sp_a, tot_t_a]
                        st.dataframe(df_after_disp, use_container_width=True)

                        if phan_loai_col:
                            st.markdown("##### 🏷️ 2.2 Thống kê tổng hợp theo Phân loại cấp 1, Loại hoạt động & Cấp độ")
                            
                            group_keys_summary = [phan_loai_col]
                            if loai_hd_col and loai_hd_col in df_clean_unified.columns:
                                group_keys_summary.append(loai_hd_col)
                            if cap_do_col and cap_do_col in df_clean_unified.columns:
                                group_keys_summary.append(cap_do_col)
                            group_keys_summary.append("Năm học hiển thị")

                            df_phanloai_summary = df_clean_unified.groupby(group_keys_summary).agg(**{
                                "Số lượng sản phẩm": (tiet_col_target, "count"),
                                "Tổng số tiết": (tiet_col_target, "sum")
                            }).reset_index().sort_values(group_keys_summary)

                            tot_sl_pl = df_phanloai_summary["Số lượng sản phẩm"].sum()
                            tot_tiet_pl = df_phanloai_summary["Tổng số tiết"].sum()

                            df_phanloai_summary_disp = df_phanloai_summary.copy()
                            total_row = ["**Tổng cộng**"] + [""] * (len(df_phanloai_summary_disp.columns) - 3) + [tot_sl_pl, tot_tiet_pl]
                            df_phanloai_summary_disp.loc[len(df_phanloai_summary_disp)] = total_row
                            with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                                st.dataframe(df_phanloai_summary_disp, use_container_width=True)
                       
                        st.markdown("##### 🔍 2.3 Bảng chi tiết kèm Tên sản phẩm & Danh sách thành viên (Tùy chỉnh tiêu chí)")

                        cols_lower_all = {str(c).strip().lower(): c for c in df_clean_unified.columns}
                        col_ma_sp = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["mã sản phẩm", "ma san pham", "code"])), None)
                        col_tap_chi = next((cols_lower_all[c] for c in cols_lower_all if any(x in c for x in ["tạp chí", "tap chi", "hội thảo", "hoi thao", "sách", "sach"])), None)
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
                            group_detail_dynamic.append("Năm học hiển thị")
                        if opt_loai and loai_hd_col and loai_hd_col in df_clean_unified.columns:
                            group_detail_dynamic.append(loai_hd_col)
                        if opt_cap and cap_do_col and cap_do_col in df_clean_unified.columns:
                            group_detail_dynamic.append(cap_do_col)
                        if opt_pl1 and phan_loai_col and phan_loai_col in df_clean_unified.columns:
                            group_detail_dynamic.append(phan_loai_col)
                        if opt_pl2 and phan_loai_2 and phan_loai_2 in df_clean_unified.columns:
                            group_detail_dynamic.append(phan_loai_2)
                        if opt_pl3 and phan_loai_3 and phan_loai_3 in df_clean_unified.columns:
                            group_detail_dynamic.append(phan_loai_3)
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
                            group_detail_dynamic = ["Năm học hiển thị"]

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

                        df_nckh_detail = df_clean_unified.groupby(group_detail_dynamic, dropna=False).agg(agg_dyn_dict).reset_index()

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
                        # 📊 3. BIỂU ĐỒ TRỰC QUAN ĐỘNG CHO NCKH (CHỈ VẼ 5 TIÊU CHỈ & GÁN KÝ HỘI TRỤC X)
                        # ==========================================
                        first_col_nckh = df_nckh_detail.columns[0]
                        df_plot_nckh = df_nckh_detail[df_nckh_detail[first_col_nckh] != "**Tổng cộng**"].copy()
    
                        if not df_plot_nckh.empty:
                            st.markdown("##### 📊 3. Biểu đồ trực quan theo các tiêu chí đã chọn")
    
                            metrics_nckh = ["Số lượng", "Tổng số tiết"]
                            
                            # Danh sách ánh xạ chính xác từ checkbox và tên cột tương ứng trong bảng chi tiết
                            allowed_mapping = []
                            if opt_y and "Năm học hiển thị" in df_nckh_detail.columns:
                                allowed_mapping.append(("Năm học hiển thị", "Năm học"))
                            if opt_cap and cap_do_col and cap_do_col in df_nckh_detail.columns:
                                allowed_mapping.append((cap_do_col, "Cấp độ"))
                            if opt_loai and loai_hd_col and loai_hd_col in df_nckh_detail.columns:
                                allowed_mapping.append((loai_hd_col, "Loại HĐ"))
                            if opt_role and role_col_check and role_col_check in df_nckh_detail.columns:
                                allowed_mapping.append((role_col_check, "Vai trò"))
                            if opt_pl1 and phan_loai_col and phan_loai_col in df_nckh_detail.columns:
                                allowed_mapping.append((phan_loai_col, "PL Cấp 1"))
    
                            # Duyệt và vẽ cặp biểu đồ cho từng tiêu chí được phép
                            for col_name, display_name in allowed_mapping:
                                if col_name not in df_plot_nckh.columns:
                                    continue
    
                                st.markdown(f"###### 📌 Phân tích theo tiêu chí: **{display_name}**")
                                col_chart1, col_chart2 = st.columns(2)
    
                                # Nhóm dữ liệu theo tiêu chí
                                df_grouped_nckh = df_plot_nckh.groupby(col_name)[metrics_nckh].sum().reset_index()
                                
                                # Xử lý tự động rút gọn tên trên trục hoành nếu tên quá dài
                                unique_labels = df_grouped_nckh[col_name].astype(str).tolist()
                                needs_mapping = any(len(lbl) > 15 for lbl in unique_labels)
    
                                if needs_mapping:
                                    # Tạo từ điển ánh xạ từ Tên dài sang Ký hiệu ngắn (K1, K2, K3...)
                                    label_mapping = {lbl: f"K{i+1}" for i, lbl in enumerate(unique_labels)}
                                    df_grouped_nckh["_Short_Label"] = df_grouped_nckh[col_name].map(label_mapping)
                                    x_plot_col = "_Short_Label"
                                else:
                                    x_plot_col = col_name
    
                                # Biểu đồ 1: Số lượng sản phẩm
                                with col_chart1:
                                    fig1, ax1 = plt.subplots(figsize=(6, 3.5))
                                    bars1 = ax1.bar(df_grouped_nckh[x_plot_col].astype(str), df_grouped_nckh["Số lượng"], color="#55A868")
                                    for bar in bars1:
                                        h = bar.get_height()
                                        ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=6, fontweight="bold")
                                    
                                    ax1.set_xlabel("Ký hiệu" if needs_mapping else display_name, fontsize=7)
                                    ax1.set_ylabel("Số lượng sản phẩm", fontsize=9)
                                    ax1.set_title(f"Số lượng theo {display_name}", fontsize=10, fontweight="bold")
                                    ax1.tick_params(axis="x", rotation=45 if needs_mapping else 45)
                                    st.pyplot(fig1, bbox_inches="tight")
    
                                # Biểu đồ 2: Tổng số tiết thực hiện
                                with col_chart2:
                                    fig2, ax2 = plt.subplots(figsize=(6, 3.5))
                                    bars2 = ax2.bar(df_grouped_nckh[x_plot_col].astype(str), df_grouped_nckh["Tổng số tiết"], color="#C44E52")
                                    for bar in bars2:
                                        h = bar.get_height()
                                        ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=6, fontweight="bold")
                                    
                                    ax2.set_xlabel("Ký hiệu" if needs_mapping else display_name, fontsize=7)
                                    ax2.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
                                    ax2.set_title(f"Tổng số tiết theo {display_name}", fontsize=10, fontweight="bold")
                                    ax2.tick_params(axis="x", rotation=45 if needs_mapping else 45)
                                    st.pyplot(fig2, bbox_inches="tight")
    
                                # Nếu có dùng ký hiệu rút gọn, hiển thị bảng chú thích ngay bên dưới biểu đồ
                                if needs_mapping:
                                    st.markdown(f"**📝 Chú thích ký hiệu trục hoành cho ({display_name}):**")
                                    with st.expander("📅 **(Bấm để mở/đóng)**", expanded=True):
                                        note_df = pd.DataFrame(list(label_mapping.items()), columns=["Ký hiệu", "Tên đầy đủ"])
                                        st.dataframe(note_df, use_container_width=True, hide_index=True)
                              
        else:
            st.info("ℹ️ Không tìm thấy cột 'SỐ TIẾT KÊ KHAI' hoặc cột thời gian phù hợp để vẽ biểu đồ.")
    else:
        st.info("ℹ️ Nhập từ khóa để hiển thị kết quả phân tích.")

# ----------------------------------------------------------
# TAB 2: DỮ LIỆU CÁC NHÓM CÔNG VIỆC GD, NCKH, OTHER
# ----------------------------------------------------------
with tab2:
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
        st.dataframe(detail_dfs[chosen_key_view], height=450, use_container_width=True)
      else:
        st.warning(f"⚠️ Nhóm {selected_group_view} hiện chưa có dữ liệu.")
    else:
      st.error("❌ Không thể tải dữ liệu chi tiết từ Google Sheets.")

# ----------------------------------------------------------
# TAB 3: DỮ LIỆU MÔ TẢ (df1 & df2)
# ----------------------------------------------------------
with tab3:
    st.markdown("#### 📂 Dữ liệu mô tả (df1 & df2)")
    col1, col2 = st.columns(2)
    
    with col1:
      if "df1" not in st.session_state or st.session_state["df1"] is None:
        st.session_state["df1"] = read_gsheet(links["df1"])
      if st.session_state["df1"] is not None:
        st.success("✅ Đã tải df1 (Year - Term - Code)!")
        st.dataframe(st.session_state["df1"], height=400, use_container_width=True)
    
    with col2:
      if "df2" not in st.session_state or st.session_state["df2"] is None:
        st.session_state["df2"] = read_gsheet(links["df2"])
      if st.session_state["df2"] is not None:
        st.success("✅ Đã tải df2 (Category - Description)!")
        st.dataframe(st.session_state["df2"], height=400, use_container_width=True)
