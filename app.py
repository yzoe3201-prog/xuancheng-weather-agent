"""
app.py
功能：Streamlit 前端，支持快捷操作 + 历史记录 + 图表展示。
"""

import streamlit as st
from core_functions import ask_database, analyze_and_explain

# ============ 页面配置 ============
st.set_page_config(
    page_title="宣城气象智能分析 Agent",
    layout="wide",
    page_icon="🌤️"
)

st.title("🌤️ 宣城日常气象智能分析 Agent")
st.write("📍 合肥工业大学宣城校区 人工智能实训项目")
st.caption("💡 支持自然语言提问，自动生成智能分析与交互式图表。")

# ============ 历史记录初始化 ============
if "history" not in st.session_state:
    st.session_state.history = []
if "query" not in st.session_state:
    st.session_state.query = ""

# ============ 侧边栏 ============
with st.sidebar:
    st.header("📊 快捷操作")

    if st.button("宣城最近7天气温趋势"):
        st.session_state.query = "查询宣城最近7天的平均气温"
    if st.button("宣城降雨量分析"):
        st.session_state.query = "查询宣城最近7天的降雨量"
    if st.button("宣城今日天气简报"):
        st.session_state.query = "查询宣城最近3天的气温和湿度"
    if st.button("宣城风速变化"):
        st.session_state.query = "查询宣城最近7天的风速"

    st.divider()

    st.header("📝 历史查询记录")
    if not st.session_state.history:
        st.write("暂无历史记录，快去提问吧！")
    else:
        for i, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"🕐 查询 {len(st.session_state.history) - i}"):
                st.write(f"**问题**：{item['question']}")
                st.info(f"**结论**：{item['insights']}")

# ============ 主界面输入 ============
user_query = st.text_input(
    "✍️ 输入您的气象分析问题：",
    value=st.session_state.query,
    placeholder="例如：查询宣城最近7天的平均气温"
)

if st.button("🚀 智能生成报告", type="primary"):
    if not user_query.strip():
        st.warning("请输入有效的问题！")
    else:
        # 1. 生成 SQL 并查询
        with st.spinner("🧠 引擎正在调用大模型生成 SQL 并查询数据..."):
            result_df, sql = ask_database(user_query)

        with st.expander("🧠 查看系统生成的 SQL 语句"):
            st.code(sql, language="sql")

        # 2. 判断结果
        if not result_df.empty:
            with st.spinner("📊 正在分析数据并绘制图表..."):
                insights, fig = analyze_and_explain(user_query, result_df)

                # 存入历史
                st.session_state.history.append({
                    "question": user_query,
                    "insights": insights
                })

                # 展示结论
                st.subheader("📝 智能分析结论")
                st.markdown(insights)

                # 分列展示图表和数据
                col1, col2 = st.columns([3, 1.5])
                with col1:
                    st.subheader("📈 可视化报告")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("数据量不足以生成图表，请查看右侧明细数据。")
                with col2:
                    st.subheader("📋 详细数据明细")
                    st.dataframe(result_df, use_container_width=True, height=400)
        else:
            st.error("❌ 查询无结果。可能是数据库暂无该时段数据，或 SQL 逻辑异常，请调整提问方式。")

st.markdown("---")
st.caption("Powered by Python · Pandas · Streamlit · DeepSeek LLM · Open-Meteo")