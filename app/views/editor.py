"""
可编辑交易表格 + 批量修改组件
"""
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from app.db.models import get_session, FactTransaction, DimCategory, DimSource


def get_all_categories() -> list[str]:
    """获取所有类别名称列表"""
    session = get_session()
    try:
        return sorted([c.category_name for c in session.query(DimCategory).all()])
    finally:
        session.close()


def _render_aggrid(df: pd.DataFrame, key: str, suppress_resize: bool = False):
    """用 AgGrid 渲染表格（中文菜单、筛选、表格撑满容器宽度）"""
    gb = GridOptionsBuilder.from_dataframe(df)
    # 所有列禁止移动位置（防止列边框被拖走导致右边界漂移）
    gb.configure_default_column(
        sortable=True,
        filter=True,
        suppressMovable=True,
        resizable=True,  # 默认允许拖拽修改列宽
    )
    
    # 针对不同列设置合理的 minWidth，确保数据文字完全可见、不会被遮挡
    for col in df.columns:
        col_str = str(col)
        if "排名" in col_str:
            gb.configure_column(col_str, minWidth=60)
        elif "商家" in col_str or "商户" in col_str or "merchant" in col_str:
            gb.configure_column(col_str, minWidth=150)
        elif "金额" in col_str or "总支出" in col_str or "总收入" in col_str or "结余" in col_str or "日均" in col_str or "环比" in col_str:
            gb.configure_column(col_str, minWidth=100, filter="agNumberColumnFilter")
        elif "次数" in col_str or "笔数" in col_str:
            gb.configure_column(col_str, minWidth=80, filter="agNumberColumnFilter")
        elif "日期" in col_str or "月份" in col_str:
            gb.configure_column(col_str, minWidth=110)
        else:
            gb.configure_column(col_str, minWidth=100)

    # 中文筛选菜单 + 表格自适应容器高度
    gb.configure_grid_options(
        localeText=_aggrid_zh_locale(),
        domLayout="autoHeight",
    )
    grid_options = gb.build()
    
    # ── 完美复刻 Excel 拖拽逻辑 ──
    # 1. 严格锁死整体表格宽度，禁止出现横向滚动条，禁止整体表格溢出外层容器
    grid_options["suppressHorizontalScroll"] = True

    if suppress_resize:
        # 当禁止拖动列宽时，配置每一列使用 flex 弹性拉伸填充容器
        for col_def in grid_options.get("columnDefs", []):
            if isinstance(col_def, dict):
                col_def["flex"] = 1
                col_def["resizable"] = False
    else:
        cols = grid_options.get("columnDefs", [])
        if cols and len(cols) > 0:
            # 2. 最后一列右边界（最右侧）彻底禁用拖拽，固定在容器最右端
            last_col = cols[-1]
            if isinstance(last_col, dict):
                last_col["resizable"] = False
            
            # 3. 启用每一列的 flex 属性。
            # 为了确保初始加载和任何时刻都完美占满 100% 容器，我们需要强制所有的列都拥有 flex。
            # 但 AgGrid 原生的 `fit_columns_on_grid_load` 如果和 `flex` 混用，有时会在计算初始列宽时冲突导致没有完全占满。
            # 因此，我们不仅为每列配置 flex，还要在渲染配置里保证启用自动调整。
            for col_def in cols:
                if isinstance(col_def, dict):
                    col_def["flex"] = 1

    AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        height=None,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        theme="streamlit",  # 显式使用 streamlit 样式，防止主题默认 padding 留白
        key=key,
    )


