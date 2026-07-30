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

# ==========================================================
# ⚙️ CẤU HÌNH APPS
# ==========================================================
st.set_page_config(page_title="📋 Ứng dụng QLCV", layout="wide")
st.title("📋 Ứng dụng Quản lý Công việc")
st.write(
    "Tổng hợp dữ liệu công việc từ nhiều bảng (df1_year-term-code;"
    " df2_category-description; GD_giảng dạy; NCKH_nghiên cứu; Other_khác)"
)

import time  # Nhớ đảm bảo đã import time ở đầu file (nếu chưa có)

# ==========================================================
# 🔄 NÚT CẬP NHẬT / LÀM MỚI DỮ LIỆU (REFRESH CACHE)
# ==========================================================
col_refresh1, col_refresh2 = st.columns([4, 1])
with col_refresh2:
  if st.button("🔄 Cập nhật dữ liệu", use_container_width=True):
    # Xóa toàn bộ cache đã lưu bằng @st.cache_data
    st.cache_data.clear()

    # Xóa sạch các biến dữ liệu trong session_state để app bắt buộc load mới
    keys_to_reset = ["df1", "df2", "detail_dfs", "selected_years_stat"]
    for k in keys_to_reset:
      if k in st.session_state:
        del st.session_state[k]

    # Tạo một container trống để hiển thị thông báo tạm thời
    status_placeholder = st.empty()
    status_placeholder.success("✅ Updated!")

    # Dừng 2 giây để người dùng kịp nhìn thấy thông báo
    time.sleep(2)

    # Xóa thông báo đi rồi mới tải lại trang
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
    # Tháng >= 8 thuộc học kỳ 1 năm học YYYY - (YYYY+1)
    if month >= 8:
      return f"{year}-{year + 1}"
    # Tháng < 8 thuộc học kỳ 2 năm học (YYYY-1) - YYYY
    else:
      return f"{year - 1}-{year}"

  # Trường hợp chỉ nhập năm YYYY
  match_year = re.search(r"\b(\d{4})\b", dot_str)
  if match_year:
    y = int(match_year.group(1))
    return f"{y}-{y + 1}"

  return "Khác / Chưa xác định"


# ==========================================================
# 🧩 HÀM ĐỌC GOOGLE SHEET (CÓ CACHE ĐỂ ỔN ĐỊNH DỮ LIỆU)
# ==========================================================
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
    # Làm sạch tên cột (loại bỏ khoảng trắng thừa)
    df.columns = [str(c).strip() for c in df.columns]

    # Ép toàn bộ các cột kiểu object/text về dạng chuỗi (string) để tránh lỗi .str.contains()
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
st.markdown("#### 📂 Dữ liệu mô tả (df1 & df2)")

col1, col2 = st.columns(2)

with col1:
  if "df1" not in st.session_state or st.session_state["df1"] is None:
    st.session_state["df1"] = read_gsheet(links["df1"])
  if st.session_state["df1"] is not None:
    st.success("✅ Đã tải df1 (Year - Term - Code)!")
    st.dataframe(st.session_state["df1"], height=180, use_container_width=True)

with col2:
  if "df2" not in st.session_state or st.session_state["df2"] is None:
    st.session_state["df2"] = read_gsheet(links["df2"])
  if st.session_state["df2"] is not None:
    st.success("✅ Đã tải df2 (Category - Description)!")
    st.dataframe(st.session_state["df2"], height=180, use_container_width=True)

# Tải dữ liệu chi tiết vào session_state nếu chưa có
if "detail_dfs" not in st.session_state or not st.session_state["detail_dfs"]:
  detail_dfs = {}
  for key in ["GD", "NCKH", "Other"]:
    df = read_gsheet(links[key])
    if df is not None:
      detail_dfs[key] = df
  st.session_state["detail_dfs"] = detail_dfs

# ==========================================================
# 📚 TẢI DỮ LIỆU CHI TIẾT VÀ ĐỒNG BỘ SESSION STATE
# ==========================================================
st.markdown("#### 📘 Các nhóm công việc chi tiết")

