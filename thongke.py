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
@st.cache_data(ttl=600)  # Lưu cache 10 phút để tránh gọi liên tục gây lỗi mạng
def read_gsheet(link):
  try:
    df = pd.read_csv(link)
    df.columns = [c.strip() for c in df.columns]
    return df
  except Exception as e:
    st.error(f"❌ Lỗi đọc Google Sheet: {e}")
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
# 🔍 TAB RADIO LỌC PHẠM VI TÌM KIẾM NÂNG CAO
# ==========================================================
st.header("🔍 Tra cứu công việc nâng cao")

# Thanh radio lựa chọn phạm vi tìm kiếm theo yêu cầu cấu trúc mới
search_scope = st.radio(
    "📂 Chọn phạm vi / hạng mục cần tìm kiếm:",
    options=["🌐 Tất cả các bảng", "📚 GD (Giảng dạy)", "🔬 NCKH (Nghiên cứu)", "📌 Other (Khác)"],
    horizontal=True,
)

keyword_input = (
    st.text_input(
        "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)\nVí"
        " dụ: SCK & chủ biên hoặc TLTK, cấp cơ sở"
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

    # --- MỞ RỘNG TỪ KHÓA THÔNG MINH & TỪ VIẾT TẮT (SYNONYMS) ---
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
      df.columns = [c.strip() for c in df.columns]
      df_temp = df.copy()

      priority_target_cols = [
          c
          for c in df_temp.columns
          if any(
              x in c.lower()
              for x in [
                  "loại hoạt động",
                  "cấp độ",
                  "phân loại cấp 1",
                  "phân loại cấp 2",
                  "phân loại cấp 3",
                  "vai trò",
              ]
          )
      ]

      all_text_cols = [
          c for c in df_temp.columns if df_temp[c].dtype == "object" or c == "id"
      ]

      if all_text_cols:
        mask = pd.Series(True, index=df_temp.index)
        for syn_list in expanded_keywords:
          mask_syn = pd.Series(False, index=df_temp.index)
          for kw in syn_list:
            cols_to_check = (
                priority_target_cols
                if priority_target_cols
                else all_text_cols
            )

            mask_kw = (
                df_temp[cols_to_check]
                .apply(
                    lambda col: col.astype(str)
                    .str.lower()
                    .str.contains(kw, na=False)
                )
                .any(axis=1)
            )

            if not mask_kw.any() and priority_target_cols:
              mask_kw = (
                  df_temp[all_text_cols]
                  .apply(
                      lambda col: col.astype(str)
                      .str.lower()
                      .str.contains(kw, na=False)
                  )
                  .any(axis=1)
              )

            mask_syn |= mask_kw
          mask &= mask_syn
      else:
        mask = pd.Series(False, index=df_temp.index)

      match_df = df_temp[mask]

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
        found_records.append((name, match_df))

    # --- HIỂN THỊ KẾT QUẢ TÌM KIẾM ---
    if found_records:
      st.success(
          f"✅ Tìm thấy kết quả phù hợp từ {len(found_records)} nhóm bảng"
      )

      for name, rec_df in found_records:
        st.markdown(
            f"#### 📘 Nhóm kết quả tìm thấy từ bảng dữ liệu gốc: **{name}** — {len(rec_df)}"
            " dòng"
        )
        st.dataframe(rec_df, use_container_width=True)
    else:
      st.warning("❌ Không tìm thấy dữ liệu phù hợp trong phạm vi đã chọn.")
else:
  st.info("👆 Chọn phạm vi và nhập từ khóa để bắt đầu tìm kiếm và thống kê.")


# ==========================================================
# 📊 THỐNG KÊ, TRỪ TRÙNG LẶP VÀ VẼ ĐỒ THỊ
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
  st.markdown("#### 📈 THỐNG KÊ VÀ XỬ LÝ TRÙNG LẶP SẢN PHẨM HOẶC SỐ LỚP")

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

    # --- 🎛️ BỘ LỌC CHỌN NĂM HỌC HIỂN THỊ (DẠNG Ô VUÔNG / CHECKBOX NHIỀU LỰA CHỌN) ---
    all_years = sorted(
        total_rec_df["Năm học hiển thị"].dropna().unique().tolist()
    )

    st.markdown("📅 **Chọn năm học muốn xem thống kê và biểu đồ:**")

    # Khởi tạo session state lưu trạng thái checkbox nếu chưa có
    if "selected_years_stat" not in st.session_state:
      st.session_state["selected_years_stat"] = (
          all_years  # Mặc định chọn tất cả
      )

    # Hiển thị các ô vuông checkbox nằm ngang
    cols_chk = st.columns(len(all_years) if len(all_years) > 0 else 1)
    selected_years = []

    for i, year in enumerate(all_years):
      with cols_chk[i % len(cols_chk)]:
        # Kiểm tra xem năm này có đang được chọn sẵn không
        is_checked = st.checkbox(
            str(year),
            value=(year in st.session_state["selected_years_stat"]),
            key=f"chk_year_{year}",
        )
        if is_checked:
          selected_years.append(year)

    # Cập nhật lại session state
    st.session_state["selected_years_stat"] = selected_years

    if not selected_years:
      st.warning("⚠️ Vui lòng tích chọn ít nhất một năm học để hiển thị dữ liệu.")
    else:
      # Lọc dataframe theo các năm học được chọn
      total_rec_df = total_rec_df[
          total_rec_df["Năm học hiển thị"].isin(selected_years)
      ]

      if total_rec_df.empty:
        st.warning("❌ Không có dữ liệu cho năm học đã chọn.")
      else:
        # --- 1. THỐNG KÊ TRƯỚC KHI TRỪ TRÙNG LẶP ---
        st.markdown("##### 📋 1. Bảng thống kê TRƯỚC khi trừ trùng lặp")
        df_before = (
            total_rec_df.groupby("Năm học hiển thị")
            .agg(
                **{
                    "Tổng số dòng kê khai": (tiet_col_target, "count"),
                    "Tổng số tiết": (tiet_col_target, "sum"),
                }
            )
            .reset_index()
            .sort_values("Năm học hiển thị")
        )

        tot_d_b = df_before["Tổng số dòng kê khai"].sum()
        tot_t_b = df_before["Tổng số tiết"].sum()
        df_before_disp = df_before.copy()
        df_before_disp.loc[len(df_before_disp)] = ["**Tổng cộng**", tot_d_b, tot_t_b]
        st.dataframe(df_before_disp, use_container_width=True)

        # --- 2. XỬ LÝ TRÙNG LẶP THÔNG MINH BẰNG SKLEARN (COSINE SIMILARITY) ---
        df_clean = total_rec_df.copy()
        name_prod_col = next(
            (c for c in df_clean.columns if c.lower() in ["tên sản phẩm"]), None
        )

        if name_prod_col and not df_clean.empty:
          df_clean["_normalized_name"] = (
              df_clean[name_prod_col]
              .astype(str)
              .str.lower()
              .str.replace(r"\s+", " ", regex=True)
              .str.strip()
          )
          unique_names = df_clean["_normalized_name"].unique()

          if len(unique_names) > 1:
            vectorizer = TfidfVectorizer().fit(unique_names)
            tfidf_matrix = vectorizer.transform(unique_names)
            similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

            threshold = 0.85
            visited = set()
            to_drop_indices = []

            for i in range(len(unique_names)):
              if i in visited:
                continue
              similar_indices = np.where(similarity_matrix[i] >= threshold)[0]
              for idx in similar_indices:
                if idx != i:
                  visited.add(idx)
                  duplicate_rows = df_clean[
                      df_clean["_normalized_name"] == unique_names[idx]
                  ].index
                  to_drop_indices.extend(list(duplicate_rows[1:]))

            df_clean = df_clean.drop(index=to_drop_indices)

          if "_normalized_name" in df_clean.columns:
            df_clean = df_clean.drop(columns=["_normalized_name"])
        else:
          df_clean = df_clean.drop_duplicates()

        st.markdown(
            "##### 🧹 2. Bảng thống kê SAU KHI trừ trùng lặp"
        )
        df_after = (
            df_clean.groupby("Năm học hiển thị")
            .agg(
                **{
                    "Số lượng sản phẩm/số lớp": (tiet_col_target, "count"),
                    "Tổng số tiết thực hiện": (tiet_col_target, "sum"),
                }
            )
            .reset_index()
            .sort_values("Năm học hiển thị")
        )

        tot_sp_a = df_after["Số lượng sản phẩm/số lớp"].sum()
        tot_t_a = df_after["Tổng số tiết thực hiện"].sum()
        df_after_disp = df_after.copy()
        df_after_disp.loc[len(df_after_disp)] = [
            "**Tổng cộng**",
            tot_sp_a,
            tot_t_a,
        ]
        st.dataframe(df_after_disp, use_container_width=True)

        # --- 2.1 THỐNG KÊ THEO PHÂN LOẠI CẤP 1 ---
        phan_loai_col = next(
            (
                c
                for c in df_clean.columns
                if "phân loại cấp 1" in c.lower() or c.lower() == "phân loại cấp 1"
            ),
            None,
        )
        loai_hd_col_check = next(
            (
                c
                for c in df_clean.columns
                if any(x in c.lower() for x in ["loại hoạt động", "loại"])
            ),
            None,
        )
        name_prod_col_check = next(
            (c for c in total_rec_df.columns if c.lower() in ["tên sản phẩm"]),
            None,
        )
        id_col_check = next(
            (c for c in total_rec_df.columns if c.lower() in ["mã sản phẩm"]),
            None,
        )
        name_col_check = next(
            (c for c in total_rec_df.columns if c.lower() == "name"), None
        )
        surname_col_check = next(
            (c for c in total_rec_df.columns if c.lower() == "surname"), None
        )
        role_col_check = next(
            (
                c
                for c in total_rec_df.columns
                if any(x in c.lower() for x in ["vai trò", "role"])
            ),
            None,
        )

        if phan_loai_col:
          st.markdown(
              "##### 🏷️ 2.2 Thống kê tổng hợp theo Phân loại cấp 1 & Loại hoạt"
              " động (Sau khi trừ trùng lặp)"
          )

          group_keys_summary = [phan_loai_col]
          if loai_hd_col_check and loai_hd_col_check in df_clean.columns:
            group_keys_summary.append(loai_hd_col_check)
          group_keys_summary.append("Năm học hiển thị")

          df_phanloai_summary = (
              df_clean.groupby(group_keys_summary)
              .agg(
                  **{
                      "Số lượng sản phẩm": (tiet_col_target, "count"),
                      "Tổng số tiết": (tiet_col_target, "sum"),
                  }
              )
              .reset_index()
              .sort_values(group_keys_summary)
          )

          tot_sl_pl = df_phanloai_summary["Số lượng sản phẩm"].sum()
          tot_tiet_pl = df_phanloai_summary["Tổng số tiết"].sum()

          df_phanloai_summary_disp = df_phanloai_summary.copy()
          total_row = ["**Tổng cộng**"] + [""] * (
              len(df_phanloai_summary_disp.columns) - 3
          ) + [tot_sl_pl, tot_tiet_pl]
          df_phanloai_summary_disp.loc[len(df_phanloai_summary_disp)] = total_row

          st.dataframe(df_phanloai_summary_disp, use_container_width=True)

          st.markdown(
              "##### 🔍 2.3 Bảng chi tiết Phân loại cấp 1 kèm Tên sản phẩm &"
              " Danh sách thành viên (Đã gom nhóm thông minh bằng Sklearn)"
          )

          df_temp_detail = total_rec_df.copy()
          df_temp_detail[tiet_col_target] = pd.to_numeric(
              df_temp_detail[tiet_col_target], errors="coerce"
          ).fillna(0)

          if name_prod_col_check and not df_temp_detail.empty:
            df_temp_detail["_clean_prod_name"] = (
                df_temp_detail[name_prod_col_check]
                .astype(str)
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
          else:
            df_temp_detail["_clean_prod_name"] = "sản phẩm chung"

          if name_col_check:
            if surname_col_check:
              df_temp_detail["_full_name"] = (
                  df_temp_detail[surname_col_check].astype(str)
                  + " "
                  + df_temp_detail[name_col_check].astype(str)
              )
            else:
              df_temp_detail["_full_name"] = df_temp_detail[
                  name_col_check
              ].astype(str)
          else:
            df_temp_detail["_full_name"] = "Không rõ"

          unique_names_list = df_temp_detail["_clean_prod_name"].unique()
          name_to_canonical = {}

          if len(unique_names_list) > 1:
            vectorizer = TfidfVectorizer().fit(unique_names_list)
            tfidf_matrix = vectorizer.transform(unique_names_list)
            similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

            threshold = 0.80
            visited_set = set()

            for i in range(len(unique_names_list)):
              if i in visited_set:
                continue
              canonical_name = unique_names_list[i]
              similar_idx = np.where(similarity_matrix[i] >= threshold)[0]
              for idx in similar_idx:
                visited_set.add(idx)
                name_to_canonical[unique_names_list[idx]] = canonical_name
          else:
            for name_item in unique_names_list:
              name_to_canonical[name_item] = name_item

          df_temp_detail["Sản phẩm chuẩn hóa"] = df_temp_detail[
              "_clean_prod_name"
          ].map(name_to_canonical)

          group_keys_final = [
              phan_loai_col,
              "Năm học hiển thị",
              "Sản phẩm chuẩn hóa",
          ]
          agg_rules_detail = {
              tiet_col_target: "first",
              "_full_name": lambda x: ", ".join(x.dropna().unique()),
          }

          if (
              name_prod_col_check
              and name_prod_col_check in df_temp_detail.columns
          ):
            agg_rules_detail[name_prod_col_check] = lambda x: (
                " / ".join(x.dropna().unique())
            )
          if id_col_check and id_col_check in df_temp_detail.columns:
            agg_rules_detail[id_col_check] = lambda x: (
                " / ".join(x.dropna().unique())
            )
          if role_col_check:
            agg_rules_detail[role_col_check] = lambda x: (
                " & ".join(x.dropna().unique())
            )

          df_phanloai_detail = (
              df_temp_detail.groupby(group_keys_final)
              .agg(agg_rules_detail)
              .reset_index()
          )

          rename_dict = {
              tiet_col_target: "Tổng số tiết",
              "_full_name": "Danh sách thành viên",
          }
          if role_col_check:
            rename_dict[role_col_check] = "Các vai trò"

          df_phanloai_detail = df_phanloai_detail.rename(columns=rename_dict)
          df_phanloai_detail = df_phanloai_detail.sort_values(
              [phan_loai_col, "Năm học hiển thị"]
          )

          if "_clean_prod_name" in df_phanloai_detail.columns:
            df_phanloai_detail = df_phanloai_detail.drop(
                columns=["_clean_prod_name"]
            )
          if "Sản phẩm chuẩn hóa" in df_phanloai_detail.columns:
            df_phanloai_detail = df_phanloai_detail.drop(
                columns=["Sản phẩm chuẩn hóa"]
            )

          st.dataframe(df_phanloai_detail, use_container_width=True)
        else:
          st.info(
              "ℹ️ Không tìm thấy cột 'Phân loại cấp 1 (NCKH)' để thực hiện thống kê"
              " chi tiết do đang thống kê nhóm GD hoặc Other."
          )

        # --- 3. VẼ ĐỒ THỊ ---
        df_plot_data = df_after[
            df_after["Năm học hiển thị"] != "**Tổng cộng**"
        ]
        if not df_plot_data.empty:
          st.markdown(
              "##### 📊 3. Biểu đồ trực quan theo năm học (Sau khi trừ trùng"
              " lặp)"
          )

          col_chart1, col_chart2 = st.columns(2)

          with col_chart1:
            fig1, ax1 = plt.subplots(figsize=(6, 3.5))
            bars1 = ax1.bar(
                df_plot_data["Năm học hiển thị"],
                df_plot_data["Số lượng sản phẩm/số lớp"],
                color="#55A868",
            )
            for bar in bars1:
              h = bar.get_height()
              ax1.text(
                  bar.get_x() + bar.get_width() / 2,
                  h,
                  f"{int(h):,}",
                  ha="center",
                  va="bottom",
                  fontsize=8,
                  fontweight="bold",
              )
            ax1.set_xlabel("Năm học", fontsize=9)
            ax1.set_ylabel("Số lượng sản phẩm", fontsize=9)
            ax1.tick_params(axis="x", rotation=45)
            st.pyplot(fig1, bbox_inches="tight")

          with col_chart2:
            fig2, ax2 = plt.subplots(figsize=(6, 3.5))
            bars2 = ax2.bar(
                df_plot_data["Năm học hiển thị"],
                df_plot_data["Tổng số tiết thực hiện"],
                color="#C44E52",
            )
            for bar in bars2:
              h = bar.get_height()
              ax2.text(
                  bar.get_x() + bar.get_width() / 2,
                  h,
                  f"{int(h):,}",
                  ha="center",
                  va="bottom",
                  fontsize=8,
                  fontweight="bold",
              )
            ax2.set_xlabel("Năm học", fontsize=9)
            ax2.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
            ax2.tick_params(axis="x", rotation=45)
            st.pyplot(fig2, bbox_inches="tight")
        else:
          st.info("ℹ️ Không đủ dữ liệu biểu đồ cho các năm học đã chọn.")
  else:
    st.info(
        "ℹ️ Không tìm thấy cột 'SỐ TIẾT KÊ KHAI' hoặc cột thời gian phù hợp để"
        " vẽ biểu đồ."
    )
else:
  st.info("ℹ️ Nhập từ khóa để hiển thị kết quả phân tích.")
