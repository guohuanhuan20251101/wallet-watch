"""
总览仪表盘 - 卡片风格
"""
import streamlit as st
import pandas as pd
import io
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

    # ── 第二行：统计指标 ──
    expense_df = df[df["transaction_type"] == "支出"]
    if not expense_df.empty:
        daily_expense = expense_df.groupby("date")["amount"].sum()
        cols2 = st.columns(3)
        with cols2[0]:
            st.metric("📆 日均支出", f"¥{daily_expense.mean():.0f}")
        with cols2[1]:
            st.metric("🔺 最高单日支出", f"¥{daily_expense.max():.0f}")
        with cols2[2]:
            st.metric("🔻 最低单日支出", f"¥{daily_expense[daily_expense > 0].min():.0f}")

    st.divider()

    # ── 商家 TOP10 + 图表行 ──
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">🏪 商家消费 TOP10</p>', unsafe_allow_html=True)
        if not expense_df.empty:
            merchant_top = expense_df.groupby("merchant").agg(
                金额=("amount", "sum"), 次数=("amount", "count")
            ).sort_values("金额", ascending=False).head(10).reset_index()
            merchant_top["金额"] = merchant_top["金额"].round(2)
            merchant_top.index = range(1, len(merchant_top) + 1)
            merchant_top.index.name = "排名"
            st.dataframe(merchant_top, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">🍩 消费类别分布</p>', unsafe_allow_html=True)
        st.plotly_chart(category_pie(df), use_container_width=True, key="dash_pie")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 月度趋势（独立一行）──
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📈 月度收支趋势</p>', unsafe_allow_html=True)
    st.plotly_chart(monthly_trend(df), use_container_width=True, key="dash_monthly")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 年度对比 ──
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📅 年度支出对比</p>', unsafe_allow_html=True)
    st.plotly_chart(year_over_year(df), use_container_width=True, key="dash_yoy")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 消费洞察 ──
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">💡 消费洞察</p>', unsafe_allow_html=True)
    show_insights(df)
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

    # ── 数据管理（编辑/删除/导出/上传历史） ──
    st.divider()
    with st.expander("🔧 数据管理 - 修改分类 / 删除记录 / 导出报告 / 上传历史"):
        # 上传历史
        show_upload_history()

        st.divider()
        # 导出按钮
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # 汇总
                summary_data = {
                    "指标": ["总支出", "总收入", "交易笔数", "日均支出"],
                    "数值": [stats["total_expense"], stats["total_income"],
                            stats["transaction_count"], stats["avg_daily_expense"]],
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name="汇总", index=False)

                # 分类统计
                expense_df2 = df[df["transaction_type"] == "支出"]
                if not expense_df2.empty:
                    cat_summary = expense_df2.groupby("category")["amount"].agg(["sum", "count", "mean"]).round(2)
                    cat_summary.columns = ["总金额", "笔数", "平均金额"]
                    cat_summary.to_excel(writer, sheet_name="分类统计")

                # 每日汇总
                daily_sum = df.groupby("date")["amount"].agg(["sum", "count"])
                daily_sum.columns = ["总金额", "笔数"]
                daily_sum.to_excel(writer, sheet_name="每日汇总")

                # 全部明细
                df.to_excel(writer, sheet_name="明细数据", index=False)

            st.download_button(
                label="📥 导出 Excel 报告",
                data=output.getvalue(),
                file_name=f"wallet_watch_report_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.divider()
        show_data_editor(df)


def show_upload_history():
    """显示上传历史"""
    from app.db.models import get_session, FactTransaction
    session = get_session()
    try:
        batches = session.query(
            FactTransaction.upload_batch
        ).filter(FactTransaction.upload_batch.isnot(None)).distinct().all()

        if not batches:
            st.caption("暂无上传记录")
            return

        history = []
        for (batch,) in batches:
            txns = session.query(FactTransaction).filter_by(upload_batch=batch).all()
            if not txns:
                continue
            dates = [t.date_id for t in txns]
            history.append({
                "文件名": batch.rsplit("_", 2)[0] if "_" in batch else batch,
                "上传时间": batch.rsplit("_", 1)[-1].split("_")[0] if "_" in batch else "未知",
                "记录数": len(txns),
                "日期范围": f"{min(dates)} ~ {max(dates)}",
                "batch": batch,
            })

        if history:
            st.markdown("**📂 上传历史**")
            hist_df = pd.DataFrame(history)
            st.dataframe(
                hist_df[["文件名", "记录数", "日期范围"]],
                use_container_width=True, hide_index=True,
            )

            # 删除某个批次
            batch_to_delete = st.selectbox(
                "选择要删除的批次（仅删除该批次数据，不影响其他批次）",
                ["—"] + [h["batch"] for h in history],
            )
            if batch_to_delete != "—":
                if st.button(f"🗑️ 删除批次「{batch_to_delete.rsplit('_', 2)[0]}」的数据", type="secondary"):
                    count = session.query(FactTransaction).filter_by(
                        upload_batch=batch_to_delete
                    ).delete()
                    session.commit()
                    st.success(f"已删除 {count} 条记录")
                    st.rerun()
    finally:
        session.close()


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


def show_insights(df: pd.DataFrame):
    """纯数据洞察，不说教"""
    if df.empty or len(df) < 5:
        st.info("数据太少，多上传几个月账单就能看到洞察了")
        return

    df = df.copy()
    df["date_dt"] = pd.to_datetime(df["date"])
    df["month"] = df["date_dt"].dt.to_period("M")
    expense = df[df["transaction_type"] == "支出"]

    if expense.empty:
        return

    months = sorted(df["month"].unique())
    current_month = months[-1]
    curr_expense = expense[expense["month"] == current_month]
    curr_total = curr_expense["amount"].sum()
    curr_days = curr_expense["date_dt"].dt.date.nunique()
    curr_daily = curr_total / max(curr_days, 1)

    insights = []

    # 1. 本月概况
    insights.append(f"📊 本月（{current_month}）共支出 **¥{curr_total:,.0f}**，"
                    f"日均 **¥{curr_daily:.0f}**，共 {len(curr_expense)} 笔交易")

    # 2. 环比变化
    if len(months) >= 2:
        prev_month = months[-2]
        prev_expense = expense[expense["month"] == prev_month]
        prev_total = prev_expense["amount"].sum()
        if prev_total > 0:
            change = curr_total - prev_total
            pct = change / prev_total * 100
            direction = "多" if change > 0 else "少"
            insights.append(f"📈 比上月（{prev_month}）{direction}花了 **¥{abs(change):,.0f}**"
                            f"（{pct:+.1f}%）")

            # 哪个类别变化最大
            curr_cat = curr_expense.groupby("category")["amount"].sum()
            prev_cat = prev_expense.groupby("category")["amount"].sum()
            cat_change = (curr_cat - prev_cat).abs()
            if not cat_change.empty:
                top_cat = cat_change.idxmax()
                top_diff = curr_cat.get(top_cat, 0) - prev_cat.get(top_cat, 0)
                if abs(top_diff) > 1:
                    direction2 = "增加" if top_diff > 0 else "减少"
                    insights.append(f"   → 变化最大是「{top_cat}」，比上月{direction2}了 **¥{abs(top_diff):,.0f}**")

    # 3. 最大单笔
    max_row = expense.loc[expense["amount"].idxmax()]
    insights.append(f"💣 本月最大单笔消费：**¥{max_row['amount']:,.0f}**"
                    f"（{max_row['date']} · {max_row['merchant']}）")

    # 4. 高频消费
    merchant_freq = expense["merchant"].value_counts()
    if merchant_freq.iloc[0] >= 5:
        top_merchant = merchant_freq.index[0]
        top_count = merchant_freq.iloc[0]
        top_merchant_total = expense[expense["merchant"] == top_merchant]["amount"].sum()
        insights.append(f"🏪 本月在「{top_merchant}」消费了 **{top_count} 次**，"
                        f"合计 ¥{top_merchant_total:,.0f}")

    # 5. 周末 vs 工作日
    df["dow"] = df["date_dt"].dt.dayofweek
    weekend_expense = df[(df["dow"] >= 5) & (df["transaction_type"] == "支出")]
    weekday_expense = df[(df["dow"] < 5) & (df["transaction_type"] == "支出")]
    if len(weekend_expense) > 0 and len(weekday_expense) > 0:
        we_daily = weekend_expense["amount"].sum() / max(weekend_expense["date_dt"].dt.date.nunique(), 1)
        wd_daily = weekday_expense["amount"].sum() / max(weekday_expense["date_dt"].dt.date.nunique(), 1)
        if wd_daily > 0:
            ratio = we_daily / wd_daily
            insights.append(f"📅 周末日均消费 **¥{we_daily:.0f}**，"
                            f"工作日日均 **¥{wd_daily:.0f}**（周末是工作日的 {ratio:.1f} 倍）")

    # 6. 入不敷出
    income_total = df[df["transaction_type"] == "收入"]["amount"].sum()
    if income_total < curr_total and income_total > 0:
        gap = curr_total - income_total
        insights.append(f"⚖️ 本月支出 ¥{curr_total:,.0f}，收入 ¥{income_total:,.0f}，"
                        f"缺口 ¥{gap:,.0f}")

    # 渲染
    for insight in insights:
        st.markdown(insight)

    if not insights:
        st.info("暂无足够数据生成洞察")

