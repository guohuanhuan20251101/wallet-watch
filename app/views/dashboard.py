"""
总览仪表盘 - 卡片风格
"""
import streamlit as st
import pandas as pd
from app.transform.cleaner import get_summary_stats
from app.utils.charts import monthly_trend, category_pie, year_over_year


def show_dashboard(df: pd.DataFrame):
    if df.empty:
        st.info("👋 还没有数据，请在左侧边栏上传微信/支付宝账单", icon="📤")
        return

    stats = get_summary_stats(df)

    # ── KPI 卡片行 ──
    cols = st.columns(4)
    card_data = [
        ("💰 总支出", f"¥{stats['total_expense']:,.0f}", "expense"),
        ("💵 总收入", f"¥{stats['total_income']:,.0f}", "income"),
        ("📝 交易笔数", str(stats["transaction_count"]), "count"),
        ("💎 结余", f"¥{stats['total_income'] - stats['total_expense']:,.0f}", "balance"),
    ]

    for col, (label, value, css_class) in zip(cols, card_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card {css_class}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # 日期范围
    st.caption(f"📅 {stats['date_range']}")

    st.divider()

    # ── 图表行 ──
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">📈 月度收支趋势</p>', unsafe_allow_html=True)
        st.plotly_chart(monthly_trend(df), use_container_width=True, key="dash_monthly")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">🍩 消费类别分布</p>', unsafe_allow_html=True)
        st.plotly_chart(category_pie(df), use_container_width=True, key="dash_pie")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 年度对比 ──
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📅 年度支出对比</p>', unsafe_allow_html=True)
    st.plotly_chart(year_over_year(df), use_container_width=True, key="dash_yoy")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 最近交易表格 ──
    st.markdown('<p class="section-title">🕐 最近交易记录</p>', unsafe_allow_html=True)
    recent = df.sort_values("date", ascending=False).head(15).copy()

    rows_html = ""
    for _, row in recent.iterrows():
        src_cls = "wechat" if row["source"] == "微信" else "alipay"
        amt_cls = "amount-expense" if row["transaction_type"] == "支出" else "amount-income"
        rows_html += f"""
        <tr>
            <td>{row['date']}</td>
            <td>{row['merchant']}</td>
            <td><span class="badge">{row['category']}</span></td>
            <td class="{amt_cls}">¥{row['amount']:.2f}</td>
            <td><span class="badge {src_cls}">{row['source']}</span></td>
        </tr>"""

    st.markdown(f"""
    <table class="styled-table">
        <thead><tr>
            <th>日期</th><th>商户</th><th>类别</th><th>金额</th><th>来源</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)
