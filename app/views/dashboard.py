"""
总览仪表盘
"""
import streamlit as st
import pandas as pd
from datetime import date
from app.transform.cleaner import get_summary_stats
from app.utils.charts import monthly_trend, category_pie, year_over_year


def show_dashboard(df: pd.DataFrame):
    """展示总览仪表盘"""
    st.header("📊 财务总览")

    if df.empty:
        st.info("👋 还没有数据，请先在侧边栏上传账单")
        return

    stats = get_summary_stats(df)

    # ---- 指标卡片 ----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 总支出", f"¥{stats['total_expense']:,.0f}")
    with col2:
        st.metric("💵 总收入", f"¥{stats['total_income']:,.0f}")
    with col3:
        st.metric("📝 交易笔数", f"{stats['transaction_count']}")
    with col4:
        net = stats["total_income"] - stats["total_expense"]
        delta_color = "normal" if net >= 0 else "inverse"
        st.metric("💎 结余", f"¥{net:,.0f}", delta_color=delta_color)

    # 数据范围
    st.caption(f"📅 数据范围: {stats['date_range']}")

    st.divider()

    # ---- 月度趋势 ----
    st.subheader("📈 月度收支趋势")
    st.plotly_chart(monthly_trend(df), use_container_width=True)

    # ---- 类别分析 ----
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("🍩 消费类别分布")
        st.plotly_chart(category_pie(df), use_container_width=True)

    with col_right:
        st.subheader("📅 年度对比")
        st.plotly_chart(year_over_year(df), use_container_width=True)

    # ---- 最近交易 ----
    st.divider()
    st.subheader("🕐 最近交易记录")
    recent = df.sort_values("date", ascending=False).head(20).copy()
    recent["date"] = recent["date"].astype(str)
    recent_display = recent[["date", "merchant", "category", "amount", "source", "transaction_type"]]
    recent_display.columns = ["日期", "商户", "类别", "金额", "来源", "类型"]
    st.dataframe(recent_display, use_container_width=True, hide_index=True)