# Khởi tạo detail_dfs trong session_state nếu chưa có
if "detail_dfs" not in st.session_state or not st.session_state["detail_dfs"]:
  detail_dfs = {}
  for key in ["GD", "NCKH", "Other"]:
    df = read_gsheet(links[key])
    if df is not None:
      detail_dfs[key] = df
  st.session_state["detail_dfs"] = detail_dfs

# Luôn lấy detail_dfs từ session_state để tránh lỗi NameError
detail_dfs = st.session_state["detail_dfs"]

with st.expander(
    "🔍 Click để xem danh sách các nhóm công việc chi tiết", expanded=False
):
  if detail_dfs:
    selected_group_view = st.radio(
        "Chọn nhóm công việc muốn xem:",
        options=["GD (Giảng dạy)", "NCKH (Nghiên cứu)", "Other (Khác)"],
        horizontal=True,
    )
    key_mapping_view = {
        "GD (Giảng dạy)": "GD",
        "NCKH (Nghiên cứu)": "NCKH",
        "Other (Khác)": "Other",
    }
    chosen_key_view = key_mapping_view[selected_group_view]
    if chosen_key_view in detail_dfs:
      st.success(f"✅ Đang hiển thị dữ liệu nhóm: {selected_group_view}")
      st.dataframe(detail_dfs[chosen_key_view], height=250, use_container_width=True)
    else:
      st.warning(f"⚠️ Nhóm {selected_group_view} hiện chưa có dữ liệu.")
  else:
    st.error("❌ Không thể tải dữ liệu chi tiết từ Google Sheets.")

