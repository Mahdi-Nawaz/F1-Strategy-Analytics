import fastf1
import pandas as pd
import sqlite3
import os

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    return conn

def fetch_and_store_race(year, race_name, conn, cache_dir):
    fastf1.Cache.enable_cache(cache_dir)
    print(f"Fetching {year} {race_name}...")
    try:
        # Load race session (telemetry=False to save time if we don't need micro-level telemetry for now)
        # We need weather=True, messages=False is fine but maybe we want messages later. 
        # Let's load everything except full car telemetry for speed, or just load everything.
        session = fastf1.get_session(year, race_name, 'R')
        session.load(telemetry=False, weather=True, messages=True)
        
        # 1. Laps
        laps = session.laps
        laps['Year'] = year
        laps['Race'] = race_name
        # Convert timedelta columns to total seconds for SQLite compatibility
        for col in laps.columns:
            if pd.api.types.is_timedelta64_dtype(laps[col]):
                laps[col] = laps[col].dt.total_seconds()
            elif pd.api.types.is_datetime64_any_dtype(laps[col]):
                laps[col] = laps[col].astype(str)
        
        # 2. Weather
        weather = session.weather_data
        weather['Year'] = year
        weather['Race'] = race_name
        for col in weather.columns:
            if pd.api.types.is_timedelta64_dtype(weather[col]):
                weather[col] = weather[col].dt.total_seconds()
            elif pd.api.types.is_datetime64_any_dtype(weather[col]):
                weather[col] = weather[col].astype(str)
        
        # 3. Results
        results = session.results
        results['Year'] = year
        results['Race'] = race_name
        # Convert datetime/timedelta columns
        for col in results.columns:
            if pd.api.types.is_timedelta64_dtype(results[col]):
                results[col] = results[col].dt.total_seconds()
            elif pd.api.types.is_datetime64_any_dtype(results[col]):
                results[col] = results[col].astype(str)
                
        # Write to sqlite
        # Stringify list or dict columns if they exist
        for df in [laps, weather, results]:
            for col in df.columns:
                if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                    df[col] = df[col].astype(str)
                    
        laps.to_sql('laps', conn, if_exists='append', index=False)
        weather.to_sql('weather', conn, if_exists='append', index=False)
        results.to_sql('results', conn, if_exists='append', index=False)
        
        # 4. Race Control Messages
        messages = session.race_control_messages
        if not messages.empty:
            messages['Year'] = year
            messages['Race'] = race_name
            for col in messages.columns:
                if pd.api.types.is_timedelta64_dtype(messages[col]):
                    messages[col] = messages[col].dt.total_seconds()
                elif pd.api.types.is_datetime64_any_dtype(messages[col]):
                    messages[col] = messages[col].astype(str)
            messages.to_sql('messages', conn, if_exists='append', index=False)

        print(f"Saved {year} {race_name}")
    except Exception as e:
        print(f"Error fetching {year} {race_name}: {e}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(base_dir, 'cache')
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    db_path = os.path.join(data_dir, 'f1_data.db')
    
    # If starting fresh for testing, remove old db
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = init_db(db_path)
    
    # Start with 5 races from 2024
    races_to_fetch = [
        (2024, 'Bahrain'),
        (2024, 'Saudi Arabia'),
        (2024, 'Australia'),
        (2024, 'Japan'),
        (2024, 'China')
    ]
    
    for year, race in races_to_fetch:
        fetch_and_store_race(year, race, conn, cache_dir)
        
    conn.close()
    print("Done fetching 5 races dataset.")
