"""
星型模型: 1 张事实表 + 3 张维度表
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "wallet_watch.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class DimDate(Base):
    """日期维度表"""
    __tablename__ = "dim_date"

    date_id = Column(Date, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    week_of_year = Column(Integer)
    day_of_week = Column(Integer)          # 0=周一 6=周日
    day_name = Column(String(10))           # Monday, Tuesday...
    month_name = Column(String(10))         # January, February...
    is_weekend = Column(Boolean, default=False)
    is_month_start = Column(Boolean, default=False)
    is_month_end = Column(Boolean, default=False)

    transactions = relationship("FactTransaction", back_populates="dim_date")


class DimCategory(Base):
    """消费类别维度表"""
    __tablename__ = "dim_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(20), unique=True, nullable=False)
    parent_category = Column(String(20))    # 必要支出 / 可选支出
    color = Column(String(7), default="#636EFA")  # 图表颜色

    transactions = relationship("FactTransaction", back_populates="dim_category")


class DimSource(Base):
    """支付来源维度表"""
    __tablename__ = "dim_source"

    source_id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(10), unique=True, nullable=False)

    transactions = relationship("FactTransaction", back_populates="dim_source")


class FactTransaction(Base):
    """交易事实表"""
    __tablename__ = "fact_transaction"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    date_id = Column(Date, ForeignKey("dim_date.date_id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("dim_category.category_id"), nullable=False)
    source_id = Column(Integer, ForeignKey("dim_source.source_id"), nullable=False)
    amount = Column(Float, nullable=False)
    merchant = Column(String(200))
    description = Column(Text)
    transaction_type = Column(String(10), default="支出")  # 支出 / 收入
    upload_batch = Column(String(50))      # 上传批次，溯源用
    created_at = Column(DateTime)

    dim_date = relationship("DimDate", back_populates="transactions")
    dim_category = relationship("DimCategory", back_populates="transactions")
    dim_source = relationship("DimSource", back_populates="transactions")


def get_session():
    return Session()
