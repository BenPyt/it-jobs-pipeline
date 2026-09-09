"""Dashboard Streamlit: buc tranh thi truong viec lam IT tu du lieu da lam sach.

Chay:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve  # noqa: E402
from src.store import JobStore  # noqa: E402

# --- Bang mau categorical da duoc kiem dinh (thu tu co dinh, khong xoay vong) ---
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PRIMARY = SERIES[0]
MILLION = 1_000_000

cfg = load_config()
st.set_page_config(page_title=cfg.dashboard["page_title"], page_icon="📊", layout="wide")


# ---------------------------------------------------------------- du lieu
SNAPSHOT_CSV = ROOT / "data" / "snapshot" / "jobs_snapshot.csv"
RUNS_CSV = ROOT / "data" / "snapshot" / "runs_snapshot.csv"
SNAPSHOT_META = ROOT / "data" / "snapshot" / "meta.json"


@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, dict]:
    """Doc du lieu theo thu tu uu tien: CSDL cuc bo -> ban chup trong repo.

    Khi chay tren may ban, CSDL SQLite la nguon day du va moi nhat.
    Khi deploy len Streamlit Cloud thi khong co CSDL (thu muc data/ khong len
    Git), nen doc ban chup CSV da commit kem repo. `info` cho biet dang xem
    nguon nao de hien thi dung ghi chu cho nguoi doc.
    """
    db_path = resolve(cfg.paths.db_path)
    if db_path.exists():
        store = JobStore(db_path)
        try:
            df = store.load_jobs()
        finally:
            store.close()
        if not df.empty:
            return df, {"origin": "db"}

    if SNAPSHOT_CSV.exists():
        df = pd.read_csv(SNAPSHOT_CSV)
        for col in ("skills", "locations"):
            if col in df.columns:
                df[col] = df[col].fillna("").apply(
                    lambda v: [x.strip() for x in str(v).split(",") if x.strip()]
                )
        if "salary_disclosed" in df.columns:
            df["salary_disclosed"] = df["salary_disclosed"].astype(bool)
        meta = {}
        if SNAPSHOT_META.exists():
            try:
                meta = json.loads(SNAPSHOT_META.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        return df, {"origin": "snapshot", **meta}

    return pd.DataFrame(), {"origin": "empty"}


@st.cache_data(ttl=300)
def load_runs() -> pd.DataFrame:
    """Lich su cac lan chay pipeline - uu tien CSDL, khong co thi doc ban chup."""
    db_path = resolve(cfg.paths.db_path)
    if db_path.exists():
        store = JobStore(db_path)
        try:
            runs = store.load_runs(limit=90)
        finally:
            store.close()
        if not runs.empty:
            return runs
    if RUNS_CSV.exists():
        return pd.read_csv(RUNS_CSV)
    return pd.DataFrame()


def base_layout(fig: go.Figure, height: int = 340) -> go.Figure:
    """Nen trong suot de dashboard doc duoc o ca giao dien sang lan toi."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=32, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.18)", zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False),
    )
    return fig


df, data_info = load_data()

st.title("📊 Thị trường việc làm IT Việt Nam")

if df.empty:
    st.warning(
        "Chưa có dữ liệu trong CSDL.\n\n"
        "Chạy `python run_pipeline.py` để crawl dữ liệu thật, "
        "hoặc `python scripts/make_sample_raw.py && "
        "python run_pipeline.py --from-raw data/raw/SAMPLE_jobs_demo.json` để xem thử với dữ liệu mô phỏng."
    )
    st.stop()

if data_info.get("origin") == "snapshot":
    exported = str(data_info.get("exported_at", ""))[:10]
    st.info(
        f"Đang xem **bản chụp dữ liệu ngày {exported}** kèm theo mã nguồn "
        f"({data_info.get('n_jobs', len(df))} tin từ ITviec và CareerLink). "
        "Đây không phải dữ liệu thời gian thực — chạy `python run_pipeline.py` "
        "trên máy để crawl bản mới nhất."
    )

