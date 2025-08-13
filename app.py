import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="🌦️ Live Weather Forecast",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------
# Global Styles (Animated Background + Glass Cards)
# ---------------------------
ANIMATED_CSS = """
<style>
/********************
  Animated gradient background
*********************/
.stApp {
  background: linear-gradient(60deg, var(--c1), var(--c2), var(--c3));
  background-size: 400% 400%;
  animation: gradientFlow 18s ease infinite;
}

@keyframes gradientFlow {
  0% {background-position: 0% 50%;}
  50% {background-position: 100% 50%;}
  100% {background-position: 0% 50%;}
}

/********************
  Glassmorphism card
*********************/
.glass {
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 16px 18px;
}

.metric-title {font-size: 16px; margin: 0; opacity: 0.9}
.metric-value {font-size: 28px; font-weight: 700; margin: 4px 0 0}

/********************
  Nice header band
*********************/
.header {
  padding: 14px 18px;
  border-radius: 18px;
  display: flex;
  gap: 16px;
  align-items: center;
}
.header .emoji {font-size: 28px}
.header .title {font-size: 20px; font-weight: 700}
.header .subtitle {opacity: 0.85}

/********************
  Progress bar wrapper (for precipitation)
*********************/
.bar-wrap{height:12px;background:rgba(255,255,255,0.25);border-radius:999px;overflow:hidden}
.bar{height:100%;background:linear-gradient(90deg,#60a5fa,#22d3ee);width:0%;transition:width .8s ease}

</style>
"""

# ---------------------------
# Helpers: theme by condition, cards, API calls
# ---------------------------
CONDITION_THEMES = {
    "clear":    {"c1":"#657c87","c2":"#9e978a","c3":"#c78868", "emoji":"☀️", "name":"Clear"},
    "cloudy":   {"c1":"#90A5BA","c2":"#5B7BAA","c3":"#124E82", "emoji":"⛅", "name":"Cloudy"},
    "fog":      {"c1":"#ccb297","c2":"#ae9377","c3":"#231b12", "emoji":"🌫️", "name":"Fog"},
    "rain":     {"c1":"#4e5d7a","c2":"#5b7ac0","c3":"#8ec5fc", "emoji":"🌧️", "name":"Rain"},
    "storm":    {"c1":"#2d3748","c2":"#4b5563","c3":"#111827", "emoji":"⛈️", "name":"Storm"},
    "snow":     {"c1":"#92e6f6","c2":"#c3e7ff","c3":"#ffffff", "emoji":"❄️", "name":"Snow"},
}

# WMO weather codes mapping -> simple condition key
# https://open-meteo.com/en/docs#api_form
WMO_MAP = {
    0:  "clear",
    1:  "cloudy", 2:  "cloudy", 3:  "cloudy",
    45: "fog", 48: "fog",
    51: "rain", 53: "rain", 55: "rain",
    56: "rain", 57: "rain",
    61: "rain", 63: "rain", 65: "rain",
    66: "rain", 67: "rain",
    71: "snow", 73: "snow", 75: "snow",
    77: "snow",
    80: "rain", 81: "rain", 82: "rain",
    85: "snow", 86: "snow",
    95: "storm", 96: "storm", 99: "storm",
}

@st.cache_data(ttl=1800)
def geocode_city(city_name: str):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    r = requests.get(url, timeout=20)
    if r.status_code == 200:
        js = r.json()
        if js.get("results"):
            res = js["results"][0]
            return {
                "latitude": res["latitude"],
                "longitude": res["longitude"],
                "name": res["name"],
                "country": res.get("country", ""),
            }
    return None

@st.cache_data(ttl=300)
def fetch_weather(lat: float, lon: float):
    # Hourly + Daily with useful fields
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&hourly=temperature_2m,apparent_temperature,relativehumidity_2m,windspeed_10m,precipitation_probability"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,"
        "sunrise,sunset,uv_index_max,precipitation_sum,windspeed_10m_max,windgusts_10m_max"
        "&timezone=auto"
    )
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def set_theme_from_code(wmo_code: int):
    key = WMO_MAP.get(wmo_code, "cloudy")
    theme = CONDITION_THEMES[key]
    css_vars = f"<style>:root{{--c1:{theme['c1']};--c2:{theme['c2']};--c3:{theme['c3']};}}</style>"
    st.markdown(css_vars + ANIMATED_CSS, unsafe_allow_html=True)
    return theme

