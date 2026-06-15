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

    # ── 数据管理（编辑/删除） ──
    st.divider()
    with st.expander("🔧 数据管理 - 修改分类 / 删除记录"):
        show_data_editor(df)


def show_data_editor(df: pd.DataFrame):
    """数据编辑界面：修改分类、交易类型、删除"""
    from app.db.models import get_session, FactTransaction, DimCategory, DimSource as DBSource

    session = get_session()
    all_cats = sorted([c.category_name for c in session.query(DimCategory).all()])

    # 搜索过滤
    search = st.text_input("🔍 搜索商户名", placeholder="输入商户名筛选...")
    if search:
        mask = df["merchant"].astype(str).str.contains(search, case=False, na=False)
        edit_df = df[mask].head(50).copy()
    else:
        edit_df = df.head(50).copy()

    if edit_df.empty:
        st.info("无匹配记录")
        session.close()
        return

    # 选择要修改的记录
    st.caption(f"共 {len(edit_df)} 条，选择要修改的记录：")

    record_options = [
        f"{r['date']} | {r['merchant']} | ¥{r['amount']:.2f} | {r['category']} | {r['transaction_type']}"
        for _, r in edit_df.iterrows()
    ]
    selected_idx = st.selectbox("选择记录", range(len(record_options)),
                                format_func=lambda i: record_options[i])

    if selected_idx is not None:
        selected = edit_df.iloc[selected_idx]

        col1, col2, col3 = st.columns(3)
        with col1:
            new_cat = st.selectbox(
                "🏷️ 修改类别",
                all_cats,
                index=all_cats.index(selected["category"]) if selected["category"] in all_cats else 0,
            )
        with col2:
            new_type = st.selectbox(
                "💰 修改类型",
                ["支出", "收入"],
                index=0 if selected["transaction_type"] == "支出" else 1,
            )
        with col3:
            new_merchant = st.text_input("✏️ 修改商户名", value=selected["merchant"])

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ 保存修改", use_container_width=True):
                cat_obj = session.query(DimCategory).filter_by(category_name=new_cat).first()
                txn = session.query(FactTransaction).filter_by(
                    date_id=pd.to_datetime(selected["date"]).date(),
                    amount=selected["amount"],
                    merchant=selected["merchant"],
                ).first()
                if txn and cat_obj:
                    txn.category_id = cat_obj.category_id
                    txn.transaction_type = new_type
                    txn.merchant = new_merchant
                    session.commit()
                    st.success("已保存！刷新页面即可看到变化")
                    st.rerun()
                else:
                    st.error("保存失败，请刷新后重试")

        with col_btn2:
            if st.button("🗑️ 删除此记录", use_container_width=True):
                from app.db.models import FactTransaction as FT
                txn = session.query(FT).filter_by(
                    date_id=pd.to_datetime(selected["date"]).date(),
                    amount=selected["amount"],
                    merchant=selected["merchant"],
                ).first()
                if txn:
                    session.delete(txn)
                    session.commit()
                    st.success("已删除！刷新页面即可看到变化")
                    st.rerun()

    session.close()
