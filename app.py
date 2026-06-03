import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import datetime

st.set_page_config(page_title="Погода Дашборд", page_icon="🌧", layout="wide", initial_sidebar_state="collapsed")

# CSS-хак для замены текста "Select all" и "Clear all" внутри Streamlit компонентов
# А также для увеличения шрифта в боковом меню
st.markdown("""
    <style>
    /* Увеличиваем шрифт заголовков и подписей в боковой панели */
    [data-testid="stSidebar"] .st-emotion-cache-1104q3m {
        font-size: 22px !important;
    }
    [data-testid="stSidebar"] label p {
        font-size: 18px !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 16px !important;
    }

    /* Пытаемся перевести системные надписи через CSS-псевдоэлементы */
    div[data-baseweb="select"] ul li:first-child[aria-label="Select all"] span {
        font-size: 0;
    }
    div[data-baseweb="select"] ul li:first-child[aria-label="Select all"] span::after {
        content: "Выбрать всё";
        font-size: 1rem;
        visibility: visible;
    }

    /* Скрываем кнопку Deploy и стандартное меню (гамбургер) Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none !important;}
    [data-testid="stAppDeployButton"] {display: none !important;}

    /* Адаптация для мобильных устройств */
    @media (max-width: 768px) {
        h1 { font-size: 1.4rem !important; }
        h2, h3 { font-size: 1.1rem !important; }
        [data-testid="stSidebar"] label p { font-size: 15px !important; }
        [data-testid="stSidebar"] div[role="radiogroup"] label p { font-size: 14px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# Используем относительный путь, чтобы база находилась и локально, и на сервере
DB_PATH = "weather_data.db"

@st.cache_data(ttl=3600)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM precipitation", conn)
    conn.close()
    return df

try:
    df = load_data()
    df = df[df["Year"] >= 2021] # Фильтр: только с 2021 года
except Exception as e:
    st.error(f"Ошибка загрузки базы данных: {e}")
    st.stop()

st.title("🌧 Анализ динамики осадков (pogodaiklimat.ru)", anchor=False)

st.sidebar.header("Настройки фильтра")

# Читаем сохраненное состояние из URL
qp = st.query_params
saved_cities = qp.get_all("city") if "city" in qp else []
saved_mode   = qp.get("mode", "По годам")
saved_season = qp.get("season", "Зима")
saved_month  = qp.get("month", "Январь")

# City filter
available_cities = sorted(df["City"].unique())
default_cities = [c for c in saved_cities if c in available_cities] or (available_cities[:1] if available_cities else [])
selected_cities = st.sidebar.multiselect(
    "Выберите города:", 
    available_cities, 
    default=default_cities,
    placeholder="Выберите город(а)..."
)

if not selected_cities:
    st.warning("Пожалуйста, выберите хотя бы один город для анализа.")
    st.stop()

modes = ["По годам", "По сезонам", "По месяцам", "Сводная"]
saved_mode_idx = modes.index(saved_mode) if saved_mode in modes else 0
analysis_mode = st.sidebar.radio(
    "Режим анализа:",
    modes,
    index=saved_mode_idx
)

# Сохраняем города и режим в URL
st.query_params["city"] = selected_cities
st.query_params["mode"] = analysis_mode

# Filtering data for selected cities
df_filtered = df[df["City"].isin(selected_cities)].copy()

if df_filtered.empty:
    st.warning("Нет данных для выбранных фильтров.")
    st.stop()

if analysis_mode == "По годам":
    # Group by City, Year
    df_grouped = df_filtered.groupby(["City", "Year"])["Precipitation"].sum().reset_index()
    
    st.subheader("Суммарное количество осадков по годам")
    
    fig = px.bar(
        df_grouped, x="Year", y="Precipitation", color="City", barmode="group",
        labels={"Year": "Год", "Precipitation": "Количество осадков (мм)"},
        title="Динамика осадков (По годам)",
        text_auto='.1f'
    )
    fig.update_xaxes(type='category', title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_traces(textfont_size=14, textangle=0, textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)

elif analysis_mode == "По сезонам":
    seasons = ["Зима", "Весна", "Лето", "Осень"]
    saved_season_idx = seasons.index(saved_season) if saved_season in seasons else 0
    selected_season = st.sidebar.selectbox("Выберите сезон:", seasons, index=saved_season_idx)
    st.query_params["season"] = selected_season
    
    # Filter by season
    df_season = df_filtered[df_filtered["Season"] == selected_season]
    
    # Убираем будущие года (например, зима 2027), так как там нет полных данных
    current_year = datetime.date.today().year
    df_season = df_season[df_season["SeasonYear"] <= current_year]
    
    # Sum by City, SeasonYear
    df_grouped = df_season.groupby(["City", "SeasonYear"])["Precipitation"].sum().reset_index()
    
    st.subheader(f"Сравнение количества осадков в сезон: {selected_season}")
    st.info("Примечание: Зима включает декабрь предыдущего года, а также январь и февраль текущего (указанного) года.")
    
    fig = px.bar(
        df_grouped, x="SeasonYear", y="Precipitation", color="City", barmode="group",
        labels={"SeasonYear": "Год сезона", "Precipitation": "Количество осадков (мм)"},
        title=f"Динамика осадков (Сезон: {selected_season})",
        text_auto='.1f'
    )
    fig.update_xaxes(type='category', title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_traces(textfont_size=14, textangle=0, textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)

elif analysis_mode == "По месяцам":
    month_names = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    month_list = list(month_names.values())
    saved_month_idx = month_list.index(saved_month) if saved_month in month_list else 0
    selected_month_name = st.sidebar.selectbox("Выберите месяц:", month_list, index=saved_month_idx)
    st.query_params["month"] = selected_month_name
    selected_month_num = [k for k, v in month_names.items() if v == selected_month_name][0]
    
    # Filter by month
    df_month = df_filtered[df_filtered["Month"] == selected_month_num]
    
    st.subheader(f"Сравнение количества осадков в месяц: {selected_month_name}")
    
    fig = px.bar(
        df_month, x="Year", y="Precipitation", color="City", barmode="group",
        labels={"Year": "Год", "Precipitation": "Количество осадков (мм)"},
        title=f"Динамика осадков (Месяц: {selected_month_name})",
        text_auto='.1f'
    )
    fig.update_xaxes(type='category', title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=14))
    fig.update_traces(textfont_size=14, textangle=0, textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)

elif analysis_mode == "Сводная":
    st.subheader("Сводная матрица осадков (Тепловая карта)")
    st.info("Чем темнее цвет ячейки, тем больше осадков выпало в этот месяц.")
    
    month_names_dict = {
        1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр",
        5: "Май", 6: "Июн", 7: "Июл", 8: "Авг",
        9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек"
    }
    
    for city in selected_cities:
        if len(selected_cities) > 1:
            st.markdown(f"### {city}")
            
        df_city = df_filtered[df_filtered["City"] == city]
        
        # Создаем сводную таблицу (Year vs Month)
        pivot_df = df_city.pivot_table(index="Year", columns="Month", values="Precipitation", aggfunc="sum")
        
        # Переименуем колонки в текстовые названия месяцев
        pivot_df = pivot_df.rename(columns=month_names_dict)
        
        # Сортируем года по убыванию, чтобы текущий год был сверху (удобнее читать)
        pivot_df = pivot_df.sort_index(ascending=False)
        
        fig = px.imshow(
            pivot_df,
            labels=dict(x="Месяц", y="Год", color="Осадки (мм)"),
            x=pivot_df.columns,
            y=pivot_df.index.astype(str), # как строки для оси
            text_auto='.1f',
            aspect="auto",
            color_continuous_scale="Blues"
        )
        # Переносим ось X (месяцы) наверх для удобства
        fig.update_xaxes(side="top", title_font=dict(size=16), tickfont=dict(size=14))
        fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=14))
        
        st.plotly_chart(fig, use_container_width=True)