if df["url"].astype(str).str.contains("example.invalid").any():
    st.error(
        "⚠️ CSDL đang chứa **dữ liệu mô phỏng** (sinh bởi `scripts/make_sample_raw.py`) — "
        "chỉ dùng để kiểm thử giao diện, **không** phản ánh thị trường thật."
    )

# ---------------------------------------------------------------- bo loc
with st.sidebar:
    st.header("Bộ lọc")
    sources = sorted(df["source"].dropna().unique())
    pick_sources = st.multiselect("Nguồn", sources, default=sources)

    cities = sorted(df["location_primary"].dropna().unique())
    pick_cities = st.multiselect("Thành phố", cities, default=cities)

    levels = [lv for lv in
              ["Intern", "Fresher", "Junior", "Nhân viên", "Middle", "Senior", "Lead",
               "Principal/Architect", "Manager", "Head/Director", "Không rõ"]
              if lv in set(df["seniority"])]
    pick_levels = st.multiselect("Cấp bậc", levels, default=levels)

    only_salary = st.checkbox("Chỉ tin có công bố lương", value=False)
    kw = st.text_input("Từ khoá trong tiêu đề", "")

mask = (
    df["source"].isin(pick_sources)
    & df["seniority"].isin(pick_levels)
    & (df["location_primary"].isin(pick_cities) | df["location_primary"].isna())
)
if only_salary:
    mask &= df["salary_disclosed"]
if kw.strip():
    mask &= df["title"].str.contains(kw.strip(), case=False, na=False)

view = df[mask]
if view.empty:
    st.info("Không có tin nào khớp bộ lọc.")
    st.stop()

# ---------------------------------------------------------------- so lieu chinh
paid = view[view["salary_disclosed"] & view["salary_mid_vnd"].notna()]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Số tin tuyển dụng", f"{len(view):,}")
c2.metric("Số công ty", f"{view['company'].nunique():,}")
c3.metric("Tin công bố lương", f"{100 * view['salary_disclosed'].mean():.0f}%")
c4.metric(
    "Lương trung vị",
    f"{paid['salary_mid_vnd'].median() / MILLION:.1f} tr" if not paid.empty else "—",
    help="Trung vị mức lương giữa khoảng, chỉ tính các tin có công bố lương.",
)

st.caption(
    f"Ghi chú: {100 * (1 - view['salary_disclosed'].mean()):.0f}% số tin không công bố lương "
    "(thường ghi “Thoả thuận” hoặc yêu cầu đăng nhập) — mọi số liệu lương bên dưới chỉ tính trên phần có công bố."
)

tab_overview, tab_skills, tab_salary, tab_data, tab_health = st.tabs(
    ["Tổng quan", "Kỹ năng", "Lương", "Dữ liệu", "Sức khoẻ pipeline"]
)

# ---------------------------------------------------------------- tong quan
with tab_overview:
    left, right = st.columns(2)

    with left:
        st.subheader("Số tin theo thành phố")
        by_city = view["location_primary"].value_counts().head(10).sort_values()
        fig = px.bar(x=by_city.values, y=by_city.index, orientation="h", text=by_city.values)
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0,
                          textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Số tin", yaxis_title=None)
        st.plotly_chart(base_layout(fig), use_container_width=True)

    with right:
        st.subheader("Số tin theo cấp bậc")
        order = ["Intern", "Fresher", "Junior", "Nhân viên", "Middle", "Senior", "Lead",
                 "Principal/Architect", "Manager", "Head/Director", "Không rõ"]
        by_lv = view["seniority"].value_counts()
        by_lv = by_lv.reindex([o for o in order if o in by_lv.index])
        fig = px.bar(x=by_lv.index, y=by_lv.values, text=by_lv.values)
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0,
                          textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title=None, yaxis_title="Số tin")
        st.plotly_chart(base_layout(fig), use_container_width=True)

    left2, right2 = st.columns(2)
    with left2:
        st.subheader("Công ty tuyển nhiều nhất")
        top_co = view["company"].value_counts().head(12).sort_values()
        fig = px.bar(x=top_co.values, y=top_co.index, orientation="h", text=top_co.values)
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0,
                          textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Số tin", yaxis_title=None)
        st.plotly_chart(base_layout(fig, height=420), use_container_width=True)

    with right2:
        st.subheader("Hình thức làm việc")
        arr = view["work_arrangement"].fillna("Không rõ").value_counts().sort_values()
        fig = px.bar(x=arr.values, y=arr.index, orientation="h", text=arr.values)
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0,
                          textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Số tin", yaxis_title=None)
        st.plotly_chart(base_layout(fig, height=420), use_container_width=True)