def _aggrid_zh_locale() -> dict:
    """AgGrid 筛选/排序菜单的中文翻译"""
    return {
        # 列头菜单
        "pinColumn": "固定列",
        "pinLeft": "固定到左侧",
        "pinRight": "固定到右侧",
        "unpin": "取消固定",
        "valueAggregation": "数值聚合",
        "autosizeThiscolumn": "自动调整此列宽度",
        "autosizeAllColumns": "自动调整所有列宽度",
        "groupBy": "分组",
        "ungroupBy": "取消分组",
        "resetColumns": "重置列",
        "expandAll": "展开所有",
        "collapseAll": "折叠所有",
        "copy": "复制",
        "ctrlC": "Ctrl+C",
        "copyWithGroupHeaders": "复制（含组标题）",
        "copyWithHeaders": "复制（含列头）",
        "paste": "粘贴",
        # 排序
        "sortAscending": "升序排序",
        "sortDescending": "降序排序",
        "sortUnSort": "取消排序",
        # 筛选
        "filter": "筛选",
        "filters": "筛选",
        "applyFilter": "应用筛选",
        "resetFilter": "重置筛选",
        "clearFilter": "清除筛选",
        "andCondition": "并且",
        "orCondition": "或者",
        "contains": "包含",
        "notContains": "不包含",
        "equals": "等于",
        "notEqual": "不等于",
        "startsWith": "开始于",
        "endsWith": "结束于",
        "lessThan": "小于",
        "greaterThan": "大于",
        "lessThanOrEqual": "小于或等于",
        "greaterThanOrEqual": "大于或等于",
        "inRange": "在范围内",
        "inRangeStart": "从",
        "inRangeEnd": "到",
        "blank": "空白",
        "notBlank": "非空白",
        # 筛选按钮
        "apply": "应用",
        "reset": "重置",
        "clear": "清除",
        # 日期筛选
        "dateFormatOoo": "yyyy-mm-dd",
        # 选择筛选
        "selectAll": "选择全部",
        "selectAllSearchResults": "选择搜索结果",
        "addCurrentSelectionToFilter": "将当前选择加入筛选",
        # 搜索框
        "searchOoo": "搜索...",
        "noMatches": "无匹配结果",
        # 数字筛选
        "equalsTo": "等于",
        "notEqualsTo": "不等于",
        "lessThanTo": "小于",
        "greaterThanTo": "大于",
        # 通用
        "noRowsToShow": "暂无数据",
        "enabled": "启用",
    }


