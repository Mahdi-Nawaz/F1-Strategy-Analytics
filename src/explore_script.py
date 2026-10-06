import fastf1
import pandas as pd
import os

# Enable caching
cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
fastf1.Cache.enable_cache(cache_dir)

# Load 2024 Monaco Race
print("Loading session...")
session = fastf1.get_session(2024, 'Monaco', 'R')
session.load()

print("\n--- LAPS DATA ---")
laps = session.laps
print(f"Laps shape: {laps.shape}")
print("Columns:", laps.columns.tolist())
print("Missing values in Laps:")
print(laps.isna().sum()[laps.isna().sum() > 0])

print("\n--- WEATHER DATA ---")
weather = session.weather_data
print(f"Weather shape: {weather.shape}")
print("Columns:", weather.columns.tolist())

print("\n--- RESULTS DATA ---")
results = session.results
print(f"Results shape: {results.shape}")
print("Columns:", results.columns.tolist())

print("\n--- RACE CONTROL MESSAGES ---")
messages = session.race_control_messages
print(f"Messages shape: {messages.shape}")
print("Columns:", messages.columns.tolist())
print(messages.head())
