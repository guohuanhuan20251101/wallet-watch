"""
PDF 账单解析器 (支付宝/微信 PDF 账单)
使用 pdfplumber 提取表格数据

注意: PDF 格式多变，这是基础实现，需要根据实际账单格式调优
"""
import pandas as pd
import warnings

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def parse_alipay_pdf(filepath: str) -> pd.DataFrame:
    """
    解析支付宝 PDF 账单
    支付宝 PDF 账单通常包含表格形式的交易记录
    """
    if not HAS_PDFPLUMBER:
        raise ImportError("请安装 pdfplumber: pip install pdfplumber")

    all_rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and any(row):
                            # 过滤空行和表头行
                            row_text = " ".join([str(c) for c in row if c])
                            if "交易时间" in row_text or "交易创建时间" in row_text:
                                continue
                            all_rows.append(row)

    if not all_rows:
        return pd.DataFrame()

    # 尝试构建 DataFrame (假设格式: 交易时间, 交易对方, 商品, 金额, 收/支...)
    records = []
    for row in all_rows:
        # 找到日期列
        date_val = None
        amount_val = None
        merchant_val = ""
        direction = "支出"

        for cell in row:
            cell_str = str(cell).strip() if cell else ""
            if not cell_str:
                continue

            # 日期匹配
            if not date_val and ("-" in cell_str or "/" in cell_str):
                try:
                    date_val = pd.to_datetime(cell_str, errors="coerce")
                    if pd.isna(date_val):
                        date_val = None
                except Exception:
                    pass

            # 金额匹配
            if not amount_val:
                try:
                    cleaned = cell_str.replace("¥", "").replace(",", "").replace(" ", "")
                    amount_val = float(cleaned)
                except ValueError:
                    pass

            # 收支判断
            if "收入" in cell_str:
                direction = "收入"

            # 商户名
            if len(cell_str) > 2 and not any(k in cell_str for k in ["¥", "元", "收入", "支出"]):
                try:
                    float(cell_str.replace("¥", "").replace(",", ""))
                except ValueError:
                    if not merchant_val:
                        merchant_val = cell_str

        if date_val is not None and amount_val is not None:
            records.append({
                "date": date_val.date() if hasattr(date_val, 'date') else date_val,
                "amount": abs(amount_val),
                "merchant": merchant_val or "未知商户",
                "description": "",
                "source": "支付宝",
                "transaction_type": direction,
            })

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.sort_values("date").reset_index(drop=True)
    return result


def parse_wechat_pdf(filepath: str) -> pd.DataFrame:
    """解析微信 PDF 账单"""
    # 微信 PDF 账单格式类似，复用支付宝逻辑
    if not HAS_PDFPLUMBER:
        raise ImportError("请安装 pdfplumber: pip install pdfplumber")

    result = parse_alipay_pdf(filepath)
    if not result.empty:
        result["source"] = "微信"
    return result


def parse_pdf(filepath: str, source: str = "unknown") -> pd.DataFrame:
    """统一 PDF 入口"""
    if source == "支付宝":
        return parse_alipay_pdf(filepath)
    elif source == "微信":
        return parse_wechat_pdf(filepath)
    else:
        raise ValueError("请指定 source='微信' 或 source='支付宝'")
