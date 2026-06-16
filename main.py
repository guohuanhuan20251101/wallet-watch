"""
💸 Wallet Watch — 个人财务分析工具
"""
import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
from pathlib import Path

from app.db.models import get_session, DimCategory, DimSource, FactTransaction
from app.db.init_db import init_all
from app.etl.parser_wechat import parse_wechat
from app.etl.parser_alipay import parse_alipay
from app.transform.cleaner import clean_transactions
from app.transform.categorizer import classify_transactions
from app.views.dashboard import show_dashboard
from app.views.daily import show_daily
from app.views.monthly import show_monthly
from app.views.yearly import show_yearly

# ──────────────────── 页面配置 ────────────────────
st.set_page_config(
    page_title="Wallet Watch · 个人财务",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────── 自定义 CSS ────────────────────
st.markdown("""
<style>
    /* ── 全局 ── */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    }

    /* ── 顶部导航栏 ── */
    .nav-bar {
        display: flex; align-items: center; gap: 24px;
        padding: 12px 0 8px 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 24px;
    }
    .nav-logo { font-size: 22px; font-weight: 700; color: #1a1a2e; }
    .nav-logo span { color: #6c5ce7; }

    /* ── KPI 指标卡 ── */
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-top: 3px solid #ccc;
    }
    .kpi-card.expense  { border-top-color: #e74c3c; }
    .kpi-card.income  { border-top-color: #2ecc71; }
    .kpi-card.count   { border-top-color: #3498db; }
    .kpi-card.balance { border-top-color: #6c5ce7; }
    .kpi-label  { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value  { font-size: 26px; font-weight: 700; color: #1a1a2e; margin: 4px 0; }
    .kpi-sub    { font-size: 12px; color: #aaa; }

    /* ── 表格美化 ── */
    .styled-table {
        width: 100%; border-collapse: collapse;
        font-size: 13px;
    }
    .styled-table thead th {
        background: #f8f9fc; color: #555; font-weight: 600;
        padding: 10px 12px; text-align: left; border-bottom: 2px solid #e0e0e0;
    }
    .styled-table tbody td {
        padding: 8px 12px; border-bottom: 1px solid #f0f0f0;
    }
    .styled-table tbody tr:hover { background: #f0f4ff; }
    .amount-expense { color: #e74c3c; font-weight: 600; }
    .amount-income  { color: #2ecc71; font-weight: 600; }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 11px; font-weight: 500;
        background: #e8ecf1; color: #555;
    }
    .badge.wechat  { background: #e8f5e9; color: #2e7d32; }
    .badge.alipay  { background: #e3f2fd; color: #1565c0; }

    /* ── 图表容器 ── */
    .chart-box {
        background: white; border-radius: 12px; padding: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-bottom: 16px;
    }

    /* ── 侧边栏 ── */
    section[data-testid="stSidebar"] {
        background: #1a1a2e;
    }
    section[data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: #6c5ce7 !important; border: none !important;
    }

    /* ── 标题 ── */
    .page-title { font-size: 20px; font-weight: 700; color: #1a1a2e; margin-bottom: 16px; }
    .section-title { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 12px; }

    /* ── 隐藏 Streamlit 默认元素 ── */
    #MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ──────────────────── 数据库初始化 ────────────────────
@st.cache_resource
def init_database():
    init_all()

init_database()


# ──────────────────── 加载数据 ────────────────────
@st.cache_data(ttl=30)
def load_all_transactions():
    session = get_session()
    try:
        from app.db.models import FactTransaction, DimSource, DimCategory as DBCat
        txns = session.query(
            FactTransaction.transaction_id,
            FactTransaction.date_id.label("date"),
            FactTransaction.trade_time,
            FactTransaction.amount,
            FactTransaction.merchant,
            FactTransaction.description,
            DimSource.source_name.label("source"),
            DBCat.category_name.label("category"),
            FactTransaction.transaction_type,
        ).join(DimSource, FactTransaction.source_id == DimSource.source_id)\
         .join(DBCat, FactTransaction.category_id == DBCat.category_id)\
         .order_by(FactTransaction.date_id.desc())\
         .all()

        if not txns:
            return pd.DataFrame(columns=[
                "transaction_id", "date", "trade_time", "amount", "merchant", "description",
                "source", "category", "transaction_type"
            ])

        return pd.DataFrame(txns, columns=[
            "transaction_id", "date", "trade_time", "amount", "merchant", "description",
            "source", "category", "transaction_type"
        ])
    finally:
        session.close()



# ──────────────────── 保存到数据库 ────────────────────
def save_to_db(df: pd.DataFrame, batch_name: str):
    session = get_session()
    cats = {c.category_name: c.category_id for c in session.query(DimCategory).all()}
    from app.db.models import DimSource, FactTransaction
    srcs = {s.source_name: s.source_id for s in session.query(DimSource).all()}

    new_count, skip_count = 0, 0
    for _, row in df.iterrows():
        cat_id = cats.get(row["category"], cats.get("其他", list(cats.values())[0]))
        src_id = srcs.get(row["source"])
        if src_id is None:
            continue

        existing = session.query(FactTransaction).filter_by(
            date_id=row["date"], amount=row["amount"], merchant=row["merchant"]
        ).first()

        if existing:
            skip_count += 1
            continue

        session.add(FactTransaction(
            date_id=row["date"], category_id=cat_id, source_id=src_id,
            amount=row["amount"], merchant=row["merchant"],
            trade_time=str(row.get("trade_time", "")) if pd.notna(row.get("trade_time")) else None,
            description=str(row.get("description", "")),
            transaction_type=row["transaction_type"],
            upload_batch=batch_name, created_at=datetime.now(),
        ))
        new_count += 1

    session.commit()
    session.close()
    load_all_transactions.clear()
    return new_count, skip_count


# ──────────────────── 顶部导航 ────────────────────
st.markdown('<div class="nav-bar">'
            '<div class="nav-logo">💸 Wallet <span>Watch</span></div>'
            '<div style="flex:1"></div>'
            '</div>', unsafe_allow_html=True)

# ──────────────────── 侧边栏（可折叠） ────────────────────
with st.sidebar:
    st.markdown("### 📤 导入账单")

    upload_type = st.selectbox(
        "账单类型",
        ["微信 (CSV/Excel)", "支付宝 (CSV/Excel)", "支付宝 PDF", "微信 PDF"],
        label_visibility="collapsed",
    )

    uploaded_file = st.file_uploader(
        "选择文件", type=["csv", "xls", "xlsx", "pdf"],
        label_visibility="collapsed",
        key="bill_uploader",
    )

    # 刚导入完，清空上传器状态并刷新
    if st.session_state.get("import_done"):
        st.session_state["import_done"] = False
        st.session_state.pop("bill_uploader", None)
        st.rerun()

    if uploaded_file:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        try:
            with st.spinner("解析中..."):
                if "微信 (CSV" in upload_type:
                    raw_df = parse_wechat(tmp_path)
                elif "支付宝 (CSV" in upload_type:
                    raw_df = parse_alipay(tmp_path)
                elif "支付宝 PDF" in upload_type:
                    from app.etl.parser_pdf import parse_pdf
                    raw_df = parse_pdf(tmp_path, source="支付宝")
                else:
                    from app.etl.parser_pdf import parse_pdf
                    raw_df = parse_pdf(tmp_path, source="微信")

            if raw_df.empty:
                st.error("❌ 未解析到数据，请检查文件格式")
            else:
                st.success(f"📄 解析到 {len(raw_df)} 条记录")
                clean_df = clean_transactions(raw_df)
                classified_df = classify_transactions(clean_df)

                # ── 重叠检测 ──
                existing_dates = load_all_transactions()
                if not existing_dates.empty:
                    new_dates = set(classified_df["date"].unique())
                    old_dates = set(existing_dates["date"].unique())
                    overlap_dates = new_dates & old_dates
                    if overlap_dates:
                        st.warning(f"⚠️ 有 {len(overlap_dates)} 天与已有数据重叠（{min(overlap_dates)} ~ {max(overlap_dates)}）")
                        overlap_choice = st.radio(
                            "重叠部分如何处理？",
                            ["跳过重叠日期（保留已有数据）", "用新数据覆盖已有数据"],
                            key="overlap_choice"
                        )
                        if overlap_choice == "跳过重叠日期（保留已有数据）":
                            classified_df = classified_df[~classified_df["date"].isin(overlap_dates)]
                            if classified_df.empty:
                                st.info("去除重叠后无新数据")
                                st.stop()
                            st.caption(f"去除重叠后剩余 {len(classified_df)} 条新记录")

                with st.expander("📋 预览", expanded=True):
                    preview = classified_df.head(8)[["date", "merchant", "category", "amount", "source"]]
                    preview["date"] = preview["date"].astype(str)
                    st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("✅ 确认导入", type="primary", use_container_width=True):
                    batch = f"{uploaded_file.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    new, skip = save_to_db(classified_df, batch)
                    if new > 0:
                        st.session_state["import_done"] = True
                        st.success(f"导入 {new} 条" + (f"，跳过 {skip} 条重复" if skip else ""))
                        st.rerun()
                    else:
                        st.warning(f"全部 {skip} 条已存在")
        finally:
            os.unlink(tmp_path)

    st.divider()

    # 导航按钮
    if st.button("📂 历史上传文件", use_container_width=True):
        st.session_state["page"] = "history"
        st.rerun()

    st.divider()
    st.caption("💡 数据存储在本地，不会上传到任何服务器")


def show_upload_history_page():
    """历史上传文件 - 独立页面（表格 + 点击预览）"""
    st.markdown("## 📂 历史上传文件")

    if st.button("← 返回主页面"):
        st.session_state["page"] = "dashboard"
        st.rerun()

    st.divider()

    session = get_session()
    try:
        batches_raw = session.query(
            FactTransaction.upload_batch
        ).filter(FactTransaction.upload_batch.isnot(None)).distinct().all()
    finally:
        session.close()

    if not batches_raw:
        st.info("暂无上传记录，请先在侧边栏上传账单")
        return

    # 构建文件列表
    file_list = []
    for (batch_name,) in batches_raw:
        s = get_session()
        try:
            batch_txns = s.query(FactTransaction).filter_by(upload_batch=batch_name).all()
            if not batch_txns:
                continue
            dates = sorted([t.date_id for t in batch_txns])
            file_list.append({
                "batch": batch_name,
                "name": batch_name.rsplit("_", 2)[0] if "_" in batch_name else batch_name,
                "count": len(batch_txns),
                "start": str(dates[0]),
                "end": str(dates[-1]),
            })
        finally:
            s.close()

    # 渲染表格
    for i, f in enumerate(file_list):
        cols = st.columns([3, 1, 2, 1.5, 1.5])
        with cols[0]:
            st.markdown(f"📄 {f['name']}")
        with cols[1]:
            st.caption(f"{f['count']} 条")
        with cols[2]:
            st.caption(f"{f['start']} ~ {f['end']}")
        with cols[3]:
            if st.button("🔍 预览", key=f"preview_{i}"):
                st.session_state[f"show_preview_{i}"] = not st.session_state.get(f"show_preview_{i}", False)
                st.rerun()
        with cols[4]:
            if st.button("🗑️ 删除", key=f"histdel_{i}"):
                st.session_state[f"confirm_del_{i}"] = True
                st.rerun()

        # 预览展开
        if st.session_state.get(f"show_preview_{i}"):
            s = get_session()
            try:
                batch_txns = s.query(FactTransaction).filter_by(upload_batch=f["batch"]).all()
                cats_map = {c.category_id: c.category_name for c in s.query(DimCategory).all()}
                srcs_map = {src.source_id: src.source_name for src in s.query(DimSource).all()}

                preview_data = []
                for t in batch_txns[:50]:
                    preview_data.append({
                        "日期": str(t.date_id), "商户": t.merchant, "金额": t.amount,
                        "类别": cats_map.get(t.category_id, "其他"),
                        "来源": srcs_map.get(t.source_id, "未知"),
                        "类型": t.transaction_type,
                    })
                st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
                if len(batch_txns) > 50:
                    st.caption(f"... 还有 {len(batch_txns) - 50} 条")

                # 下载
                export_data = []
                for t in batch_txns:
                    export_data.append({
                        "日期": str(t.date_id), "商户": t.merchant, "金额": t.amount,
                        "类别": cats_map.get(t.category_id, "其他"),
                        "来源": srcs_map.get(t.source_id, "未知"),
                        "类型": t.transaction_type,
                    })
                csv_data = pd.DataFrame(export_data).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"📥 下载 {f['name']}.csv", csv_data,
                    file_name=f"{f['name']}.csv", mime="text/csv",
                    key=f"history_dl_btn_{i}",
                )
            finally:
                s.close()

        # 删除确认
        if st.session_state.get(f"confirm_del_{i}"):
            st.warning(f"确定要删除「{f['name']}」的 {f['count']} 条数据吗？")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认", key=f"confirm_yes_{i}", type="primary"):
                    s2 = get_session()
                    s2.query(FactTransaction).filter_by(upload_batch=f["batch"]).delete()
                    s2.commit()
                    s2.close()
                    st.session_state[f"confirm_del_{i}"] = False
                    st.success(f"已删除「{f['name']}」")
                    st.rerun()
            with c2:
                if st.button("❌ 取消", key=f"confirm_no_{i}"):
                    st.session_state[f"confirm_del_{i}"] = False
                    st.rerun()

        st.divider()


# ──────────────────── 页面路由 ────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"

if st.session_state["page"] == "history":
    show_upload_history_page()
else:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 总览", "📆 每日", "📅 月度", "📅 年度"])

    df_all = load_all_transactions()

    with tab1:
        show_dashboard(df_all)
    with tab2:
        show_daily(df_all)
    with tab3:
        show_monthly(df_all)
    with tab4:
        show_yearly(df_all)

    st.divider()
    st.caption("💸 Wallet Watch · 数据存储于本地 SQLite · 不会上传到任何服务器")


