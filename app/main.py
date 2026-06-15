"""
💸 Wallet Watch — 个人财务分析工具

支持微信 + 支付宝账单导入，自动分类，多维度可视化
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
    page_title="Wallet Watch 💸",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💸 Wallet Watch")
st.caption("个人财务分析工具 · 支持微信 & 支付宝账单 · 数据仅保存在本地")


# ──────────────────── 初始化数据库 ────────────────────
@st.cache_resource
def init_database():
    init_all()


init_database()


# ──────────────────── 加载已存储的数据 ────────────────────
@st.cache_data(ttl=60)
def load_all_transactions():
    """从数据库加载所有交易"""
    session = get_session()
    try:
        records = session.query(FactTransaction).all()
        if not records:
            return pd.DataFrame(columns=[
                "date", "amount", "merchant", "description",
                "source", "category", "transaction_type"
            ])

        data = []
        for t in records:
            cat = session.query(DimCategory).filter_by(category_id=t.category_id).first()
            src = session.query(DimSource).filter_by(source_id=t.source_id).first()
            data.append({
                "date": t.date_id,
                "amount": t.amount,
                "merchant": t.merchant or "",
                "description": t.description or "",
                "source": src.source_name if src else "未知",
                "category": cat.category_name if cat else "其他",
                "transaction_type": t.transaction_type,
            })

        return pd.DataFrame(data)
    finally:
        session.close()


# ──────────────────── 保存到数据库 ────────────────────
def save_to_db(df: pd.DataFrame, batch_name: str):
    """将清洗分类后的数据写入数据库"""
    session = get_session()

    # 获取或创建分类 ID 映射
    cats = {c.category_name: c.category_id for c in session.query(DimCategory).all()}
    srcs = {s.source_name: s.source_id for s in session.query(DimSource).all()}

    new_count = 0
    skip_count = 0

    for _, row in df.iterrows():
        cat_id = cats.get(row["category"])
        src_id = srcs.get(row["source"])

        if cat_id is None:
            cat_id = cats.get("其他", list(cats.values())[0])
        if src_id is None:
            continue

        # 去重检查：同日同金额同商户
        existing = session.query(FactTransaction).filter_by(
            date_id=row["date"],
            amount=row["amount"],
            merchant=row["merchant"],
        ).first()

        if existing:
            skip_count += 1
            continue

        t = FactTransaction(
            date_id=row["date"],
            category_id=cat_id,
            source_id=src_id,
            amount=row["amount"],
            merchant=row["merchant"],
            description=str(row.get("description", "")),
            transaction_type=row["transaction_type"],
            upload_batch=batch_name,
            created_at=datetime.now(),
        )
        session.add(t)
        new_count += 1

    session.commit()
    session.close()

    # 清除缓存让下次加载拿到新数据
    load_all_transactions.clear()

    return new_count, skip_count


# ──────────────────── 页面导航 ────────────────────
page = st.sidebar.radio(
    "📌 导航",
    ["📊 总览", "📆 每日分析", "📅 月度分析", "📅 年度分析"],
)

# ──────────────────── 侧边栏：文件上传 ────────────────────
st.sidebar.divider()
st.sidebar.header("📤 上传账单")

upload_type = st.sidebar.selectbox(
    "账单类型",
    ["微信账单 (CSV/Excel)", "支付宝账单 (CSV/Excel)", "支付宝 PDF 账单", "微信 PDF 账单"],
)

uploaded_file = st.sidebar.file_uploader(
    "选择账单文件",
    type=["csv", "xls", "xlsx", "pdf"],
    help="支持微信和支付宝导出的账单文件",
)

if uploaded_file is not None:
    # 保存到临时文件
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    try:
        with st.spinner("🔍 解析账单中..."):
            # 根据类型解析
            if upload_type == "微信账单 (CSV/Excel)":
                raw_df = parse_wechat(tmp_path)
            elif upload_type == "支付宝账单 (CSV/Excel)":
                raw_df = parse_alipay(tmp_path)
            elif upload_type == "支付宝 PDF 账单":
                from app.etl.parser_pdf import parse_pdf
                raw_df = parse_pdf(tmp_path, source="支付宝")
            elif upload_type == "微信 PDF 账单":
                from app.etl.parser_pdf import parse_pdf
                raw_df = parse_pdf(tmp_path, source="微信")
            else:
                raw_df = pd.DataFrame()

        if raw_df.empty:
            st.sidebar.error("❌ 未能从文件中提取到交易数据，请检查文件格式")
        else:
            st.sidebar.info(f"📄 解析到 {len(raw_df)} 条记录")

            with st.spinner("🧹 清洗 + 分类中..."):
                # 清洗
                clean_df = clean_transactions(raw_df)
                # 分类
                classified_df = classify_transactions(clean_df)

            # 预览
            st.sidebar.subheader("📋 预览（前10条）")
            preview = classified_df.head(10).copy()
            preview["date"] = preview["date"].astype(str)
            st.sidebar.dataframe(
                preview[["date", "merchant", "category", "amount", "source"]],
                use_container_width=True,
                hide_index=True,
            )

            # 保存按钮
            if st.sidebar.button("✅ 确认导入", type="primary", use_container_width=True):
                batch = f"{uploaded_file.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                new, skip = save_to_db(classified_df, batch)

                if new > 0:
                    st.sidebar.success(f"✅ 成功导入 {new} 条新记录" +
                                       (f"，跳过 {skip} 条重复" if skip > 0 else ""))
                    st.rerun()
                else:
                    st.sidebar.warning(f"⚠️ 所有 {skip} 条记录已存在，没有新数据导入")

    finally:
        os.unlink(tmp_path)

# 显示已存储数据统计
st.sidebar.divider()
st.sidebar.caption("💡 上传的账单会自动保存，不删除就不会丢失。数据存储在本地 SQLite 数据库中。")

# ──────────────────── 主页面渲染 ────────────────────
df_all = load_all_transactions()

if df_all.empty and page != "📊 总览":
    st.warning("📭 还没有任何数据，请先在左侧上传账单！")

# 分类纠错工具
st.sidebar.divider()
st.sidebar.header("🏷️ 分类纠错")

# 显示当前分类分布
if not df_all.empty:
    cat_counts = df_all["category"].value_counts().to_dict()
    selected_cat_fix = st.sidebar.selectbox(
        "查看分类", ["全部"] + sorted(cat_counts.keys()),
        key="cat_fix"
    )

    if selected_cat_fix != "全部":
        session = get_session()
        try:
            # 查找该分类对应的 category_id
            cat_obj = session.query(DimCategory).filter_by(category_name=selected_cat_fix).first()
            if cat_obj:
                wrong_txns = session.query(FactTransaction).filter_by(
                    category_id=cat_obj.category_id
                ).order_by(FactTransaction.date_id.desc()).limit(30).all()

                if wrong_txns:
                    fix_data = []
                    for t in wrong_txns:
                        cat = session.query(DimCategory).filter_by(category_id=t.category_id).first()
                        fix_data.append({
                            "日期": str(t.date_id),
                            "商户": t.merchant,
                            "金额": t.amount,
                            "类别": cat.category_name if cat else "未知",
                        })
                    fix_df = pd.DataFrame(fix_data)
                    st.sidebar.dataframe(fix_df, use_container_width=True, hide_index=True)

                    # 批量修改
                    new_cat = st.sidebar.selectbox(
                        "移动到分类",
                        sorted(cats.keys()),
                        key="new_cat"
                    )
                    if st.sidebar.button("🔄 批量修改此分类", use_container_width=True):
                        new_cat_id = cats.get(new_cat)
                        if new_cat_id:
                            count = session.query(FactTransaction).filter_by(
                                category_id=cat_obj.category_id
                            ).update({"category_id": new_cat_id})
                            session.commit()
                            st.sidebar.success(f"已移动 {count} 条记录")
                            load_all_transactions.clear()
                            st.rerun()
        finally:
            session.close()


# 渲染页面
if page == "📊 总览":
    show_dashboard(df_all)
elif page == "📆 每日分析":
    show_daily(df_all)
elif page == "📅 月度分析":
    show_monthly(df_all)
elif page == "📅 年度分析":
    show_yearly(df_all)

# ──────────────────── 页脚 ────────────────────
st.divider()
st.caption("💸 Wallet Watch · 数据存储于本地 SQLite · 不会上传到任何服务器")