# Render a glass metric card
def glass_metric(title: str, value: str):
    st.markdown(
        f"""
        <div class="glass">
            <p class="metric-title">{title}</p>
            <p class="metric-value">{value}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Render header band
def header_band(emoji: str, title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="glass header">
            <div class="emoji">{emoji}</div>
            <div>
                <div class="title">{title}</div>
                <div class="subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------
# Sidebar Controls
# ---------------------------
st.sidebar.title("⚙️ Controls")
city = st.sidebar.text_input("Enter City (India)", value="Chennai")
hours_ahead = st.sidebar.slider("Forecast Horizon (hours)", min_value=6, max_value=48, value=24, step=6)
show_table = st.sidebar.checkbox("Show Detailed Table", value=True)

# Useful quick-picks
with st.sidebar.expander("Quick Picks"):
    col_a, col_b = st.columns(2)
    if col_a.button("Delhi"): city = "Delhi"
    if col_b.button("Mumbai"): city = "Mumbai"
    if col_a.button("Bengaluru"): city = "Bengaluru"
    if col_b.button("Chennai"): city = "Chennai"

st.title("🌦️ Live Weather Dashboard — Animated & Interactive")

if not city:
    st.info("Please enter a city in the sidebar to begin.")
    st.stop()

# ---------------------------
# Fetch: Geocode -> Weather
# ---------------------------
geo = geocode_city(city)
if not geo:
    st.error("❌ City not found. Please try another name.")
    st.stop()

try:
    data = fetch_weather(geo["latitude"], geo["longitude"])
except Exception as e:
    st.error(f"❌ Failed to fetch weather data: {e}")
    st.stop()

current = data.get("current_weather", {})

# Theme + header
theme = set_theme_from_code(int(current.get("weathercode", 1)))
local_time = pd.to_datetime(current.get("time")).strftime("%a, %d %b %Y • %I:%M %p")
header_band(
    theme["emoji"],
    f"{geo['name']}, {geo['country']} — {theme['name']}",
    f"Last updated: {local_time}",
)

# ---------------------------
# Current Conditions (Cards)
# ---------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    glass_metric("Temperature", f"{current.get('temperature','–')} °C")
with col2:
    glass_metric("Feels Like", "–")  # will fill from hourly below
with col3:
    glass_metric("Wind Speed", f"{current.get('windspeed','–')} km/h")
with col4:
    glass_metric("Wind Direction", f"{current.get('winddirection','–')}°")

# ---------------------------
# Prepare Hourly / Daily DataFrames
# ---------------------------
hourly = pd.DataFrame(data.get("hourly", {}))
daily = pd.DataFrame(data.get("daily", {}))

if not hourly.empty:
    hourly["time"] = pd.to_datetime(hourly["time"])  # already in local timezone
    now = pd.to_datetime(current["time"]) if current.get("time") else hourly["time"].iloc[0]
    mask = (hourly["time"] >= now) & (hourly["time"] < now + timedelta(hours=hours_ahead))
    hr = hourly.loc[mask].copy()

    # Fill Feels Like in card if available
    if "apparent_temperature" in hourly.columns and not hr.empty:
        feels_now = hr.iloc[0]["apparent_temperature"]
        with col2:
            glass_metric("Feels Like", f"{feels_now:.1f} °C")

 # --- Friendly Weather Messages ---
    def weather_message(temp, wind, rain_prob):
        if temp > 38:
            return "🔥 It's scorching outside! Better stay indoors with a cool drink."
        elif temp > 30:
            return "☀️ It's quite sunny today. Don't forget your sunglasses!"
        elif temp < 10:
            return "❄️ Brrr! It's freezing out there. Dress warmly and sip something hot."
        elif temp < 18:
            return "🌤️ It's a cool day, perfect for a walk."
        
        if wind > 40:
            return "🌪️ Strong winds are blowing. Secure loose objects outside!"
        elif wind > 20:
            return "💨 Breezy day! A cap might fly away."

        if rain_prob > 70:
            return "🌧️ High chance of rain — take an umbrella!"
        elif rain_prob > 40:
            return "🌦️ You might get some showers later today."

        return "🌈 Weather looks pleasant. Enjoy your day!"

    rain_probability = hr.iloc[0]["precipitation_probability"] if "precipitation_probability" in hr else 0
    friendly_message = weather_message(
        current['temperature'],
        current['windspeed'],
        rain_probability
    )
    st.info(friendly_message)

# ---------------------------
# Alerts (Heat / Wind / Rain / UV)
# ---------------------------
alerts = []
if not hr.empty:
    t_now = float(hr.iloc[0]["apparent_temperature"]) if "apparent_temperature" in hr else float(current.get("temperature", 0))
    if t_now >= 40:
        alerts.append("🔥 Severe Heat Alert: Stay hydrated, avoid peak sun.")
    elif t_now >= 35:
        alerts.append("🥵 Heat Caution: Wear light clothing and drink water.")

    ws_now = float(current.get("windspeed", 0))
    if ws_now >= 75:
        alerts.append("🌬️ Gale Warning: Secure loose items, avoid high places.")
    elif ws_now >= 50:
        alerts.append("💨 High Wind: Be cautious outdoors.")

    rain_next6 = hr.head(6)["precipitation_probability"].max() if "precipitation_probability" in hr else 0
    if rain_next6 >= 70:
        alerts.append("🌧️ High chance of rain in next 6 hours. Carry an umbrella.")

    # UV index from today's daily
    if not daily.empty and "uv_index_max" in daily.columns:
        uv_today = float(daily.iloc[0]["uv_index_max"])
        if uv_today >= 8:
            alerts.append("☀️ Extreme UV today. Use SPF 30+, hat & sunglasses.")

if alerts:
    for a in alerts:
        st.warning(a)

# ---------------------------
# Charts: Temperature (air vs feels), Precip %, Wind speed
# ---------------------------
if not hr.empty:
    # Pretty labels
    hr_plot = hr.rename(columns={
        "temperature_2m": "Air Temperature (°C)",
        "apparent_temperature": "Feels Like (°C)",
        "precipitation_probability": "Precipitation Probability (%)",
        "windspeed_10m": "Wind Speed (km/h)",
    })

    st.subheader("📈 Hourly Forecast")

    # Temperature chart
    temp_cols = [c for c in ["Air Temperature (°C)", "Feels Like (°C)"] if c in hr_plot.columns]
    if temp_cols:
        fig_t = px.line(hr_plot, x="time", y=temp_cols, markers=True)
        fig_t.update_layout(title="Temperature (Next Hours)", xaxis_title="Time", yaxis_title="°C", legend_title="")
        st.plotly_chart(fig_t, use_container_width=True)

    # Precipitation probability
    if "Precipitation Probability (%)" in hr_plot.columns:
        fig_p = px.bar(hr_plot, x="time", y="Precipitation Probability (%)")
        fig_p.update_layout(title="Precipitation Probability", xaxis_title="Time", yaxis_title="%")
        st.plotly_chart(fig_p, use_container_width=True)

    # Wind speed
    if "Wind Speed (km/h)" in hr_plot.columns:
        fig_w = px.line(hr_plot, x="time", y="Wind Speed (km/h)", markers=True)
        fig_w.update_layout(title="Wind Speed", xaxis_title="Time", yaxis_title="km/h")
        st.plotly_chart(fig_w, use_container_width=True)

# ---------------------------
# Today Snapshot (Sunrise/Sunset & High/Low)
# ---------------------------
if not daily.empty:
    st.subheader("🗓️ Today at a Glance")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def fmt_time(x):
        try:
            return pd.to_datetime(x).strftime("%I:%M %p")
        except:
            return "–"

    with c1:
        glass_metric("High", f"{daily.iloc[0]['temperature_2m_max']:.1f} °C")
    with c2:
        glass_metric("Low", f"{daily.iloc[0]['temperature_2m_min']:.1f} °C")
    with c3:
        glass_metric("Feels Max", f"{daily.iloc[0]['apparent_temperature_max']:.1f} °C")
    with c4:
        glass_metric("Sunrise", fmt_time(daily.iloc[0]['sunrise']))
    with c5:
        glass_metric("Sunset", fmt_time(daily.iloc[0]['sunset']))
    with c6:
        glass_metric("UV Index Max", f"{daily.iloc[0]['uv_index_max']:.0f}")

# ---------------------------
# Precipitation progress (next hour)
# ---------------------------
if not hr.empty and "precipitation_probability" in hr:
    next_prob = int(hr.iloc[0]["precipitation_probability"]) if pd.notna(hr.iloc[0]["precipitation_probability"]) else 0
    st.markdown("#### ☔ Chance of Rain (next hour)")
    st.markdown(
        f"""
        <div class="glass" style="padding:14px">
            <div class="bar-wrap"><div class="bar" style="width:{next_prob}%"></div></div>
            <div style="margin-top:8px;font-weight:600">{next_prob}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------
# Details Table
# ---------------------------
if show_table and not hr.empty:
    table = hr[[c for c in [
        "time", "temperature_2m", "apparent_temperature", "relativehumidity_2m",
        "precipitation_probability", "windspeed_10m"
    ] if c in hr.columns]].copy()
    table.columns = [
        "Time", "Temp (°C)", "Feels (°C)", "Humidity (%)", "Rain %", "Wind (km/h)"
    ]
    table["Time"] = table["Time"].dt.strftime("%d %b • %I:%M %p")
    st.markdown("#### 🔎 Detailed Hourly Table")
    st.dataframe(table, use_container_width=True, hide_index=True)

# ---------------------------
# Footer note
# ---------------------------
st.caption("Data source: Open-Meteo. This dashboard uses animated backgrounds, glass cards, and interactive Plotly charts for an at-a-glance weather experience.")
