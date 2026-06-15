"""
日视图：当月每日消费分析
"""
import streamlit as st
import pandas as pd
from datetime import date
from app.utils.charts import daily_bar_line, monthly_category_stack


def show_daily(df: pd.DataFrame):
    """展示日维度分析"""
    st.header("📆 每日消费分析")

    if df.empty:
        st.info("请先上传账单")
        return

    df_with_dt = df.copy()
    df_with_dt["date"] = pd.to_datetime(df["date"])

    # 月份选择器
    years = sorted(df_with_dt["date"].dt.year.unique(), reverse=True)
    if not years:
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_year = st.selectbox("选择年份", years, key="daily_year")
    with col2:
        months = sorted(
            df_with_dt[df_with_dt["date"].dt.year == selected_year]["date"].dt.month.unique(),
            reverse=True
        )
        if months:
            selected_month = st.selectbox("选择月份", months, key="daily_month")
        else:
            st.warning("该年无数据")
            return

    # 来源筛选
    sources = ["全部", "微信", "支付宝"]
    selected_source = st.radio("🔀 数据来源", sources, horizontal=True, key="daily_source")

    # 按来源过滤
    view_df = df_with_dt.copy()
    if selected_source != "全部":
        view_df = view_df[view_df["source"] == selected_source]

    # ---- 图表 ----
    tab1, tab2 = st.tabs(["📊 每日趋势", "🍱 分类构成"])

    with tab1:
        st.plotly_chart(
            daily_bar_line(view_df, selected_month, selected_year),
            use_container_width=True,
        )

    with tab2:
        st.plotly_chart(
            monthly_category_stack(view_df, selected_month, selected_year),
            use_container_width=True,
        )

    # ---- 当月每日明细表 ----
    st.subheader(f"📋 {selected_year}年{selected_month}月 每日明细")

    mask = (view_df["date"].dt.month == selected_month) & (view_df["date"].dt.year == selected_year)
    daily_detail = view_df[mask].groupby("date").agg(
        消费笔数=("amount", "count"),
        总支出=("amount", lambda x: x[view_df.loc[x.index, "transaction_type"] == "支出"].sum()),
        总收入=("amount", lambda x: x[view_df.loc[x.index, "transaction_type"] == "收入"].sum()),
    ).reset_index()
    daily_detail["date"] = daily_detail["date"].dt.strftime("%m-%d")
    daily_detail = daily_detail.sort_values("date")
    daily_detail.columns = ["日期", "笔数", "支出", "收入"]

    st.dataframe(daily_detail, use_container_width=True, hide_index=True)