# ==========================================================
# 🔍 TAB RADIO LỌC PHẠM VI TÌM KIẾM NÂNG CAO (TỐI ƯU ĐA BẢNG GD, NCKH, OTHER)
# ==========================================================
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
        "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)\nVí"
        " dụ: Quản lý danh mục đầu tư hoặc Toán cao cấp"
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

    # --- MỞ RỘNG TỪ KHÓA THÔNG MINH (SYNONYMS) ---
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

    # Xác định tập hợp các bảng cần tìm dựa vào lựa chọn trên radio tab
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
    else:  # Tất cả
      target_search_dict = detail_dfs

    for name, df in target_search_dict.items():
      if df is None or df.empty:
        continue

      df_temp = df.copy()
      df_temp.columns = [str(c).strip() for c in df_temp.columns]

      # 🌟 ÉP KIỂM TOÀN BỘ CỘT VỀ CHUỖI AN TOÀN TRÊN CLOUD
      for col in df_temp.columns:
        df_temp[col] = df_temp[col].fillna("").astype(str)

      # Lấy toàn bộ các cột có trong bảng để quét tìm kiếm (Không phân biệt tên cột tiếng Anh hay tiếng Việt)
      all_text_cols = list(df_temp.columns)

      if all_text_cols:
        mask = pd.Series(True, index=df_temp.index)
        for syn_list in expanded_keywords:
          mask_syn = pd.Series(False, index=df_temp.index)
          for kw in syn_list:
            # Quét trên tất cả các cột của bảng (class, subject, short_name, program, category,...)
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
        
        # 🌟 Gắn nhãn tên bảng vào DataFrame trước khi đưa vào found_records
        match_df["_source_table"] = name 
        
        found_records.append((name, match_df))

    # --- HIỂN THỊ KẾT QUẢ TÌM KIẾM ---
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
# 📊 THỐNG KÊ, TRỪ TRÙNG LẶP VÀ VẼ ĐỒ THỊ (PHÂN TÁCH RIÊNG GD VÀ NCKH/OTHER)
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

        # --- 🎛️ BỘ LỌC CHỌN NĂM HỌC HIỂN THỊ (DẠNG Ô VUÔNG) ---
        all_years = sorted(
            total_rec_df["Năm học hiển thị"].dropna().unique().tolist()
        )

        st.markdown("📅 **Chọn năm học muốn xem thống kê và biểu đồ:**")

        if "selected_years_stat" not in st.session_state:
            st.session_state["selected_years_stat"] = all_years

        cols_chk = st.columns(len(all_years) if len(all_years) > 0 else 1)
        selected_years = []

        for i, year in enumerate(all_years):
            with cols_chk[i % len(cols_chk)]:
                is_checked = st.checkbox(
                    str(year),
                    value=(year in st.session_state["selected_years_stat"]),
                    key=f"chk_year_{year}",
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
                # 🌟 PHÂN TÁCH LUỒNG XỬ LÝ DỰA TRƯỜNG _source_table (GD VS NCKH/OTHER)
                is_only_gd = (
                    "_source_table" in total_rec_df.columns
                    and (total_rec_df["_source_table"] == "GD").all()
                )

                if is_only_gd:
                    # ==========================================
                    # 📚 XỬ LÝ RIÊNG CHO KHỐI GIẢNG DẠY (GD) - BẢNG THỐNG KÊ TÙY CHỈNH & ĐỒ THỊ MỚI
                    # ==========================================
                    st.markdown("##### 📚 Thống kê Giảng dạy Tùy chỉnh & Chi tiết")

                    df_clean = total_rec_df.drop_duplicates().copy()
                    df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]

                    # Đảm bảo cột "năm học hiển thị" luôn tồn tại
                    time_col_actual = next((c for c in df_clean.columns if any(x in c for x in ["năm học", "year", "đợt", "term"])), None)
                    if "năm học hiển thị" not in df_clean.columns and time_col_actual:
                        df_clean["năm học hiển thị"] = df_clean[time_col_actual].apply(quy_doi_nam_hoc)
                    elif "năm học hiển thị" not in df_clean.columns:
                        df_clean["năm học hiển thị"] = "Chưa xác định"

                    tiet_col = next((c for c in df_clean.columns if any(x in c for x in ["tiết", "period"])), list(df_clean.columns)[-1])
                    df_clean[tiet_col] = pd.to_numeric(df_clean[tiet_col], errors="coerce").fillna(0)

                    # Xác định tên các cột thực tế
                    c_class = "class" if "class" in df_clean.columns else df_clean.columns[0]
                    c_subject = "subject" if "subject" in df_clean.columns else ("short_name" if "short_name" in df_clean.columns else df_clean.columns[0])
                    c_program = "program" if "program" in df_clean.columns else None
                    name_col = "name" if "name" in df_clean.columns else None
                    surname_col = "surname" if "surname" in df_clean.columns else None

                    # Gộp họ tên giảng viên để dễ theo dõi
                    if name_col:
                        if surname_col:
                            df_clean["_full_name"] = df_clean[surname_col].astype(str) + " " + df_clean[name_col].astype(str)
                        else:
                            df_clean["_full_name"] = df_clean[name_col].astype(str)
                    else:
                        df_clean["_full_name"] = "Không rõ"

                    # 1. Bảng thống kê tổng quan trước khi xử lý
                    df_before = df_clean.groupby("năm học hiển thị").agg(**{
                        "Tổng số dòng kê khai": (tiet_col, "count"),
                        "Tổng số tiết": (tiet_col, "sum")
                    }).reset_index().sort_values("năm học hiển thị")

                    tot_d_b = df_before["Tổng số dòng kê khai"].sum()
                    tot_t_b = df_before["Tổng số tiết"].sum()
                    df_before_disp = df_before.copy()
                    df_before_disp.loc[len(df_before_disp)] = ["**Tổng cộng**", tot_d_b, tot_t_b]
                    st.dataframe(df_before_disp, use_container_width=True)

                    # 2. Bảng tổng hợp theo năm học
                    df_after = df_clean.groupby("năm học hiển thị").agg(**{
                        "Tổng số tiết thực hiện": (tiet_col, "sum"),
                        "Số lượng lớp": (c_class, "nunique"),
                        "Số lượng môn học": (c_subject, "nunique")
                    }).reset_index().sort_values("năm học hiển thị")
                    df_after = df_after.rename(columns={"năm học hiển thị": "Năm học hiển thị"})

                    st.markdown("##### 🧹 2. Bảng tổng hợp Giảng dạy theo Năm học")
                    tot_lop = df_after["Số lượng lớp"].sum()
                    tot_mon = df_after["Số lượng môn học"].sum()
                    tot_tiet = df_after["Tổng số tiết thực hiện"].sum()

                    df_after_disp = df_after.copy()
                    df_after_disp.loc[len(df_after_disp)] = ["**Tổng cộng**", tot_tiet, tot_lop, tot_mon]
                    df_after_disp = df_after_disp[["Năm học hiển thị", "Số lượng lớp", "Số lượng môn học", "Tổng số tiết thực hiện"]]
                    st.dataframe(df_after_disp, use_container_width=True)

                    # ==========================================
                    # 🌟 2.3 BẢNG CHI TIẾT GIẢNG DẠY CÓ TÙY CHỈNH TIÊU CHÍ (DYNAMIC GROUPBY)
                    # ==========================================
                    st.markdown("##### 🔍 2.3 Bảng chi tiết Giảng dạy (Tùy chỉnh theo tiêu chí)")

                    # Tạo các checkbox tùy chọn tiêu chí thống kê cho người dùng
                    st.markdown("⚙️ **Chọn các tiêu chí muốn gom nhóm chi tiết:**")
                    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
                    with col_opt1:
                        opt_year = st.checkbox("Theo Năm học", value=True)
                    with col_opt2:
                        opt_prog = st.checkbox("Theo Chương trình (Program)", value=True)
                    with col_opt3:
                        opt_subj = st.checkbox("Theo Môn học (Subject)", value=True)
                    with col_opt4:
                        opt_lecturer = st.checkbox("Theo Giảng viên", value=True)

                    # Xây dựng danh sách khóa gom nhóm động dựa trên lựa chọn của người dùng
                    group_detail_keys = []
                    if opt_year:
                        group_detail_keys.append("năm học hiển thị")
                    if opt_prog and c_program and c_program in df_clean.columns:
                        group_detail_keys.append(c_program)
                    if opt_subj:
                        group_detail_keys.append(c_subject)
                    if opt_lecturer:
                        group_detail_keys.append("_full_name")

                    # Nếu người dùng bỏ chọn hết, mặc định gom theo năm học
                    if not group_detail_keys:
                        group_detail_keys = ["năm học hiển thị"]

                    agg_detail_dict = {
                        tiet_col: "sum",
                        c_class: "nunique"  # Đếm số lượng lớp độc lập
                    }

                    df_gd_detail = df_clean.groupby(group_detail_keys).agg(agg_detail_dict).reset_index()

                    # Đổi tên cột hiển thị tiếng Việt thân thiện
                    rename_detail_dict = {
                        "năm học hiển thị": "Năm học",
                        c_subject: "Tên môn học",
                        tiet_col: "Tổng số tiết",
                        c_class: "Số lượng lớp",
                        "_full_name": "Giảng viên"
                    }
                    if c_program:
                        rename_detail_dict[c_program] = "Chương trình"

                    df_gd_detail = df_gd_detail.rename(columns=rename_detail_dict)

                    # 🌟 THÊM DÒNG TỔNG CỘNG VÀO CUỐI BẢNG 2.3
                    if not df_gd_detail.empty:
                        total_tiet_val = df_gd_detail["Tổng số tiết"].sum()
                        total_lop_val = df_gd_detail["Số lượng lớp"].sum()
                        
                        # Tạo một dòng tổng cộng với các giá trị định dạng
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
                    # 📊 3. VẼ ĐỒ THỊ RIÊNG CHO GD
                    # ==========================================
                    df_plot_data = df_after[df_after["Năm học hiển thị"] != "**Tổng cộng**"]
                    if not df_plot_data.empty:
                        st.markdown("##### 📊 3. Biểu đồ trực quan Giảng dạy")
                        col_c1, col_c2 = st.columns(2)

                        # Đồ thị 1: Tổng số lượng lớp theo năm học
                        with col_c1:
                            fig1, ax1 = plt.subplots(figsize=(6, 3.5))
                            b1 = ax1.bar(df_plot_data["Năm học hiển thị"], df_plot_data["Số lượng lớp"], color="#4C72B0")
                            for bar in b1:
                                h = bar.get_height()
                                ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=8, fontweight="bold")
                            ax1.set_xlabel("Năm học", fontsize=9)
                            ax1.set_ylabel("Tổng số lượng lớp", fontsize=9)
                            ax1.set_title("Tổng số lớp theo năm học", fontsize=10, fontweight="bold")
                            ax1.tick_params(axis="x", rotation=45)
                            st.pyplot(fig1, bbox_inches="tight")

                        # Đồ thị 2: Tổng số lượng lớp theo từng tên môn học ngắn gọn (short_name)
                        with col_c2:
                            fig2, ax2 = plt.subplots(figsize=(6, 3.5))
                            
                            # Ưu tiên lấy cột short_name nếu có trong DataFrame, nếu không thì dùng subject
                            c_display_subject = "short_name" if "short_name" in df_clean.columns else c_subject
                            
                            # Tính tổng số lớp gộp cho từng môn theo short_name
                            df_subj_total = df_clean.groupby(c_display_subject)[c_class].nunique().reset_index()
                            df_subj_total = df_subj_total.sort_values(by=c_class, ascending=False)

                            b2 = ax2.bar(df_subj_total[c_display_subject].astype(str), df_subj_total[c_class], color="#DD8452")
                            for bar in b2:
                                h = bar.get_height()
                                ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=8, fontweight="bold")
                            ax2.set_xlabel("Môn học (Short name)", fontsize=9)
                            ax2.set_ylabel("Tổng số lớp", fontsize=9)
                            ax2.set_title("Tổng số lớp theo Tên viết tắt môn học", fontsize=10, fontweight="bold")
                            ax2.tick_params(axis="x", rotation=45)
                            st.pyplot(fig2, bbox_inches="tight")

                else:
                    # ==========================================
                    # 🔬 XỬ LÝ GIỮ NGUYÊN CHO NCKH / OTHER / TẤT CẢ
                    # ==========================================
                    df_temp_detail = total_rec_df.copy()
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

                    phan_loai_col = next((c for c in df_temp_detail.columns if "phân loại cấp 1" in c.lower() or c.lower() == "phân loại cấp 1"), None)
                    loai_hd_col_check = next((c for c in df_temp_detail.columns if any(x in c.lower() for x in ["loại hoạt động", "loại"])), None)

                    group_keys_final = ["Năm học hiển thị", "Sản phẩm chuẩn hóa"]
                    if phan_loai_col and phan_loai_col in df_temp_detail.columns:
                        group_keys_final.insert(0, phan_loai_col)
                    if loai_hd_col_check and loai_hd_col_check in df_temp_detail.columns and loai_hd_col_check not in group_keys_final:
                        group_keys_final.insert(1, loai_hd_col_check)

                    agg_rules_detail = {
                        tiet_col_target: "first",
                        "_full_name": lambda x: ", ".join(x.dropna().unique()),
                    }
                    if name_prod_col and name_prod_col in df_temp_detail.columns:
                        agg_rules_detail[name_prod_col] = lambda x: " / ".join(x.dropna().unique())
                    if id_col_check and id_col_check in df_temp_detail.columns:
                        agg_rules_detail[id_col_check] = lambda x: " / ".join(x.dropna().unique())
                    if role_col_check:
                        agg_rules_detail[role_col_check] = lambda x: " & ".join(x.dropna().unique())

                    df_clean_unified = df_temp_detail.groupby(group_keys_final, dropna=False).agg(agg_rules_detail).reset_index()

                    # 1. Thống kê trước khi trừ trùng
                    st.markdown("##### 📋 1. Bảng thống kê TRƯỚC khi trừ trùng lặp")
                    df_before = total_rec_df.groupby("Năm học hiển thị").agg(**{
                        "Tổng số dòng kê khai": (tiet_col_target, "count"),
                        "Tổng số tiết": (tiet_col_target, "sum")
                    }).reset_index().sort_values("Năm học hiển thị")

                    tot_d_b = df_before["Tổng số dòng kê khai"].sum()
                    tot_t_b = df_before["Tổng số tiết"].sum()
                    df_before_disp = df_before.copy()
                    df_before_disp.loc[len(df_before_disp)] = ["**Tổng cộng**", tot_d_b, tot_t_b]
                    st.dataframe(df_before_disp, use_container_width=True)

                    # 2. Thống kê sau khi trừ trùng
                    st.markdown("##### 🧹 2. Bảng thống kê SAU KHI trừ trùng lặp")
                    df_after = df_clean_unified.groupby("Năm học hiển thị").agg(**{
                        "Số lượng sản phẩm độc lập": (tiet_col_target, "count"),
                        "Tổng số tiết thực hiện": (tiet_col_target, "sum")
                    }).reset_index().sort_values("Năm học hiển thị")

                    tot_sp_a = df_after["Số lượng sản phẩm độc lập"].sum()
                    tot_t_a = df_after["Tổng số tiết thực hiện"].sum()
                    df_after_disp = df_after.copy()
                    df_after_disp.loc[len(df_after_disp)] = ["**Tổng cộng**", tot_sp_a, tot_t_a]
                    st.dataframe(df_after_disp, use_container_width=True)

                    # 2.2 Thống kê phân loại cấp 1
                    if phan_loai_col and phan_loai_col in df_clean_unified.columns:
                        st.markdown("##### 🏷️ 2.2 Thống kê tổng hợp theo Phân loại cấp 1 & Loại hoạt động")
                        group_keys_summary = [phan_loai_col]
                        if loai_hd_col_check and loai_hd_col_check in df_clean_unified.columns:
                            group_keys_summary.append(loai_hd_col_check)
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
                        st.dataframe(df_phanloai_summary_disp, use_container_width=True)

                    # 2.3 Bảng chi tiết NCKH
                    st.markdown("##### 🔍 2.3 Bảng chi tiết kèm Tên sản phẩm & Danh sách thành viên (Đã gom nhóm)")
                    df_phanloai_detail = df_clean_unified.copy()
                    rename_dict = {
                        tiet_col_target: "Tổng số tiết",
                        "_full_name": "Danh sách thành viên"
                    }
                    if role_col_check and role_col_check in df_phanloai_detail.columns:
                        rename_dict[role_col_check] = "Các vai trò"

                    df_phanloai_detail = df_phanloai_detail.rename(columns=rename_dict)
                    for col_drop in ["_source_table", "_clean_key", "Sản phẩm chuẩn hóa"]:
                        if col_drop in df_phanloai_detail.columns:
                            df_phanloai_detail = df_phanloai_detail.drop(columns=[col_drop])

                    st.dataframe(df_phanloai_detail, use_container_width=True)

                    # 3. Vẽ đồ thị NCKH
                    df_plot_data = df_after[df_after["Năm học hiển thị"] != "**Tổng cộng**"]
                    if not df_plot_data.empty:
                        st.markdown("##### 📊 3. Biểu đồ trực quan theo năm học (Số lượng sản phẩm & Số tiết)")
                        col_chart1, col_chart2 = st.columns(2)
                        with col_chart1:
                            fig1, ax1 = plt.subplots(figsize=(6, 3.5))
                            bars1 = ax1.bar(df_plot_data["Năm học hiển thị"], df_plot_data["Số lượng sản phẩm độc lập"], color="#55A868")
                            for bar in bars1:
                                h = bar.get_height()
                                ax1.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=8, fontweight="bold")
                            ax1.set_xlabel("Năm học", fontsize=9)
                            ax1.set_ylabel("Số lượng sản phẩm", fontsize=9)
                            ax1.tick_params(axis="x", rotation=45)
                            st.pyplot(fig1, bbox_inches="tight")

                        with col_chart2:
                            fig2, ax2 = plt.subplots(figsize=(6, 3.5))
                            bars2 = ax2.bar(df_plot_data["Năm học hiển thị"], df_plot_data["Tổng số tiết thực hiện"], color="#C44E52")
                            for bar in bars2:
                                h = bar.get_height()
                                ax2.text(bar.get_x() + bar.get_width()/2, h, f"{int(h):,}", ha="center", va="bottom", fontsize=8, fontweight="bold")
                            ax2.set_xlabel("Năm học", fontsize=9)
                            ax2.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
                            ax2.tick_params(axis="x", rotation=45)
                            st.pyplot(fig2, bbox_inches="tight")
    else:
        st.info("ℹ️ Không tìm thấy cột 'SỐ TIẾT KÊ KHAI' hoặc cột thời gian phù hợp để vẽ biểu đồ.")
else:
    st.info("ℹ️ Nhập từ khóa để hiển thị kết quả phân tích.")