# ---------------------------------------------------------------- ky nang
with tab_skills:
    top_n = cfg.dashboard["top_n_skills"]
    counter = Counter(s for lst in view["skills"] for s in lst)
    if not counter:
        st.info("Chưa có dữ liệu kỹ năng.")
    else:
        top = pd.Series(dict(counter.most_common(top_n))).sort_values()
        st.subheader(f"Top {len(top)} kỹ năng được yêu cầu nhiều nhất")
        fig = px.bar(x=top.values, y=top.index, orientation="h", text=top.values)
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0,
                          textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="Số tin yêu cầu", yaxis_title=None)
        st.plotly_chart(base_layout(fig, height=26 * len(top) + 90), use_container_width=True)

        st.subheader("Kỹ năng nào đi kèm mức lương cao hơn?")
        rows = []
        for skill, cnt in counter.most_common(40):
            sub = paid[paid["skills"].apply(lambda lst, s=skill: s in lst)]
            if len(sub) >= 3:
                rows.append({
                    "Kỹ năng": skill,
                    "Số tin có lương": len(sub),
                    "Lương trung vị (triệu)": round(sub["salary_mid_vnd"].median() / MILLION, 1),
                })
        if rows:
            tbl = pd.DataFrame(rows).sort_values("Lương trung vị (triệu)", ascending=False)
            st.caption("Chỉ hiển thị kỹ năng có từ 3 tin công bố lương trở lên — dưới ngưỡng đó số trung vị không đáng tin.")
            st.dataframe(tbl, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa đủ tin công bố lương để so sánh theo kỹ năng.")

# ---------------------------------------------------------------- luong
with tab_salary:
    if paid.empty:
        st.info("Không có tin nào công bố lương trong phạm vi lọc hiện tại.")
    else:
        st.subheader("Phân bố mức lương (giữa khoảng)")
        fig = px.histogram(paid, x=paid["salary_mid_vnd"] / MILLION, nbins=30)
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0)
        # khe ho nho giua cac cot de doc duoc ranh gioi bin
        fig.update_layout(xaxis_title="Triệu VND / tháng", yaxis_title="Số tin", bargap=0.03)
        st.plotly_chart(base_layout(fig), use_container_width=True)

        st.subheader("Lương theo cấp bậc")
        order = ["Intern", "Fresher", "Junior", "Nhân viên", "Middle", "Senior", "Lead",
                 "Principal/Architect", "Manager", "Head/Director", "Không rõ"]
        present = [o for o in order if o in set(paid["seniority"])]
        stat = (
            paid.groupby("seniority")["salary_mid_vnd"]
            .agg(["median", "count"])
            .reindex(present)
            .dropna()
        )
        stat["median_tr"] = stat["median"] / MILLION
        fig = px.bar(x=stat.index, y=stat["median_tr"],
                     text=[f"{v:.0f}tr (n={int(n)})" for v, n in zip(stat["median_tr"], stat["count"])])
        fig.update_traces(marker_color=PRIMARY, marker_line_width=0,
                          textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title=None, yaxis_title="Lương trung vị (triệu VND)")
        st.plotly_chart(base_layout(fig, height=380), use_container_width=True)
        st.caption("n = số tin công bố lương ở mỗi cấp bậc. Cấp bậc có n nhỏ chỉ mang tính tham khảo.")

