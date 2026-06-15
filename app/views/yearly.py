"""
年视图：年度趋势 + 热力图
"""
import streamlit as st
import pandas as pd
from app.utils.charts import year_heatmap, year_over_year


def show_yearly(df: pd.DataFrame):
    """展示年维度分析"""
    st.header("📅 年度分析")

    if df.empty:
        st.info("请先上传账单")
        return

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    years = sorted(df["year"].unique(), reverse=True)

    # 来源筛选
    sources = ["全部", "微信", "支付宝"]
    selected_source = st.radio("🔀 数据来源", sources, horizontal=True, key="yearly_source")

    view_df = df.copy()
    if selected_source != "全部":
        view_df = view_df[view_df["source"] == selected_source]

    # ---- 年度对比 ----
    st.subheader("📊 年度支出对比")
    st.plotly_chart(year_over_year(view_df), use_container_width=True, key="yearly_yoy")

    # ---- 热力图 ----
    st.subheader("🔥 年度消费热力图")
    col1, _ = st.columns([1, 3])
    with col1:
        selected_year = st.selectbox("选择年份", years, key="heatmap_year")

    st.plotly_chart(year_heatmap(view_df, selected_year), use_container_width=True, key="yearly_heatmap")

    # ---- 年度汇总表 ----
    st.subheader("📋 年度汇总")

    for y in years:
        yr_df = view_df[view_df["year"] == y]
        if yr_df.empty:
            continue

        expense = yr_df[yr_df["transaction_type"] == "支出"]["amount"].sum()
        income = yr_df[yr_df["transaction_type"] == "收入"]["amount"].sum()
        count = len(yr_df)
        avg_month = expense / max(yr_df["month"].nunique(), 1)
        net = income - expense

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric(f"📅 {y}年", f"{count}笔")
        col2.metric("💰 总支出", f"¥{expense:,.0f}")
        col3.metric("💵 总收入", f"¥{income:,.0f}")
        col4.metric("📆 月均支出", f"¥{avg_month:,.0f}")
        col5.metric("💎 结余", f"¥{net:,.0f}",
                     delta_color="normal" if net >= 0 else "inverse")

        # 年度 Top5 类别
        top5 = (
            yr_df[yr_df["transaction_type"] == "支出"]
            .groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        if not top5.empty:
            st.caption(f"🔥 {y}年 TOP5 支出类别: " + "  |  ".join(
                [f"{cat} ¥{amt:,.0f}" for cat, amt in top5.items()]
            ))

        st.divider()
