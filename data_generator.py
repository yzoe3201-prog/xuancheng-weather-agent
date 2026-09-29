"""
data_generator.py
功能：从 Open-Meteo 获取宣城真实气象数据，并写入 SQLite 数据库。
特点：
  1. 历史数据（近30天）：来自 Open-Meteo Archive API（ERA5 再分析数据，2-3天延迟）
  2. 近期数据（近3天）：来自 Open-Meteo Forecast API（past_days 参数）
  3. 两段数据合并后写入数据库，保证"今日天气简报"可查到数据。
"""

import pandas as pd
import requests
from sqlalchemy import create_engine
import datetime
import sys

# ============ 配置区 ============
LATITUDE = 30.95          # 宣城纬度
LONGITUDE = 118.76        # 宣城经度
TIMEZONE = "Asia/Shanghai"
DB_PATH = "sqlite:///xuancheng_weather.db"

# ============ 工具函数 ============

def fetch_archive_data(start_date, end_date):
    """调用 Open-Meteo 历史数据 API，返回 DataFrame。"""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
            "relative_humidity_2m_mean"
        ],
        "timezone": TIMEZONE
    }
    print(f"📡 正在请求历史数据：{start_date} ~ {end_date}")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return _parse_daily(data)


def fetch_forecast_past_data(past_days=3):
    """调用 Open-Meteo 预报 API 的 past_days 参数，获取最近几天的实际数据。"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
            "relative_humidity_2m_mean"
        ],
        "past_days": past_days,
        "forecast_days": 0,      # 不要未来预报，只要过去的实际值
        "timezone": TIMEZONE
    }
    print(f"📡 正在请求最近 {past_days} 天数据（Forecast API）")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return _parse_daily(data)


def _parse_daily(data):
    """把 API 返回的 JSON 转成规范化的 DataFrame。"""
    daily = data.get("daily", {})
    df = pd.DataFrame({
        "date": daily.get("time", []),
        "avg_temp": daily.get("temperature_2m_mean", []),
        "max_temp": daily.get("temperature_2m_max", []),
        "min_temp": daily.get("temperature_2m_min", []),
        "rainfall": daily.get("precipitation_sum", []),
        "wind_speed": daily.get("wind_speed_10m_max", []),
        "humidity": daily.get("relative_humidity_2m_mean", [])
    })
    return df


# ============ 主流程 ============

def main():
    print("=" * 55)
    print("🌤️  宣城真实气象数据生成器")
    print("=" * 55)

    today = datetime.date.today()
    # 历史数据（截止到3天前）
    archive_end = today - datetime.timedelta(days=3)
    archive_start = archive_end - datetime.timedelta(days=30)

    # 1. 拉历史数据
    try:
        df_history = fetch_archive_data(archive_start, archive_end)
    except Exception as e:
        print(f"❌ 历史数据拉取失败：{e}")
        sys.exit(1)

    # 2. 拉最近3天数据
    try:
        df_recent = fetch_forecast_past_data(past_days=3)
    except Exception as e:
        print(f"⚠️ 近3天数据拉取失败（可忽略）：{e}")
        df_recent = pd.DataFrame()

    # 3. 合并
    df_all = pd.concat([df_history, df_recent], ignore_index=True)

    # 4. 清洗
    df_all["date"] = pd.to_datetime(df_all["date"]).dt.strftime("%Y-%m-%d")
    df_all = df_all.drop_duplicates(subset=["date"], keep="last")  # 用新数据覆盖
    df_all = df_all.dropna(subset=["avg_temp"])                    # 关键字段不能为空
    df_all = df_all.sort_values("date").reset_index(drop=True)
    df_all["city"] = "宣城"

    # 5. 重排列顺序，保证和数据库设计一致
    df_all = df_all[[
        "date", "city", "avg_temp", "max_temp", "min_temp",
        "rainfall", "wind_speed", "humidity"
    ]]

    # 6. 写入数据库
    engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
    df_all.to_sql("daily_weather", con=engine, if_exists="replace", index=False)

    # 7. 输出结果
    print("-" * 55)
    print(f"✅ 成功写入 {len(df_all)} 条宣城真实气象数据")
    print(f"📅 数据范围：{df_all['date'].min()} 至 {df_all['date'].max()}")
    print(f"📊 数据预览：")
    print(df_all.tail(5).to_string(index=False))
    print("=" * 55)


if __name__ == "__main__":
    main()