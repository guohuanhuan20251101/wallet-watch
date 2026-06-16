"""
初始化数据库：建表 + 预置维度数据
"""
import os
from datetime import date, timedelta
from app.db.models import Base, engine, Session, DimDate, DimCategory, DimSource


def init_dim_date(start_year=2020, end_year=2030):
    """预填充日期维度表"""
    session = Session()
    if session.query(DimDate).count() > 0:
        session.close()
        return

    current = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    month_names = ["一月", "二月", "三月", "四月", "五月", "六月",
                   "七月", "八月", "九月", "十月", "十一月", "十二月"]

    while current <= end:
        d = DimDate(
            date_id=current,
            year=current.year,
            month=current.month,
            day=current.day,
            week_of_year=current.isocalendar()[1],
            day_of_week=current.weekday(),
            day_name=day_names[current.weekday()],
            month_name=month_names[current.month - 1],
            is_weekend=current.weekday() >= 5,
            is_month_start=(current.day == 1),
            is_month_end=(current.day == (date(current.year, current.month % 12 + 1, 1) - timedelta(days=1)).day
                          if current.month < 12
                          else current.day == 31),
        )
        session.add(d)
        current += timedelta(days=1)

    session.commit()
    session.close()
    print("✅ 日期维度表初始化完成")


def init_dim_category():
    """预置消费类别"""
    session = Session()
    if session.query(DimCategory).count() > 0:
        session.close()
        return

    categories = [
        ("餐饮", "可变支出", "#FF6B6B"),
        ("交通", "可变支出", "#4ECDC4"),
        ("购物", "可变支出", "#45B7D1"),
        ("娱乐", "可变支出", "#96CEB4"),
        ("居住", "固定支出", "#FFEAA7"),
        ("通讯", "固定支出", "#DDA0DD"),
        ("医疗", "可变支出", "#FF9FF3"),
        ("教育", "可变支出", "#54A0FF"),
        ("人情", "可变支出", "#5F27CD"),
        ("理财", "可变支出", "#01A3A4"),
        ("日用", "可变支出", "#F368E0"),
        ("其他", "可变支出", "#8395A7"),
        ("收入", "收入", "#2ED573"),
    ]
    for name, parent, color in categories:
        session.add(DimCategory(category_name=name, parent_category=parent, color=color))

    session.commit()
    session.close()
    print("✅ 类别维度表初始化完成")


def init_dim_source():
    """预置支付来源"""
    session = Session()
    if session.query(DimSource).count() > 0:
        session.close()
        return

    for name in ["微信", "支付宝"]:
        session.add(DimSource(source_name=name))

    session.commit()
    session.close()
    print("✅ 来源维度表初始化完成")


def _migrate_add_trade_time():
    """为旧版本数据库补充 trade_time 列"""
    import sqlite3
    db_path = engine.url.database
    if not db_path or not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(fact_transaction)")
        columns = [row[1] for row in cursor.fetchall()]
        if "trade_time" not in columns:
            conn.execute("ALTER TABLE fact_transaction ADD COLUMN trade_time VARCHAR(10)")
            conn.commit()
            print("✅ 数据库迁移：已添加 trade_time 列")
        conn.close()
    except Exception as e:
        print(f"⚠️ 迁移 trade_time 列失败（可忽略）: {e}")


def init_all():
    Base.metadata.create_all(engine)
    # 迁移：为旧数据库补充 trade_time 列
    _migrate_add_trade_time()
    init_dim_date()
    init_dim_category()
    init_dim_source()
    print("🎉 数据库初始化完成！")


if __name__ == "__main__":
    init_all()
