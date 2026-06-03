import pandas as pd
import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime

cities = {
    "Нижний Новгород": "https://www.pogodaiklimat.ru/history/27459_2.htm",
    "Москва": "https://www.pogodaiklimat.ru/history/27612_2.htm",
    "Наро-Фоминск": "https://www.pogodaiklimat.ru/history/27611_2.htm",
    "Люберцы (Жуковский)": "https://www.pogodaiklimat.ru/history/27410_2.htm",
    "Пенза": "https://www.pogodaiklimat.ru/history/27962_2.htm",
    "Волжский (Волгоград)": "https://www.pogodaiklimat.ru/history/34561_2.htm",
    "Омск": "https://www.pogodaiklimat.ru/history/28698_2.htm",
    "Новосибирск": "https://www.pogodaiklimat.ru/history/29638_2.htm",
    "Красноярск": "https://www.pogodaiklimat.ru/history/29570_2.htm",
    "Набережные Челны (Елабуга)": "https://www.pogodaiklimat.ru/history/28506_2.htm",
    "Анапа": "https://www.pogodaiklimat.ru/history/37001_2.htm",
    "Санкт-Петербург": "https://www.pogodaiklimat.ru/history/26063_2.htm",
    "Челябинск": "https://www.pogodaiklimat.ru/history/28645_2.htm"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Мы будем обновлять данные за текущий год
current_year = datetime.date.today().year

def parse_city_current_year(name, url, retries=3):
    print(f"Updating {name} for year {current_year}...")
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            years_div = soup.find('div', class_='chronicle-table-left-column')
            data_div = soup.find('div', class_='chronicle-table')
            
            if not years_div or not data_div:
                print(f"Error: Could not find tables for {name}")
                return []
                
            years_table = years_div.find('table')
            data_table = data_div.find('table')
            
            years_rows = years_table.find_all('tr')
            data_rows = data_table.find_all('tr')
            
            records = []
            
            for y_tr, d_tr in zip(years_rows[1:], data_rows[1:]):
                y_tds = y_tr.find_all('td')
                d_tds = d_tr.find_all('td')
                
                if not y_tds or not d_tds:
                    continue
                    
                year_str = y_tds[0].text.strip()
                if not year_str.isdigit():
                    continue
                    
                year = int(year_str)
                # Инкрементальное обновление: забираем только данные за ТЕКУЩИЙ год
                if year != current_year:
                    continue
                    
                month_vals = []
                for i in range(12):
                    if i < len(d_tds):
                        val_str = d_tds[i].text.strip().replace(',', '.')
                        try:
                            val = float(val_str)
                            if val < -100:
                                val = None
                        except:
                            val = None
                    else:
                        val = None
                    month_vals.append(val)
                    
                records.append({
                    "City": name,
                    "Year": year,
                    "Jan": month_vals[0],
                    "Feb": month_vals[1],
                    "Mar": month_vals[2],
                    "Apr": month_vals[3],
                    "May": month_vals[4],
                    "Jun": month_vals[5],
                    "Jul": month_vals[6],
                    "Aug": month_vals[7],
                    "Sep": month_vals[8],
                    "Oct": month_vals[9],
                    "Nov": month_vals[10],
                    "Dec": month_vals[11]
                })
            return records
        except Exception as e:
            print(f"Attempt {attempt+1} failed to parse {name}: {e}")
    return []

all_records = []
for c_name, c_url in cities.items():
    records = parse_city_current_year(c_name, c_url)
    all_records.extend(records)

if not all_records:
    print(f"No data found for year {current_year}")
    exit(0)

df = pd.DataFrame(all_records)

month_map = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

flat_records = []
for _, row in df.iterrows():
    for m_name, m_num in month_map.items():
        flat_records.append({
            "City": row["City"],
            "Year": row["Year"],
            "Month": m_num,
            "Precipitation": row[m_name]
        })

flat_df = pd.DataFrame(flat_records)

def get_season_and_season_year(row):
    m = row['Month']
    y = row['Year']
    if m in [12, 1, 2]:
        season = "Зима"
        sy = y + 1 if m == 12 else y
    elif m in [3, 4, 5]:
        season = "Весна"
        sy = y
    elif m in [6, 7, 8]:
        season = "Лето"
        sy = y
    elif m in [9, 10, 11]:
        season = "Осень"
        sy = y
    else:
        season = "Unknown"
        sy = y
    return pd.Series([season, sy])

flat_df[['Season', 'SeasonYear']] = flat_df.apply(get_season_and_season_year, axis=1)

# Сохранение в SQLite через UPSERT-логику (DELETE + INSERT)
db_path = "F:\\WeatherDashboard\\weather_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Удаляем старые записи за текущий год, чтобы не было дублей
    cursor.execute("DELETE FROM precipitation WHERE Year = ?", (current_year,))
    conn.commit()
    
    # Добавляем обновленные записи
    flat_df.to_sql("precipitation", conn, if_exists="append", index=False)
    print(f"Incremental update for year {current_year} completed successfully!")
except Exception as e:
    print(f"Database error during update: {e}")
finally:
    conn.close()