def render_editable_table(
    df: pd.DataFrame,
    key_prefix: str,
    title: str = "交易记录",
    max_rows: int = 50,
    show_source: bool = True,
    show_time: bool = False,
):
    """
    可编辑的交易表格组件
    - 显示模式：AgGrid（中文菜单，列头点击排序/筛选/固定列）
    - 编辑模式：st.data_editor，可直接在表内修改类别和类型
    - 退出编辑时如有未保存修改，弹出确认提示
    """
    if df.empty:
        st.info("暂无数据")
        return

    all_cats = get_all_categories()

    # ── 标题行 + 编辑按钮 ──
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.markdown(f'<p class="section-title">{title}</p>', unsafe_allow_html=True)

    edit_key = f"{key_prefix}_edit_mode"
    unsaved_key = f"{key_prefix}_unsaved"

    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    # ── 处理退出确认 ──
    from_editor_key = f"{key_prefix}_editor"
    if st.session_state.get(unsaved_key):
        st.warning("⚠️ 表格中有未保存的修改，确定要放弃吗？")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ 放弃修改", key=f"{key_prefix}_discard"):
                st.session_state[edit_key] = False
                st.session_state[unsaved_key] = False
                st.rerun()
        with c2:
            if st.button("📝 继续编辑", key=f"{key_prefix}_keep"):
                st.session_state[unsaved_key] = False
                st.rerun()

    # ── 退出编辑时检测未保存修改 ──
    with col_btn:
        if st.session_state[edit_key]:
            if st.button("🔒 退出编辑", key=f"{key_prefix}_exit", use_container_width=True):
                if from_editor_key in st.session_state:
                    edited = st.session_state[from_editor_key]
                    editor_df = _build_editor_df(df.head(max_rows), show_source, show_time)
                    if _has_changes(editor_df, edited):
                        st.session_state[unsaved_key] = True
                        st.rerun()
                st.session_state[edit_key] = False
                st.rerun()
        else:
            if st.button("✏️ 编辑", key=f"{key_prefix}_enter", use_container_width=True):
                st.session_state[edit_key] = True
                st.session_state[unsaved_key] = False
                st.rerun()

    # ── 限制显示行数 ──
    display_df = df.head(max_rows).copy()

    if not st.session_state[edit_key]:
        # ── 显示模式：AgGrid（中文列头菜单，支持排序/筛选/固定列）──
        show_cols = ["date", "merchant", "category", "amount"]
        col_names = {"date": "日期", "merchant": "商户", "category": "类别", "amount": "金额"}
        if show_time and "trade_time" in display_df.columns:
            show_cols.insert(1, "trade_time")
            col_names["trade_time"] = "时间"
        if show_source:
            show_cols.append("source")
            col_names["source"] = "来源"
        show_cols.append("transaction_type")
        col_names["transaction_type"] = "收支"

        view_df = display_df[show_cols].rename(columns=col_names).reset_index(drop=True)
        # AgGrid 要求日期和时间为字符串，否则显示 [object Object]
        view_df["日期"] = view_df["日期"].astype(str)
        if "时间" in view_df.columns:
            view_df["时间"] = view_df["时间"].fillna("").astype(str)
        view_df["金额"] = view_df["金额"].round(2)
        _render_aggrid(view_df, key=f"{key_prefix}_aggrid")

    else:
        # ── 编辑模式：st.data_editor（下拉框编辑体验更好）──
        editor_df = _build_editor_df(display_df, show_source, show_time)
        editor_df["_tid"] = display_df["transaction_id"].values

        edited = st.data_editor(
            editor_df,
            column_config={
                "日期": st.column_config.TextColumn(disabled=True),
                "时间": st.column_config.TextColumn(disabled=True),
                "商户": st.column_config.TextColumn(disabled=True),
                "金额": st.column_config.NumberColumn(disabled=True, format="¥%.2f"),
                "来源": st.column_config.TextColumn(disabled=True),
                "类别": st.column_config.SelectboxColumn(
                    options=all_cats,
                    required=True,
                ),
                "收支": st.column_config.SelectboxColumn(
                    options=["支出", "收入"],
                    required=True,
                ),
                "_tid": None,
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key=from_editor_key,
        )

        st.session_state[from_editor_key] = edited

        if st.button("💾 保存修改", key=f"{key_prefix}_save", type="primary"):
            changed = 0
            for idx in range(len(editor_df)):
                if idx >= len(edited):
                    break
                orig = editor_df.iloc[idx]
                curr = edited.iloc[idx]
                if curr["类别"] != orig["类别"] or curr["收支"] != orig["收支"]:
                    changed += 1

            if changed > 0:
                # ── 确认弹窗 ──
                confirm_key = f"{key_prefix}_save_confirm"
                if not st.session_state.get(confirm_key):
                    st.session_state[confirm_key] = True
                    st.warning(f"⚠️ 即将修改 **{changed}** 条记录，确认保存吗？")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 确认保存", key=f"{key_prefix}_confirm_yes"):
                            for idx in range(len(editor_df)):
                                if idx >= len(edited):
                                    break
                                orig = editor_df.iloc[idx]
                                curr = edited.iloc[idx]
                                if curr["类别"] != orig["类别"] or curr["收支"] != orig["收支"]:
                                    tid = int(orig["_tid"])
                                    _update_transaction(tid, curr["类别"], curr["收支"])
                            st.cache_data.clear()
                            st.session_state[confirm_key] = False
                            st.session_state[edit_key] = False
                            st.session_state[unsaved_key] = False
                            st.session_state.pop(from_editor_key, None)
                            st.success(f"✅ 已保存 {changed} 条修改")
                            st.rerun()
                    with c2:
                        if st.button("❌ 取消", key=f"{key_prefix}_confirm_no"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                else:
                    # 二次渲染（rerun 后 confirm_key=True），直接走确认流程
                    for idx in range(len(editor_df)):
                        if idx >= len(edited):
                            break
                        orig = editor_df.iloc[idx]
                        curr = edited.iloc[idx]
                        if curr["类别"] != orig["类别"] or curr["收支"] != orig["收支"]:
                            tid = int(orig["_tid"])
                            _update_transaction(tid, curr["类别"], curr["收支"])
                    st.cache_data.clear()
                    st.session_state[confirm_key] = False
                    st.session_state[edit_key] = False
                    st.session_state[unsaved_key] = False
                    st.session_state.pop(from_editor_key, None)
                    st.success(f"✅ 已保存 {changed} 条修改")
                    st.rerun()
            else:
                st.info("没有检测到修改")


def _build_editor_df(display_df: pd.DataFrame, show_source: bool, show_time: bool) -> pd.DataFrame:
    """构建编辑器 DataFrame，统一列名和顺序"""
    base_cols = ["date", "merchant", "amount"]
    col_rename = {"date": "日期", "merchant": "商户", "amount": "金额"}

    if show_time and "trade_time" in display_df.columns:
        base_cols.insert(1, "trade_time")
        col_rename["trade_time"] = "时间"

    if show_source:
        base_cols.append("source")
        col_rename["source"] = "来源"

    base_cols.extend(["category", "transaction_type"])
    col_rename["category"] = "类别"
    col_rename["transaction_type"] = "收支"

    editor_df = display_df[base_cols].copy()
    editor_df.rename(columns=col_rename, inplace=True)
    editor_df.reset_index(drop=True, inplace=True)
    return editor_df


def _has_changes(editor_df: pd.DataFrame, edited: pd.DataFrame) -> bool:
    """检测编辑后的 DataFrame 是否有修改"""
    if len(editor_df) != len(edited):
        return True
    for idx in range(len(editor_df)):
        orig = editor_df.iloc[idx]
        curr = edited.iloc[idx]
        if curr.get("类别") != orig.get("类别") or curr.get("收支") != orig.get("收支"):
            return True
    return False


def render_bulk_editor(df: pd.DataFrame):
    """
    批量修改组件：按条件筛选，一次性修改一大类记录
    """
    if df.empty:
        return

    st.markdown('<p class="section-title">📦 批量修改分类</p>', unsafe_allow_html=True)
    st.caption("适用于：想一次性改一大类订单（比如京东全部从「购物」改为「美食」）")

    all_cats = get_all_categories()

    col1, col2, col3 = st.columns(3)
    with col1:
        sources = ["全部"] + sorted(df["source"].unique().tolist())
        filter_source = st.selectbox("筛选来源", sources, key="bulk_source")
    with col2:
        cats = ["全部"] + all_cats
        filter_cat = st.selectbox("当前类别", cats, key="bulk_old_cat")
    with col3:
        keyword = st.text_input("🔍 商户关键字（可选）", key="bulk_keyword",
                                placeholder="例如：京东")

    # ── 应用筛选 ──
    matched = df.copy()
    if filter_source != "全部":
        matched = matched[matched["source"] == filter_source]
    if filter_cat != "全部":
        matched = matched[matched["category"] == filter_cat]
    if keyword.strip():
        matched = matched[matched["merchant"].astype(str).str.contains(
            keyword.strip(), case=False, na=False
        )]

    st.caption(f"匹配 **{len(matched)}** 条记录（共 {len(df)} 条）")

    if matched.empty:
        st.warning("没有匹配的记录")
        return

    # ── 预览匹配结果 ──
    with st.expander(f"📋 预览匹配的 {min(len(matched), 20)} 条记录", expanded=(len(matched) <= 10)):
        preview_cols = ["date", "merchant", "category", "amount", "source"]
        col_rename = {"date": "日期", "merchant": "商户", "category": "类别", "amount": "金额", "source": "来源"}
        if "trade_time" in matched.columns:
            preview_cols.insert(1, "trade_time")
            col_rename["trade_time"] = "时间"
        preview = matched[preview_cols].head(20).rename(columns=col_rename)
        preview["日期"] = preview["日期"].astype(str)
        _render_aggrid(preview, key="bulk_preview_aggrid")

    # ── 设置目标值 ──
    col_a, col_b = st.columns(2)
    with col_a:
        new_cat = st.selectbox("改为类别", all_cats, key="bulk_new_cat")
    with col_b:
        new_type = st.selectbox("改为类型", ["不修改", "支出", "收入"], key="bulk_new_type")

    if st.button("🚀 批量修改", type="primary", use_container_width=True, key="bulk_apply"):
        # ── 确认弹窗 ──
        confirm_key = "bulk_apply_confirm"
        if not st.session_state.get(confirm_key):
            st.session_state[confirm_key] = True
            type_label = f"类型→{new_type}" if new_type != "不修改" else "类型不变"
            st.warning(f"⚠️ 即将修改 **{len(matched)}** 条记录（类别→{new_cat}，{type_label}），确认吗？")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认批量修改", key="bulk_confirm_yes"):
                    changed = 0
                    for _, row in matched.iterrows():
                        tid = int(row["transaction_id"])
                        type_to_set = row["transaction_type"] if new_type == "不修改" else new_type
                        _update_transaction(tid, new_cat, type_to_set)
                        changed += 1
                    st.cache_data.clear()
                    st.session_state[confirm_key] = False
                    st.success(f"✅ 已批量修改 {changed} 条记录")
                    st.rerun()
            with c2:
                if st.button("❌ 取消", key="bulk_confirm_no"):
                    st.session_state[confirm_key] = False
                    st.rerun()


def _update_transaction(transaction_id: int, new_category: str, new_type: str):
    """更新单条交易的分类和类型"""
    session = get_session()
    try:
        cat = session.query(DimCategory).filter_by(category_name=new_category).first()
        txn = session.query(FactTransaction).filter_by(transaction_id=transaction_id).first()
        if txn and cat:
            txn.category_id = cat.category_id
            txn.transaction_type = new_type
            session.commit()
    finally:
        session.close()
