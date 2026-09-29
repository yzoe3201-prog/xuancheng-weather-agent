"""
core_functions.py
功能：
  1. ask_database：自然语言 → SQL → 查询数据库
  2. analyze_and_explain：调用大模型总结 + 规则告警 + 图表
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import openai
from dotenv import load_dotenv

# ============ 加载环境变量 ============
load_dotenv()

# ============ 数据库连接 ============
engine = create_engine(
    "sqlite:///xuancheng_weather.db",
    connect_args={"check_same_thread": False}
)

# ============ 大模型配置 ============
API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
BASE_URL = "https://api.deepseek.com"

if not API_KEY:
    raise ValueError(
        "❌ 未检测到 DEEPSEEK_API_KEY，请检查项目根目录下的 .env 文件是否已正确配置。"
    )

client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ============ 数据库表结构说明（供大模型参考） ============
DB_SCHEMA_PROMPT = """
数据库表名为 daily_weather，字段为：
- date (文本，格式 YYYY-MM-DD)
- city (文本，默认 '宣城')
- avg_temp (数值，平均气温 ℃)
- max_temp (数值，最高气温 ℃)
- min_temp (数值，最低气温 ℃)
- rainfall (数值，降雨量 mm)
- wind_speed (数值，最大风速 km/h)
- humidity (数值，平均湿度 %)
"""


# ==================================================
# 核心1：自然语言转 SQL
# ==================================================
def ask_database(user_question):
    """把用户问题转换成 SQL，执行并返回 DataFrame 与 SQL 文本。"""
    system_prompt = f"""
你是一个气象数据分析专家。请将用户的自然语言问题转换为 SQLite 可执行的 SQL 语句。

{DB_SCHEMA_PROMPT}

特别注意：
1. 默认查询城市为 '宣城'，SQL 中可用 city = '宣城' 过滤。
2. "最近一周" 指 date >= date('now', '-7 days')。
3. 如果涉及趋势、对比、变化，默认按 date 升序排序。
4. 只返回纯 SQL 语句，不要包含 ```sql 标记、不要解释、不要多余文字。
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.1
        )
        sql_query = response.choices[0].message.content.strip()
        # 兜底清理：防止大模型偶尔加上 markdown 标记
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        with engine.connect() as conn:
            result_df = pd.read_sql_query(text(sql_query), conn)
        return result_df, sql_query
    except Exception as e:
        return pd.DataFrame(), f"生成错误: {e}"


# ==================================================
# 核心2：智能分析 + 告警 + 图表
# ==================================================
def analyze_and_explain(user_question, data_df):
    """返回 (结论文本, plotly 图表对象)。"""
    if data_df.empty:
        return "当前时间范围内未查询到气象数据，请尝试调整查询时间。", None

    # ---------- 1. 大模型总结 ----------
    prompt = f"""
用户的问题是：{user_question}

数据库查询到如下宣城气象数据：
{data_df.to_string(index=False)}

请用 80 字以内，给出一段简短的气象小结，并附上穿衣/出行建议。
要求：直接给结论，不要用标题，不要用 markdown 代码块。
"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        insights = response.choices[0].message.content.strip()
    except Exception as e:
        insights = f"（API 总结失败：{e}）基于数据判断，气温较为平稳。"

    # ---------- 2. 规则告警 ----------
    alert_msg = ""

    # 高温 / 低温预警
    if "avg_temp" in data_df.columns:
        try:
            max_temp = float(data_df["avg_temp"].max())
            if max_temp > 35:
                alert_msg += "🔥 **【高温预警】** 宣城近期出现极端高温，请注意防暑降温，减少户外活动！\n"
            elif max_temp < 0:
                alert_msg += "❄️ **【低温预警】** 宣城气温已降至冰点，路面可能结冰，出行注意交通安全！\n"
        except (TypeError, ValueError):
            pass

    # 降水提醒
    if "rainfall" in data_df.columns:
        try:
            total_rain = float(data_df["rainfall"].sum())
            if total_rain > 50:
                alert_msg += "🌧️ **【降水提醒】** 宣城近期累计降水较大，出门请带好雨具，防范局地内涝。\n"
        except (TypeError, ValueError):
            pass

    # 大风提醒
    if "wind_speed" in data_df.columns:
        try:
            max_wind = float(data_df["wind_speed"].max())
            if max_wind > 40:
                alert_msg += "💨 **【大风提醒】** 宣城近期出现大风天气，注意高空坠物，出行注意安全。\n"
        except (TypeError, ValueError):
            pass

    if alert_msg:
        insights = alert_msg + "\n" + insights

    # ---------- 3. 生成图表 ----------
    fig = None
    df_plot = data_df.copy()

    # 判断 X 轴
    if "date" in df_plot.columns:
        x_axis = "date"
    else:
        df_plot = df_plot.reset_index().rename(columns={"index": "数据点"})
        x_axis = "数据点"

    # 找出数值列
    numeric_cols = df_plot.select_dtypes(include=["number"]).columns.tolist()
    y_axis = numeric_cols[0] if numeric_cols else None

    if y_axis:
        if len(df_plot) > 1:
            fig = px.line(
                df_plot, x=x_axis, y=y_axis,
                title=f"宣城 {y_axis} 变化趋势",
                markers=True
            )
            fig.update_traces(
                line_color="#FF6B6B",
                line_width=3,
                hovertemplate=f"日期: %{{x}}<br>{y_axis}: %{{y:.1f}}"
            )
            fig.update_layout(
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20)
            )
        else:
            fig = px.bar(
                df_plot, x=x_axis, y=y_axis,
                title=f"宣城当前 {y_axis}"
            )

    return insights, fig