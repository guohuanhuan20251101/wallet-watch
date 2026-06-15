# 💸 Wallet Watch — 个人财务分析工具

多源账单导入 · 自动分类 · 多维可视化

## 功能

- 📤 **双平台支持**：微信 + 支付宝账单导入（CSV / Excel / PDF）
- 🧠 **自动分类**：基于关键字规则自动给每笔消费归类（餐饮/交通/购物/娱乐...）
- 💾 **持续积累**：所有交易存入本地 SQLite，上传不删就永久保存
- 🔀 **双源合并**：微信+支付宝按日合并，不是简单拼接
- 📊 **多维度可视化**：
  - 日视图：每日柱状图 + 累计折线 + 分类堆叠
  - 月视图：月度收支趋势 + 环比变化
  - 年视图：热力图 + 年度对比
- 🏷️ **分类纠错**：手动修正自动分类结果

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
make init

# 3. 启动
make run
# 或: streamlit run main.py

# 4. 打开浏览器 http://localhost:8501
```

## 使用方式

1. 打开微信/支付宝 → 账单 → 导出账单（CSV 格式）
2. 在 Wallet Watch 侧边栏上传文件
3. 预览解析结果，确认后点击「导入」
4. 切换日/月/年视图查看分析

## 技术栈

| 层 | 技术 |
|---|---|
| 数据接入 | pandas (CSV/Excel) + pdfplumber (PDF) |
| 存储 | SQLite + SQLAlchemy |
| 数据建模 | 星型模型: dim_date / dim_category / dim_source / fact_transaction |
| ETL | Python 多源解析 + 清洗 + 自动分类 |
| 可视化 | Streamlit + Plotly |
| 测试 | pytest |

## 项目结构

```
wallet-watch/
├── main.py                      # Streamlit 入口
├── app/
│   ├── db/
│   │   ├── models.py            # SQLAlchemy 星型模型
│   │   └── init_db.py           # 建表 + 维度初始化
│   ├── etl/
│   │   ├── parser_wechat.py     # 微信账单解析
│   │   ├── parser_alipay.py     # 支付宝账单解析
│   │   └── parser_pdf.py        # PDF 账单解析
│   ├── transform/
│   │   ├── cleaner.py           # 数据清洗
│   │   └── categorizer.py       # 自动分类引擎
│   ├── views/
│   │   ├── dashboard.py         # 总览页
│   │   ├── daily.py             # 日视图
│   │   ├── monthly.py           # 月视图
│   │   └── yearly.py            # 年视图
│   └── utils/
│       └── charts.py            # Plotly 图表
├── tests/
│   └── test_basic.py
├── requirements.txt
├── Makefile
└── README.md
```

## 待完善

- [ ] PDF 账单解析增强（适配更多格式）
- [ ] 分类规则可自定义
- [ ] 预算设置 + 超支预警
- [ ] 导出报表 (PDF/HTML)
- [ ] 多人账单模式
- [ ] Docker 部署支持