# ---------------------------------------------------------------- du lieu
with tab_data:
    st.subheader("Bảng dữ liệu đã làm sạch")
    show = view.assign(
        skills_text=view["skills"].apply(lambda v: ", ".join(v)),
        salary_tr=(view["salary_mid_vnd"] / MILLION).round(1),
    )[["title", "company", "seniority", "location_primary", "salary_raw",
       "salary_tr", "skills_text", "source", "url"]]
    show.columns = ["Tiêu đề", "Công ty", "Cấp bậc", "Thành phố", "Lương (gốc)",
                    "Lương (triệu)", "Kỹ năng", "Nguồn", "Link"]
    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={"Link": st.column_config.LinkColumn("Link", display_text="mở")},
    )
    st.download_button(
        "Tải CSV theo bộ lọc hiện tại",
        show.to_csv(index=False).encode("utf-8-sig"),
        file_name="it_jobs_filtered.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------- suc khoe
with tab_health:
    st.subheader("Lịch sử các lần chạy pipeline")
    st.caption(
        "Pipeline chạy tự động mỗi ngày. Sau mỗi lần chạy, dữ liệu được đối chiếu với "
        "một bộ quy tắc (số tin tối thiểu mỗi nguồn, tỷ lệ thiếu từng cột, mức sụt giảm "
        "so với lần trước). Mục đích: phát hiện ngay khi trang nguồn đổi giao diện làm "
        "parser gãy, thay vì vài tuần sau mới nhận ra số liệu đứng yên."
    )

    runs = load_runs()
    if runs.empty:
        st.info("Chưa có lịch sử lần chạy nào.")
    else:
        latest = runs.iloc[0]
        status = str(latest.get("status", ""))
        h1, h2, h3 = st.columns(3)
        h1.metric("Lần chạy gần nhất", str(latest.get("started_at", ""))[:16].replace("T", " "))
        h2.metric("Số tin thu được", int(latest.get("n_clean") or 0))
        h3.metric("Số vấn đề phát hiện", int(latest.get("n_issues") or 0))

        if status == "success":
            st.success("Lần chạy gần nhất: bình thường, không có cảnh báo.")
        elif status == "failed_quality":
            st.error("Lần chạy gần nhất **vi phạm ngưỡng chất lượng** — nhiều khả năng parser đã gãy.")
        elif status == "failed":
            st.error("Lần chạy gần nhất **thất bại** trước khi hoàn tất.")

        # Chi tiết vấn đề của lần chạy gần nhất
        raw_quality = latest.get("quality")
        if isinstance(raw_quality, str) and raw_quality.strip():
            try:
                q = json.loads(raw_quality)
            except json.JSONDecodeError:
                q = {}
            for issue in q.get("issues", []):
                line = f"**{issue.get('check')}** — {issue.get('message')}"
                (st.error if issue.get("level") == "failed" else st.warning)(line)

        # Diễn biến số tin qua các lần chạy
        hist = runs.sort_values("run_id").copy()
        hist["Thời điểm"] = pd.to_datetime(hist["started_at"], errors="coerce", utc=True)
        hist = hist.dropna(subset=["Thời điểm"])
        if len(hist) >= 2:
            st.subheader("Số tin thu được qua các lần chạy")
            fig = go.Figure(go.Scatter(
                x=hist["Thời điểm"], y=hist["n_clean"], mode="lines+markers",
                line=dict(color=PRIMARY, width=2), marker=dict(size=8, color=PRIMARY),
                hovertemplate="%{x|%d/%m %H:%M}<br>%{y} tin<extra></extra>",
            ))
            fig.update_layout(xaxis_title=None, yaxis_title="Số tin sau làm sạch")
            st.plotly_chart(base_layout(fig), use_container_width=True)
            st.caption(
                "Đường này tụt đột ngột là dấu hiệu sớm nhất của việc trang nguồn đổi giao diện."
            )

        st.subheader("Bảng lịch sử")
        show_runs = runs[["run_id", "started_at", "sources", "n_raw", "n_clean",
                          "status", "n_issues", "note"]].copy()
        show_runs.columns = ["Lần", "Bắt đầu", "Nguồn", "Tin thô", "Sau làm sạch",
                             "Trạng thái", "Vấn đề", "Ghi chú"]
        st.dataframe(show_runs, use_container_width=True, hide_index=True)
