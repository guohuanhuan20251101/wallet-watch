"""
图表工具函数（用 Plotly 生成交互式图表）
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def daily_bar_line(df: pd.DataFrame, month: int, year: int):
    """
    当月每日消费柱状图 + 累计消费折线
    """
    daily = df[
        (pd.to_datetime(df["date"]).dt.month == month) &
        (pd.to_datetime(df["date"]).dt.year == year)
    ].copy()

    if daily.empty:
        return go.Figure().add_annotation(text="该月无数据", showarrow=False)

    daily["date"] = pd.to_datetime(daily["date"])
    daily_agg = daily.groupby("date")["amount"].sum().reset_index()
    daily_agg = daily_agg.sort_values("date")
    daily_agg["累计"] = daily_agg["amount"].cumsum()

    # 补全当月所有日期
    date_range = pd.date_range(start=f"{year}-{month:02d}-01",
                               end=f"{year}-{month:02d}-{pd.Timestamp(year, month, 1).days_in_month}")
    full = pd.DataFrame({"date": date_range})
    full = full.merge(daily_agg, on="date", how="left")
    full["amount"] = full["amount"].fillna(0)
    full["累计"] = full["累计"].ffill().fillna(0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=full["date"],
            y=full["amount"],
            name="日消费",
            marker_color="#FF6B6B",
            hovertemplate="日期: %{x|%m-%d}<br>消费: ¥%{y:.2f}",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=full["date"],
            y=full["累计"],
            name="累计消费",
            line=dict(color="#4ECDC4", width=3),
            hovertemplate="累计: ¥%{y:.2f}",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=f"{year}年{month}月 每日消费趋势",
        hovermode="x unified",
        height=400,
        xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text="日消费 (元)", secondary_y=False)
    fig.update_yaxes(title_text="累计消费 (元)", secondary_y=True)

    return fig


def monthly_trend(df: pd.DataFrame):
    """
    月度消费趋势折线图
    """
    if df.empty:
        return go.Figure()

    df = df.copy()
    df["year_month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
    monthly = df.groupby(["year_month", "transaction_type"])["amount"].sum().reset_index()
    monthly = monthly.pivot(index="year_month", columns="transaction_type", values="amount").fillna(0)
    monthly = monthly.reset_index()

    fig = go.Figure()

    colors = {"支出": "#FF6B6B", "收入": "#2ED573"}
    for col in monthly.columns:
        if col == "year_month":
            continue
        fig.add_trace(go.Bar(
            x=monthly["year_month"], y=monthly[col],
            name=col,
            marker_color=colors.get(col, "#636EFA"),
            hovertemplate=f"{col}: ¥{{y:.0f}}",
        ))

    fig.update_layout(
        title="月度收支趋势",
        xaxis_title="",
        yaxis_title="金额 (元)",
        barmode="group",
        height=400,
        hovermode="x unified",
    )

    return fig


def category_pie(df: pd.DataFrame):
    """
    消费类别饼图
    """
    expense = df[df["transaction_type"] == "支出"]
    if expense.empty:
        return go.Figure()

    cat_data = expense.groupby("category")["amount"].sum().sort_values(ascending=False)
    cat_data = cat_data[cat_data > 0]

    fig = go.Figure(data=[go.Pie(
        labels=cat_data.index,
        values=cat_data.values,
        hole=0.4,
        textinfo="label+percent",
        textposition="outside",
        hovertemplate="%{label}<br>¥%{value:.2f}<br>占比: %{percent}",
    )])

    fig.update_layout(
        title="消费类别分布",
        height=400,
    )

    return fig


def year_heatmap(df: pd.DataFrame, year: int):
    """
    年度消费热力图 (12个月 × 类别)
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    year_df = df[
        (df["date"].dt.year == year) &
        (df["transaction_type"] == "支出")
    ].copy()

    if year_df.empty:
        return go.Figure().add_annotation(text=f"{year}年无数据", showarrow=False)

    year_df["month"] = year_df["date"].dt.month
    heat_data = year_df.groupby(["month", "category"])["amount"].sum().reset_index()

    # pivot 成矩阵
    pivot = heat_data.pivot(index="category", columns="month", values="amount").fillna(0)

    fig = go.Figure(data=[go.Heatmap(
        z=pivot.values,
        x=[f"{m}月" for m in pivot.columns],
        y=pivot.index,
        colorscale="Reds",
        hovertemplate="月份: %{x}<br>类别: %{y}<br>消费: ¥%{z:.0f}",
        colorbar=dict(title="金额 (元)"),
    )])

    fig.update_layout(
        title=f"{year}年 消费热力图",
        height=400,
        xaxis_title="",
        yaxis_title="",
    )

    return fig


def monthly_category_stack(df: pd.DataFrame, month: int, year: int):
    """
    当月各类别每日消费堆叠图
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    mask = (df["date"].dt.month == month) & (df["date"].dt.year == year) & (df["transaction_type"] == "支出")
    data = df[mask].copy()

    if data.empty:
        return go.Figure().add_annotation(text="该月无数据", showarrow=False)

    daily_cat = data.groupby(["date", "category"])["amount"].sum().reset_index()
    pivot = daily_cat.pivot(index="date", columns="category", values="amount").fillna(0)

    fig = go.Figure()
    for col in pivot.columns:
        fig.add_trace(go.Bar(
            x=pivot.index,
            y=pivot[col],
            name=col,
        ))

    fig.update_layout(
        title=f"{year}年{month}月 每日消费构成",
        barmode="stack",
        height=400,
        xaxis_title="",
        yaxis_title="金额 (元)",
        hovermode="x unified",
    )

    return fig


def year_over_year(df: pd.DataFrame):
    """年度同比/环比"""
    if df.empty:
        return go.Figure()

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    yearly = df[df["transaction_type"] == "支出"].groupby("year")["amount"].sum().reset_index()

    if len(yearly) < 2:
        return go.Figure().add_annotation(text="需至少两个年份的数据", showarrow=False)

    fig = go.Figure(data=[
        go.Bar(x=yearly["year"].astype(str), y=yearly["amount"],
               marker_color="#FF6B6B", text=yearly["amount"].round(0),
               textposition="outside", name="年度总支出")
    ])

    fig.update_layout(
        title="年度支出对比",
        height=350,
        xaxis_title="",
        yaxis_title="金额 (元)",
    )

    return fig
