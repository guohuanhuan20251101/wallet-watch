"""
微信账单解析器
支持微信导出的 CSV/Excel 格式
微信账单格式特点: 首行是标题, 后面是交易明细
"""
import re
import pandas as pd
from datetime import datetime


def parse_wechat_csv(filepath: str) -> pd.DataFrame:
    """
    解析微信账单 CSV

    微信账单 CSV 格式 (常见):
    ┌──────────────────────────────────────────────────────┐
    │ 微信支付账单                                          │
    │ 起始时间: 2024-01-01  终止时间: 2024-12-31             │
    │ 交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,... │
    └──────────────────────────────────────────────────────┘
    """
    # 先读原始文件，找到表头行
    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    header_idx = 0
    for i, line in enumerate(lines):
        if "交易时间" in line and "交易类型" in line:
            header_idx = i
            break

    df = pd.read_csv(
        filepath,
        skiprows=header_idx,
        encoding="utf-8-sig",
    )

    # 标准化列名
    col_map = {}
    for col in df.columns:
        col_stripped = col.strip()
        if "交易时间" in col_stripped:
            col_map[col] = "trade_time"
        elif "交易对方" in col_stripped or "商户" in col_stripped:
            col_map[col] = "merchant"
        elif "商品" in col_stripped or "交易说明" in col_stripped:
            col_map[col] = "product"
        elif "收/支" in col_stripped or "收支" in col_stripped:
            col_map[col] = "direction"
        elif "金额" in col_stripped:
            col_map[col] = "amount"
        elif "支付方式" in col_stripped:
            col_map[col] = "pay_method"
        elif "交易类型" in col_stripped:
            col_map[col] = "trade_type"
        elif "当前状态" in col_stripped:
            col_map[col] = "status"

    df = df.rename(columns=col_map)

    # 保留需要的列
    needed = ["trade_time", "merchant", "product", "direction", "amount", "trade_type"]
    df = df[[c for c in needed if c in df.columns]].copy()

    # 过滤掉汇总行
    if "trade_time" in df.columns:
        df = df[df["trade_time"].notna()]
        df = df[~df["trade_time"].astype(str).str.contains("共|笔|支出|收入|合计|总计")]

    # 解析时间
    df["trade_time"] = pd.to_datetime(df["trade_time"], errors="coerce")
    df = df.dropna(subset=["trade_time"])

    # 金额处理
    if "amount" in df.columns:
        df["amount"] = df["amount"].astype(str).str.replace("¥", "").str.replace("￥", "").str.replace(",", "")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # 方向处理
    if "direction" in df.columns:
        df["direction"] = df["direction"].str.strip()
        # 收入记正, 支出记正(后面展示时处理)
        df["amount"] = df["amount"].abs()

    df["source"] = "微信"

    # 统一输出列
    result = pd.DataFrame()
    result["date"] = df["trade_time"].dt.date
    result["amount"] = df["amount"].abs()
    result["merchant"] = df.get("merchant", df.get("product", "")).fillna("未知商户")
    result["description"] = df.get("product", df.get("merchant", "")).fillna("")
    result["source"] = "微信"
    result["transaction_type"] = df.get("direction", "支出").map(
        lambda x: "收入" if "收入" in str(x) else "支出"
    ).fillna("支出")

    result = result.dropna(subset=["date", "amount"])
    result = result.sort_values("date").reset_index(drop=True)

    return result


def parse_wechat(filepath: str) -> pd.DataFrame:
    """自动识别文件类型并解析"""
    if filepath.endswith(".csv"):
        return parse_wechat_csv(filepath)
    elif filepath.endswith((".xls", ".xlsx")):
        return parse_wechat_excel(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {filepath}")


def parse_wechat_excel(filepath: str) -> pd.DataFrame:
    """解析微信账单 Excel"""
    # Excel 格式类似 CSV, 但直接用 pandas 读取
    df = pd.read_excel(filepath, header=None)

    # 找表头行
    header_row = 0
    for i, row in df.iterrows():
        if row.astype(str).str.contains("交易时间").any():
            header_row = i
            break

    df.columns = df.iloc[header_row]
    df = df.iloc[header_row + 1:].reset_index(drop=True)

    # 列名映射 (同CSV)
    col_map = {}
    for col in df.columns:
        col_str = str(col).strip()
        if "交易时间" in col_str:
            col_map[col] = "trade_time"
        elif "交易对方" in col_str:
            col_map[col] = "merchant"
        elif "商品" in col_str:
            col_map[col] = "product"
        elif "收/支" in col_str or "收支" in col_str:
            col_map[col] = "direction"
        elif "金额" in col_str:
            col_map[col] = "amount"

    df = df.rename(columns=col_map)

    result = pd.DataFrame()
    if "trade_time" in df.columns:
        result["date"] = pd.to_datetime(df["trade_time"], errors="coerce").dt.date
    if "amount" in df.columns:
        result["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace("¥", "").str.replace(",", ""),
                                         errors="coerce").abs()
    result["merchant"] = df.get("merchant", df.get("product", "")).fillna("未知商户")
    result["description"] = df.get("product", df.get("merchant", "")).fillna("")
    result["source"] = "微信"
    result["transaction_type"] = df.get("direction", "支出").map(
        lambda x: "收入" if "收入" in str(x) else "支出"
    ).fillna("支出")

    result = result.dropna(subset=["date", "amount"])
    return result.sort_values("date").reset_index(drop=True)
