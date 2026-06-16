"""
月视图：月度对比分析
"""
import streamlit as st
import pandas as pd
from app.utils.charts import monthly_trend
from app.views.editor import _render_aggrid


def show_monthly(df: pd.DataFrame):
    """展示月维度分析"""
    st.header("📅 月度对比分析")

    if df.empty:
        st.info("请先上传账单")
        return

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # 年份筛选
    years = sorted(df["year"].unique(), reverse=True)
    selected_year = st.selectbox("选择年份", years, key="monthly_year")

    year_df = df[df["year"] == selected_year]

    # 来源筛选
    sources = ["全部", "微信", "支付宝"]
    selected_source = st.radio("🔀 数据来源", sources, horizontal=True, key="monthly_source")
    if selected_source != "全部":
        year_df = year_df[year_df["source"] == selected_source]

    # 月度趋势图
    st.subheader(f"📈 {selected_year}年 月度趋势")
    st.plotly_chart(monthly_trend(year_df), use_container_width=True, key="monthly_trend")

    # ---- 月度详细对比表 ----
    st.subheader(f"📋 {selected_year}年 月度详细数据")

    # 支出
    expense_monthly = (
        year_df[year_df["transaction_type"] == "支出"]
        .groupby("year_month")["amount"]
        .sum()
        .reset_index()
    )
    expense_monthly.columns = ["月份", "总支出"]

    # 收入
    income_monthly = (
        year_df[year_df["transaction_type"] == "收入"]
        .groupby("year_month")["amount"]
        .sum()
        .reset_index()
    )
    income_monthly.columns = ["月份", "总收入"]

    # 合并
    monthly_summary = expense_monthly.merge(income_monthly, on="月份", how="outer").fillna(0)
    monthly_summary["结余"] = monthly_summary["总收入"] - monthly_summary["总支出"]
    monthly_summary["日均支出"] = (monthly_summary["总支出"] / 30).round(0)

    # 环比
    monthly_summary["较上月变化"] = monthly_summary["总支出"].pct_change() * 100
    monthly_summary["较上月变化"] = monthly_summary["较上月变化"].apply(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
    )

    display = monthly_summary[["月份", "总支出", "总收入", "结余", "日均支出", "较上月变化"]]
    display.columns = ["月份", "总支出", "总收入", "结余", "日均支出", "环比变化"]
    _render_aggrid(display.reset_index(drop=True), key="monthly_summary_aggrid")

    # ---- 分类月度变化 ----
    st.subheader("📊 各分类月度趋势")
    year_df_expense = year_df[year_df["transaction_type"] == "支出"]
    cat_monthly = (
        year_df_expense.groupby(["year_month", "category"])["amount"]
        .sum()
        .reset_index()
    )
    cat_pivot = cat_monthly.pivot(index="year_month", columns="category", values="amount").fillna(0)

    st.bar_chart(cat_pivot, use_container_width=True)
