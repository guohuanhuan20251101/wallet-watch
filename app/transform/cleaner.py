"""
数据清洗模块：去重、异常值处理、标准化
"""
import pandas as pd
from datetime import datetime, date


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗交易数据
    1. 去重
    2. 移除异常金额
    3. 标准化字段
    """
    if df.empty:
        return df

    df = df.copy()

    # 确保日期列正确
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.date

    # 确保金额为数值
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["amount"])
    df["amount"] = df["amount"].abs()

    # 去掉异常大额 (>100万，可能是数据解析错误)
    df = df[df["amount"] < 1_000_000]

    # 去重: 同一天、同一金额、同一商户 视为重复
    df = df.drop_duplicates(subset=["date", "amount", "merchant"], keep="first")

    # 标准化商户名: 去掉多余空格和特殊字符
    df["merchant"] = df["merchant"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

    # 去掉金额为 0 的记录
    df = df[df["amount"] > 0]

    # 确保字段类型
    df["source"] = df["source"].fillna("未知")
    df["transaction_type"] = df["transaction_type"].fillna("支出")
    df["description"] = df["description"].fillna("")

    # 按日期排序
    df = df.sort_values("date").reset_index(drop=True)

    return df


def merge_bills(wechat_df: pd.DataFrame, alipay_df: pd.DataFrame) -> pd.DataFrame:
    """
    合并微信和支付宝账单
    按日期排序，不是简单拼接——同一天的记录交错排列
    """
    merged = pd.concat([wechat_df, alipay_df], ignore_index=True)
    if merged.empty:
        return merged

    merged = merged.sort_values(["date", "source"]).reset_index(drop=True)
    return merged


def get_date_range(df: pd.DataFrame) -> tuple:
    """获取数据的日期范围"""
    if df.empty:
        return date.today(), date.today()
    return df["date"].min(), df["date"].max()


def get_summary_stats(df: pd.DataFrame) -> dict:
    """获取汇总统计"""
    if df.empty:
        return {
            "total_expense": 0,
            "total_income": 0,
            "transaction_count": 0,
            "avg_daily_expense": 0,
            "date_range": "无数据",
        }

    expense = df[df["transaction_type"] == "支出"]
    income = df[df["transaction_type"] == "收入"]

    date_min, date_max = get_date_range(df)
    days = max((date_max - date_min).days, 1)

    return {
        "total_expense": round(expense["amount"].sum(), 2),
        "total_income": round(income["amount"].sum(), 2),
        "transaction_count": len(df),
        "avg_daily_expense": round(expense["amount"].sum() / days, 2),
        "date_range": f"{date_min} ~ {date_max}",
        "date_min": date_min,
        "date_max": date_max,
    }
