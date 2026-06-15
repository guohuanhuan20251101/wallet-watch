"""
基础测试
"""
import pytest
import pandas as pd
from app.transform.cleaner import clean_transactions, merge_bills
from app.transform.categorizer import classify_transactions


def test_clean_transactions():
    df = pd.DataFrame({
        "date": ["2024-01-15", "2024-01-15", "2024-01-16"],
        "amount": [35.5, 35.5, -10],
        "merchant": ["麦当劳", "麦当劳", ""],
        "source": ["微信", "微信", "支付宝"],
        "transaction_type": ["支出", "支出", "支出"],
        "description": ["", "", ""],
    })
    result = clean_transactions(df)
    # 重复的麦当劳记录应该被去重
    assert len(result) == 2
    # 金额都是正的
    assert (result["amount"] >= 0).all()


def test_classify_transactions():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-15", "2024-01-15", "2024-01-15"]),
        "amount": [35.0, 15.0, 5000.0],
        "merchant": ["麦当劳", "滴滴出行", "工资"],
        "source": ["微信", "微信", "支付宝"],
        "transaction_type": ["支出", "支出", "收入"],
        "description": ["", "", ""],
    })
    result = classify_transactions(df)
    categories = result["category"].tolist()
    assert "餐饮" in categories
    assert "交通" in categories
    assert "收入" in categories


def test_merge_bills():
    wx = pd.DataFrame({
        "date": ["2024-01-15", "2024-01-16"],
        "amount": [35.0, 20.0],
        "merchant": ["麦当劳", "公交"],
        "source": ["微信", "微信"],
        "transaction_type": ["支出", "支出"],
        "description": ["", ""],
    })
    ali = pd.DataFrame({
        "date": ["2024-01-15", "2024-01-17"],
        "amount": [120.0, 50.0],
        "merchant": ["超市", "奶茶"],
        "source": ["支付宝", "支付宝"],
        "transaction_type": ["支出", "支出"],
        "description": ["", ""],
    })
    merged = merge_bills(wx, ali)
    # 同一天（2024-01-15）的记录应该排在一起，然后按 source 排序
    assert len(merged) == 4
    # 同一天的两条记录相邻
    dates = merged["date"].tolist()
    assert dates[0] == "2024-01-15"
    assert dates[1] == "2024-01-15"
    assert dates[2] == "2024-01-16"
    assert dates[3] == "2024-01-17"
    # 同一天两条记录，微信和支付宝都有
    day1_sources = set(merged.iloc[:2]["source"])
    assert "微信" in day1_sources and "支付宝" in day1_sources
