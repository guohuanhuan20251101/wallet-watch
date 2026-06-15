"""
自动分类引擎
基于关键字规则匹配，将交易自动归类
"""
import pandas as pd


# 关键字 → 类别 映射表
KEYWORD_RULES = {
    "餐饮": [
        "餐厅", "饭店", "酒店", "食堂", "外卖", "美团", "饿了么", "肯德基", "麦当劳",
        "星巴克", "奶茶", "咖啡", "烧烤", "火锅", "小吃", "快餐", "食品", "水果",
        "面包", "蛋糕", "甜品", "早餐", "午餐", "晚餐", "买菜", "超市",
        "海底捞", "喜茶", "奈雪", "瑞幸", "必胜客", "汉堡", "盒马",
        "叮咚", "朴朴", "每日优鲜", "菜市场", "熟食", "零食",
    ],
    "交通": [
        "滴滴", "地铁", "公交", "出租车", "高铁", "火车", "机票", "航班",
        "加油", "停车", "ETC", "高速", "充电", "骑行", "共享单车", "哈啰",
        "青桔", "曹操", "T3", "花小猪", "一嗨", "神州",
        "12306", "航旅", "携程", "去哪儿", "飞猪",
    ],
    "购物": [
        "淘宝", "天猫", "京东", "拼多多", "唯品会", "当当", "网易考拉",
        "得物", "闲鱼", "苏宁", "银泰", "商场", "服装", "数码", "电器",
        "小米", "华为", "苹果店", "优衣库", "ZARA", "Nike", "Adidas",
        "屈臣氏", "名创优品", "无印良品", "宜家", "代购", "海淘",
    ],
    "娱乐": [
        "电影", "KTV", "游戏", "充值", "抖音", "快手", "B站", "大会员",
        "直播", "打赏", "演出", "演唱会", "剧本杀", "密室", "旅游", "景点",
        "门票", "酒店", "民宿", "健身房", "运动", "游泳", "按摩",
        "王者荣耀", "原神", "网易云", "QQ音乐", "Spotify", "爱奇艺", "腾讯视频", "优酷",
    ],
    "居住": [
        "房租", "房贷", "物业", "水电", "燃气", "暖气", "网费", "宽带",
        "维修", "装修", "家具", "家电", "保洁", "搬家",
    ],
    "通讯": [
        "话费", "手机充值", "流量", "宽带费",
        "中国移动", "中国联通", "中国电信",
    ],
    "医疗": [
        "医院", "药房", "药店", "诊所", "体检", "挂号", "牙科",
        "医保", "买药", "门诊", "住院",
    ],
    "教育": [
        "课程", "培训", "学费", "教材", "考试", "报名费",
        "得到", "极客", "慕课", "知识付费",
    ],
    "人情": [
        "红包", "转账", "份子", "礼物", "请客", "AA",
        "孝敬", "给爸妈",
    ],
    "日用": [
        "洗衣", "理发", "美容", "美甲", "快递", "邮寄", "打印",
        "便利店", "杂货",
    ],
    "理财": [
        "基金", "股票", "理财", "保险", "转账", "提现",
        "利息", "分红", "余额宝", "零钱通",
    ],
}

# 收入关键字
INCOME_KEYWORDS = [
    "工资", "薪资", "奖金", "报销", "退款", "返现", "提成", "稿费",
    "房租收入", "利息收入", "分红",
]


def classify_merchant(merchant: str) -> str:
    """根据商户名自动分类"""
    if not merchant or not isinstance(merchant, str):
        return "其他"

    merchant_lower = merchant.lower()

    for category, keywords in KEYWORD_RULES.items():
        for kw in keywords:
            if kw.lower() in merchant_lower:
                return category

    return "其他"


def classify_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    对 DataFrame 中的所有交易自动分类

    规则优先级:
    1. 先看 transaction_type: 收入 → "收入"
    2. 再看商户名关键字匹配
    3. 都没命中 → "其他"
    """
    if df.empty:
        df["category"] = []
        return df

    df = df.copy()

    # 收入直接归为"收入"类
    income_mask = df["transaction_type"] == "收入"
    df.loc[income_mask, "category"] = "收入"

    # 支出按商户名分类
    expense_mask = ~income_mask
    df.loc[expense_mask, "category"] = df.loc[expense_mask, "merchant"].apply(classify_merchant)

    return df


def get_classification_stats(df: pd.DataFrame) -> dict:
    """获取分类统计：每个类别的总金额和占比"""
    if df.empty:
        return {}

    expense_df = df[df["transaction_type"] == "支出"]
    if expense_df.empty:
        return {}

    category_stats = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
    total = category_stats.sum()

    return {
        cat: {
            "amount": round(amt, 2),
            "percent": round(amt / total * 100, 1),
        }
        for cat, amt in category_stats.items()
    }
