"""
支付宝账单解析器
支持支付宝导出的 CSV / Excel 格式
"""
import pandas as pd


def parse_alipay_csv(filepath: str) -> pd.DataFrame:
    """
    解析支付宝账单 CSV

    支付宝账单 CSV 常见格式:
    ┌──────────────────────────────────────────────────────────────────┐
    │ 支付宝交易记录                                                    │
    │ 交易号,商家订单号,交易创建时间,付款时间,最近修改时间,              │
    │ 交易对方,商品名称,金额（元）,收/支,交易状态,服务费（元）,...        │
    └──────────────────────────────────────────────────────────────────┘
    """
    # 找表头行
    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    header_idx = 0
    for i, line in enumerate(lines):
        if ("交易创建时间" in line or "交易时间" in line) and ("金额" in line):
            header_idx = i
            break

    df = pd.read_csv(filepath, skiprows=header_idx, encoding="utf-8-sig")

    # 标准化列名
    col_map = {}
    for col in df.columns:
        col_str = str(col).strip()
        if "交易创建时间" in col_str:
            col_map[col] = "trade_time"
        elif "交易时间" in col_str:
            col_map[col] = "trade_time"
        elif "交易对方" in col_str or "对方" in col_str:
            col_map[col] = "merchant"
        elif "商品名称" in col_str or "商品说明" in col_str:
            col_map[col] = "product"
        elif "收/支" in col_str or "收支" in col_str:
            col_map[col] = "direction"
        elif "金额" in col_str:
            col_map[col] = "amount"
        elif "交易状态" in col_str:
            col_map[col] = "status"

    df = df.rename(columns=col_map)

    # 过滤：只保留成功的交易
    if "status" in df.columns:
        df = df[df["status"].astype(str).str.contains("成功|交易成功")]

    # 过滤汇总行
    if "trade_time" in df.columns:
        df = df[df["trade_time"].notna()]
        df = df[~df["trade_time"].astype(str).str.contains("共|笔|合计|总计")]

    # 解析时间 (支付宝格式: 2024-01-15 12:30:45)
    if "trade_time" in df.columns:
        df["trade_time"] = pd.to_datetime(df["trade_time"], errors="coerce")
        df = df.dropna(subset=["trade_time"])

    # 金额处理
    if "amount" in df.columns:
        df["amount"] = df["amount"].astype(str).str.replace("¥", "").str.replace(",", "").str.strip()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # 方向处理
    if "direction" in df.columns:
        df["direction"] = df["direction"].str.strip()

    # 统一输出列
    result = pd.DataFrame()
    result["date"] = df["trade_time"].dt.date
    result["trade_time"] = df["trade_time"].apply(
        lambda t: t.strftime("%H:%M:%S") if pd.notna(t) and hasattr(t, 'strftime') else ""
    )
    result["amount"] = df["amount"].abs()
    result["merchant"] = df.get("merchant", "").fillna("未知商户")
    result["description"] = df.get("product", "").fillna("")
    result["source"] = "支付宝"

    direction_col = df.get("direction", pd.Series(["支出"] * len(df)))
    result["transaction_type"] = direction_col.apply(
        lambda x: "收入" if "收入" in str(x) and "支出" not in str(x) else "支出"
    )

    result = result.dropna(subset=["date", "amount"])
    result = result.sort_values("date").reset_index(drop=True)

    return result


def parse_alipay_excel(filepath: str) -> pd.DataFrame:
    """解析支付宝账单 Excel"""
    df = pd.read_excel(filepath, header=None)

    header_row = 0
    for i, row in df.iterrows():
        if row.astype(str).str.contains("交易创建时间|交易时间").any():
            header_row = i
            break

    df.columns = df.iloc[header_row]
    df = df.iloc[header_row + 1:].reset_index(drop=True)

    # 列名标准化
    col_map = {}
    for col in df.columns:
        col_str = str(col).strip()
        if "交易创建时间" in col_str or "交易时间" in col_str:
            col_map[col] = "trade_time"
        elif "交易对方" in col_str:
            col_map[col] = "merchant"
        elif "商品名称" in col_str or "商品说明" in col_str:
            col_map[col] = "product"
        elif "收/支" in col_str:
            col_map[col] = "direction"
        elif "金额" in col_str:
            col_map[col] = "amount"

    df = df.rename(columns=col_map)

    result = pd.DataFrame()
    if "trade_time" in df.columns:
        trade_dt = pd.to_datetime(df["trade_time"], errors="coerce")
        result["date"] = trade_dt.dt.date
        result["trade_time"] = trade_dt.apply(
            lambda t: t.strftime("%H:%M:%S") if pd.notna(t) and hasattr(t, 'strftime') else ""
        )
    if "amount" in df.columns:
        result["amount"] = pd.to_numeric(
            df["amount"].astype(str).str.replace("¥", "").str.replace(",", "").str.strip(),
            errors="coerce"
        ).abs()
    result["merchant"] = df.get("merchant", "").fillna("未知商户")
    result["description"] = df.get("product", "").fillna("")
    result["source"] = "支付宝"
    result["transaction_type"] = df.get("direction", "支出").apply(
        lambda x: "收入" if "收入" in str(x) else "支出"
    )

    result = result.dropna(subset=["date", "amount"])
    return result.sort_values("date").reset_index(drop=True)


def parse_alipay(filepath: str) -> pd.DataFrame:
    """自动识别文件类型并解析"""
    if filepath.endswith(".csv"):
        return parse_alipay_csv(filepath)
    elif filepath.endswith((".xls", ".xlsx")):
        return parse_alipay_excel(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {filepath}")
