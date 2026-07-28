#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  6 20:50:24 2025
📋 Ứng dụng Quản lý Công việc (QLCV)
streamlit run "/Users/trieukimlanh/Library/CloudStorage/GoogleDrive-trieukimlanh@gmail.com/My Drive/Từ OneDrive/Spyder/app_QLCV/gemini-code-1784618513228.py"
@author: trieukimlanh
"""
import io
import re
import matplotlib.pyplot as plt
import pandas as pd
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
# 🧩 HÀM ĐỌC GOOGLE SHEET
# ==========================================================
def read_gsheet(link):
  try:
    base_id = link.split("/d/")[1].split("/")[0]
    gid = link.split("gid=")[-1].split("#")[0] if "gid=" in link else "0"
    url = f"https://docs.google.com/spreadsheets/d/{base_id}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)
    df.columns = [c.strip() for c in df.columns]
    return df
  except Exception as e:
    st.error(f"❌ Lỗi đọc Google Sheet: {e}")
    return None


# ==========================================================
# 🔗 CÁC LINK DỮ LIỆU
# ==========================================================
links = {
    "df1": (
        "https://docs.google.com/spreadsheets/d/1-2LRE_94U5occybvmD5xDjDiA8Yn5tp-PvvSExg4GnU/export?format=csv&gid=2080729380"
    ),
    "df2": (
        "https://docs.google.com/spreadsheets/d/1-2LRE_94U5occybvmD5xDjDiA8Yn5tp-PvvSExg4GnU/export?format=csv&gid=0"
    ),
    "GD": (
        "https://docs.google.com/spreadsheets/d/1-2LRE_94U5occybvmD5xDjDiA8Yn5tp-PvvSExg4GnU/export?format=csv&gid=1431418978"
    ),
    "NCKH": (
        "https://docs.google.com/spreadsheets/d/10Vb_sP5IEMGkSwCQiUxvN4hrL66RXXtrLLl6e2sG8mg/edit?usp=sharing"
    ),
    "Other": (
        "https://docs.google.com/spreadsheets/d/1-2LRE_94U5occybvmD5xDjDiA8Yn5tp-PvvSExg4GnU/export?format=csv&gid=1443108898"
    ),
}

# ==========================================================
# 🧮 TẢI DỮ LIỆU CƠ BẢN
# ==========================================================
st.header("📂 Dữ liệu mô tả (df1 & df2)")

col1, col2 = st.columns(2)

with col1:
  df1 = read_gsheet(links["df1"])
  if df1 is not None:
    st.session_state["df1"] = df1
    st.success("✅ Đã tải df1 (Year - Term - Code)!")
    st.dataframe(df1, height=180, use_container_width=True)

with col2:
  df2 = read_gsheet(links["df2"])
  if df2 is not None:
    st.session_state["df2"] = df2
    st.success("✅ Đã tải df2 (Category - Description)!")
    st.dataframe(df2, height=180, use_container_width=True)

# ==========================================================
# 📚 TẢI DỮ LIỆU CHI TIẾT (Được thu gọn vào Expander + Radio)
# ==========================================================
st.header("📘 Các nhóm công việc chi tiết")

detail_dfs = {}
# Tải ngầm dữ liệu vào dictionary trước
for key in ["GD", "NCKH", "Other"]:
  df = read_gsheet(links[key])
  if df is not None:
    detail_dfs[key] = df

st.session_state["detail_dfs"] = detail_dfs

# Thiết kế giao diện Expander chứa Radio Mode theo yêu cầu của bạn
with st.expander(
    "🔍 Click để xem danh sách các nhóm công việc chi tiết", expanded=False
):
  if detail_dfs:
    # Tạo thanh chọn radio nằm ngang
    selected_group = st.radio(
        "Chọn nhóm công việc muốn xem:",
        options=["GD (Giảng dạy)", "NCKH (Nghiên cứu)", "Other (Khác)"],
        horizontal=True,
    )

    # Ánh xạ từ lựa chọn hiển thị sang key dữ liệu tương ứng
    key_mapping = {
        "GD (Giảng dạy)": "GD",
        "NCKH (Nghiên cứu)": "NCKH",
        "Other (Khác)": "Other",
    }

    chosen_key = key_mapping[selected_group]

    if chosen_key in detail_dfs:
      st.success(f"✅ Đang hiển thị dữ liệu nhóm: {selected_group}")
      st.dataframe(detail_dfs[chosen_key], height=250, use_container_width=True)
  else:
    st.error("❌ Không thể tải dữ liệu chi tiết từ Google Sheets.")

# ==========================================================
# 🔍 TRA CỨU CÔNG VIỆC NÂNG CAO
# ==========================================================
st.header("🔍 Tra cứu công việc nâng cao")

keyword_input = (
    st.text_input(
        "🔎 Nhập từ khóa cần tìm (các điều kiện cách nhau bằng & hoặc ,)\nVí"
        " dụ: đề tài & cấp cơ sở"
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
    # Tách các từ khóa dựa trên dấu & hoặc ,
    keywords = [
        k.strip() for k in re.split(r"[&,]", keyword_input) if k.strip()
    ]
    st.info(
        f"🔍 Đang tìm theo điều kiện BẮT BUỘC CHỨA ĐỒNG THỜI: **{', '.join(keywords)}**"
    )

    for name, df in detail_dfs.items():
      df.columns = [c.strip() for c in df.columns]
      df_temp = df.copy()

      # Quét trên toàn bộ các cột chữ/đối tượng
      text_cols = [
          c for c in df_temp.columns if df_temp[c].dtype == "object" or c == "id"
      ]

      if text_cols:
        # THAY ĐỔI LOGIC: Dùng phép toán AND (&) cho từng từ khóa
        # Dòng nào phải chứa TẤT CẢ các từ khóa mới được giữ lại
        mask = pd.Series(True, index=df_temp.index)
        for kw in keywords:
          mask_kw = (
              df_temp[text_cols]
              .apply(
                  lambda col: col.astype(str)
                  .str.lower()
                  .str.contains(kw, na=False)
              )
              .any(axis=1)
          )
          mask &= mask_kw  # Dùng &= để bắt buộc thỏa mãn tất cả các từ khóa
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
            f"### 📘 Nhóm kết quả tìm thấy từ bảng: **{name}** — {len(rec_df)}"
            " dòng"
        )

        priority_cols = [
            "name",
            "surname",
            "Loại hoạt động",
            "Vai trò",
            "Cấp độ",
            "Tên sản phẩm",
            "Đợt kê khai",
            "SỐ TIẾT KÊ KHAI",
            "term",
            "code",
        ]
        display_cols = [c for c in priority_cols if c in rec_df.columns]

        st.dataframe(
            rec_df[
                display_cols
                + [c for c in rec_df.columns if c not in display_cols]
            ],
            use_container_width=True,
        )

        # ==========================================================
        # 📈 ĐỒ THỊ VÀ BẢNG THỐNG KÊ ĐẶC THÙ RIÊNG CHO NCKH
        # ==========================================================
        dot_col = next(
            (
                c
                for c in rec_df.columns
                if c.lower() in ["đợt kê khai", "dot ke khai", "term"]
            ),
            None,
        )
        tiet_col = next(
            (
                c
                for c in rec_df.columns
                if any(x in c.lower() for x in ["số tiết kê khai", "tiết"])
            ),
            None,
        )

        if name.upper().startswith("NCKH") and dot_col and tiet_col:
          st.markdown(
              "#### 📆 Thống kê chi tiết NCKH theo Đợt kê khai, Năm học, Loại"
              " hoạt động & Cấp độ"
          )
          df_nckh = rec_df.copy()
          df_nckh[tiet_col] = pd.to_numeric(
              df_nckh[tiet_col], errors="coerce"
          ).fillna(0)

          # Quy đổi cột Đợt kê khai thành Năm học
          df_nckh["Năm học"] = df_nckh[dot_col].apply(quy_doi_nam_hoc)

          # Xác định cột Loại hoạt động và Cấp độ
          loai_col = next(
              (
                  c
                  for c in df_nckh.columns
                  if any(
                      x in c.lower()
                      for x in ["loại hoạt động", "phân loại", "loại"]
                  )
              ),
              None,
          )
          cap_col = next(
              (
                  c
                  for c in df_nckh.columns
                  if any(x in c.lower() for x in ["cấp độ", "cấp"])
              ),
              None,
          )

          tab1, tab2 = st.tabs([
              "📅 Tab 1: Đợt kê khai & Năm học",
              "📌 Tab 2: Loại hoạt động & Cấp độ chéo Năm học",
          ])

          # --- TAB 1: THỐNG KÊ ĐỢT KÊ KHAI & NĂM HỌC ---
          with tab1:
            col_dot, col_year = st.columns(2)

            with col_dot:
              st.markdown("**📋 Tổng tiết & sản phẩm theo đợt kê khai**")
              df_dot = (
                  df_nckh.groupby(dot_col)[tiet_col]
                  .agg(
                      **{
                          "Tổng số tiết kê khai": "sum",
                          "Số lượng sản phẩm": "count",
                      }
                  )
                  .reset_index()
                  .sort_values(dot_col)
              )
              total_dot_tiet = df_dot["Tổng số tiết kê khai"].sum()
              total_dot_sp = df_dot["Số lượng sản phẩm"].sum()

              df_dot_disp = df_dot.copy()
              df_dot_disp.loc[len(df_dot_disp)] = [
                  "**Tổng cộng**",
                  total_dot_tiet,
                  total_dot_sp,
              ]
              st.dataframe(df_dot_disp, use_container_width=True)

            with col_year:
              st.markdown("**📅 Tổng tiết & sản phẩm gộp theo năm học**")
              df_year = (
                  df_nckh.groupby("Năm học")[tiet_col]
                  .agg(
                      **{
                          "Tổng số tiết kê khai": "sum",
                          "Số lượng sản phẩm": "count",
                      }
                  )
                  .reset_index()
                  .sort_values("Năm học")
              )
              total_year_tiet = df_year["Tổng số tiết kê khai"].sum()
              total_year_sp = df_year["Số lượng sản phẩm"].sum()

              df_year_disp = df_year.copy()
              df_year_disp.loc[len(df_year_disp)] = [
                  "**Tổng cộng**",
                  total_year_tiet,
                  total_year_sp,
              ]
              st.dataframe(df_year_disp, use_container_width=True)

            # Vẽ biểu đồ Năm học
            df_plot = df_year[df_year["Năm học"] != "**Tổng cộng**"]
            if not df_plot.empty:
              fig, ax = plt.subplots(figsize=(6, 3))
              bars = ax.bar(
                  df_plot["Năm học"],
                  df_plot["Tổng số tiết kê khai"],
                  color="#4C72B0",
              )
              for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                )
              ax.set_xlabel("Năm học", fontsize=9)
              ax.set_ylabel("Tổng số tiết kê khai", fontsize=9)
              ax.tick_params(axis="x", rotation=45)

              col1_chart, col2_chart, col3_chart = st.columns([2, 7, 2])
              with col2_chart:
                st.pyplot(fig, bbox_inches="tight")

          # --- TAB 2: THỐNG KÊ LOẠI HOẠT ĐỘNG VÀ CẤP ĐỘ ---
          with tab2:
            group_cols = []
            if loai_col:
              group_cols.append(loai_col)
            if cap_col:
              group_cols.append(cap_col)

            if group_cols:
              group_cols.append("Năm học")
              st.markdown(
                  "##### 📊 Bảng thống kê Loại hoạt động, Cấp độ chéo với Năm"
                  " học"
              )

              # Thống kê gồm Tổng số tiết và Tổng số hoạt động (tần suất đếm)
              df_cross = (
                  df_nckh.groupby(group_cols)[tiet_col]
                  .agg(
                      **{
                          "Tổng số tiết kê khai": "sum",
                          "Tổng số hoạt động": "count",
                      }
                  )
                  .reset_index()
              )

              st.dataframe(df_cross, use_container_width=True)
            else:
              st.info(
                  "ℹ️ Không tìm thấy cột 'Loại hoạt động' hoặc 'Cấp độ' trong"
                  " bảng NCKH."
              )
    else:
      st.warning("❌ Không tìm thấy dữ liệu phù hợp.")
else:
  st.info(
      "👆 Nhập từ khóa (có thể nhiều điều kiện nối bằng & hoặc ,) để bắt đầu."
  )


# ==========================================================
# 📊 BIỂU ĐỒ THỐNG KÊ TỔNG HỢP KẾT QUẢ TÌM KIẾM THEO NĂM & NĂM HỌC
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
  st.markdown(
      "#### 📈 Thống kê tổng số tiết thực hiện theo Năm / Năm học (Dựa trên kết"
      " quả tìm kiếm)"
  )

  # Nhận diện cột chứa số tiết
  tiet_col_target = next(
      (
          c
          for c in total_rec_df.columns
          if any(
              x in c.lower() for x in ["sỐ tiết kê khai", "tiết", "period"]
          )
      ),
      None,
  )

  # Nhận diện cột thời gian (Đợt kê khai hoặc Năm học)
  time_col_target = next(
      (
          c
          for c in total_rec_df.columns
          if any(x in c.lower() for x in ["đợt kê khai", "năm học", "year"])
      ),
      None,
  )

  if tiet_col_target and time_col_target:
    # Chuẩn hóa dữ liệu số tiết
    total_rec_df[tiet_col_target] = pd.to_numeric(
        total_rec_df[tiet_col_target], errors="coerce"
    ).fillna(0)

    # Quy đổi sang năm học chuẩn nếu cột thời gian là đợt kê khai dạng YYYY-MM
    df_chart_calc = total_rec_df.copy()
    df_chart_calc["Năm học hiển thị"] = df_chart_calc[time_col_target].apply(
        quy_doi_nam_hoc
    )

    # Groupby tính tổng số tiết và đếm số lượng sản phẩm/công việc
    df_summary_chart = (
        df_chart_calc.groupby("Năm học hiển thị")
        .agg(
            **{
                "Tổng số tiết": (tiet_col_target, "sum"),
                "Số lượng công việc": (tiet_col_target, "count"),
            }
        )
        .reset_index()
        .sort_values("Năm học hiển thị")
    )

    # Hiển thị bảng tổng hợp kèm dòng tổng cộng
    total_tiet_val = df_summary_chart["Tổng số tiết"].sum()
    total_sp_val = df_summary_chart["Số lượng công việc"].sum()

    df_summary_display = df_summary_chart.copy()
    df_summary_display.loc[len(df_summary_display)] = [
        "**Tổng cộng**",
        total_tiet_val,
        total_sp_val,
    ]
    st.dataframe(df_summary_display, use_container_width=True)

    # Vẽ biểu đồ cột
    df_plot_data = df_summary_chart[
        df_summary_chart["Năm học hiển thị"] != "**Tổng cộng**"
    ]
    if not df_plot_data.empty:
      fig, ax = plt.subplots(figsize=(7, 3.5))
      bars = ax.bar(
          df_plot_data["Năm học hiển thị"],
          df_plot_data["Tổng số tiết"],
          color="#4C72B0",
      )

      for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h,
            f"{int(h):,}",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

      ax.set_xlabel("Năm học", fontsize=9)
      ax.set_ylabel("Tổng số tiết thực hiện", fontsize=9)
      ax.tick_params(axis="x", rotation=45)

      col_l, col_m, col_r = st.columns([1, 6, 1])
      with col_m:
        st.pyplot(fig, bbox_inches="tight")
  else:
      st.info(
          "ℹ️ Không tìm thấy cột 'SỐ TIẾT KÊ KHAI' hoặc cột thời gian phù hợp"
          " để vẽ biểu đồ tổng hợp."
      )
else:
  st.info("ℹ️ Hãy nhập từ khóa tìm kiếm để hiển thị thống kê và biểu đồ.")