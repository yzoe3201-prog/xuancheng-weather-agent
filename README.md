# xuancheng-weather-agent
An analysis based on Python &amp; Streamlit for Xuancheng meteorological data, including data cleaning, visualization and query analysis
# 宣城气象数据分析 Agent
> Xuancheng Meteorological Data Analysis Agent

## 📌 项目简介
本项目是基于Python、Streamlit搭建的气象数据分析智能Agent。
对宣城地区气象历史数据进行清洗、统计、可视化，支持自然语言提问，自动完成数据查询、图表生成与结果分析。

## 🛠️ 技术栈
- Python
- Streamlit：Web可视化页面
- Pandas：数据清洗与统计分析
- Matplotlib / Plotly：气象图表绘制
- LLM Agent：自然语言转SQL，实现数据问答

## ✨ 功能
1. 宣城气象原始数据导入、缺失值清洗
2. 气温、降水、湿度等多维度趋势可视化
3. 自然语言交互：输入问题，Agent自动分析气象数据并输出结论
4. 分析结果导出

## 📷 项目截图
> 这里后面上传你的运行截图

## ▶ 如何运行
```bash
pip install streamlit pandas plotly
streamlit run main.py

