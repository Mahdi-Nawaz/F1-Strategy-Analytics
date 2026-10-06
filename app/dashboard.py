import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import fastf1

# Add src to path so we can import summarize_race
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_dir, 'src'))
from summarize_race import generate_summary

st.set_page_config(page_title="F1 Advanced Analytics", layout="wide")

# Enable FastF1 Cache for on-demand telemetry
cache_dir = os.path.join(base_dir, 'cache')
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)

# Connect to database
@st.cache_resource
def get_db_connection():
    db_path = os.path.join(base_dir, 'data', 'f1_data.db')
    if not os.path.exists(db_path):
        return None
    return sqlite3.connect(db_path, check_same_thread=False)

conn = get_db_connection()

if conn is None:
    st.error("Database not found. Please run fetch_data.py first to populate data.")
    st.stop()

st.title("🏎️ F1 Advanced Analytics & Strategy Dashboard")

# Fetch available races
races_df = pd.read_sql("SELECT DISTINCT Year, Race FROM laps ORDER BY Year DESC, Race", conn)
if races_df.empty:
    st.warning("No data available in the database.")
    st.stop()

races_df['Race_Name'] = races_df['Year'].astype(str) + " " + races_df['Race']
race_names = races_df['Race_Name'].tolist()

selected_race_name = st.selectbox("Select a Race", race_names)
selected_year = int(selected_race_name.split(" ")[0])
selected_race = " ".join(selected_race_name.split(" ")[1:])

# Fetch data for the selected race
@st.cache_data
def load_race_data(year, race):
    query = "SELECT * FROM laps WHERE Year = ? AND Race = ?"
    df = pd.read_sql(query, conn, params=(year, race))
    return df

laps = load_race_data(selected_year, selected_race)

if not laps.empty:
    # Fetch driver mapping from results
    query_results = "SELECT Abbreviation, FullName, TeamColor FROM results WHERE Year = ? AND Race = ?"
    try:
        results_df = pd.read_sql(query_results, conn, params=(selected_year, selected_race))
        driver_map = dict(zip(results_df['Abbreviation'], results_df['FullName']))
        color_map = dict(zip(results_df['Abbreviation'], results_df['TeamColor']))
    except:
        driver_map = {}
        color_map = {}
    
    # Filter out missing drivers
    drivers = sorted(laps['Driver'].dropna().unique())
    
    st.sidebar.header("Driver Selection")
    
    def format_driver(abbr):
        return f"{driver_map.get(abbr, abbr)} ({abbr})"
        
    driver1 = st.sidebar.selectbox("Driver 1", drivers, index=0, format_func=format_driver)
    driver2 = st.sidebar.selectbox("Driver 2", drivers, index=1 if len(drivers) > 1 else 0, format_func=format_driver)
    
    # --- TABS FOR ADVANCED LAYOUT ---
    tab1, tab2, tab3 = st.tabs(["📊 Race Pace & Strategy", "🔬 Telemetry Deep Dive", "📄 Auto-Summary Report"])
    
    with tab1:
        st.subheader(f"Lap Time Comparison: {driver1} vs {driver2}")
        
        plot_df = laps[laps['Driver'].isin([driver1, driver2])].copy()
        plot_df = plot_df.dropna(subset=['LapTime'])
        plot_df['LapTime'] = pd.to_numeric(plot_df['LapTime'], errors='coerce')
        plot_df = plot_df.dropna(subset=['LapTime'])
        
        median_time = plot_df['LapTime'].median()
        plot_df = plot_df[plot_df['LapTime'] < (median_time * 1.2)]
        
        # Build line chart
        fig1 = px.line(plot_df, x='LapNumber', y='LapTime', color='Driver', 
                       markers=True, title="Lap Times over the Race",
                       labels={'LapTime': 'Lap Time (seconds)'})
        st.plotly_chart(fig1, use_container_width=True)
        
        st.subheader("Tyre Degradation per Stint")
        plot_df['TyreLife'] = pd.to_numeric(plot_df['TyreLife'], errors='coerce')
        plot_df = plot_df.dropna(subset=['TyreLife', 'Compound'])
        
        fig2 = px.scatter(plot_df, x='TyreLife', y='LapTime', color='Compound', 
                          symbol='Driver', trendline="ols",
                          title="Tyre Degradation (Lap Time vs Tyre Age)",
                          labels={'LapTime': 'Lap Time (seconds)', 'TyreLife': 'Tyre Age (Laps)'})
        st.plotly_chart(fig2, use_container_width=True)
        
        st.subheader("Track Evolution (All Drivers)")
        all_laps = laps.copy()
        all_laps['LapTime'] = pd.to_numeric(all_laps['LapTime'], errors='coerce')
        all_laps = all_laps.dropna(subset=['LapTime', 'LapNumber'])
        
        all_median = all_laps['LapTime'].median()
        all_laps = all_laps[all_laps['LapTime'] < (all_median * 1.2)]
        
        fig3 = px.scatter(all_laps, x='LapNumber', y='LapTime', opacity=0.3,
                          trendline="lowess", trendline_color_override="red",
                          title="Overall Track Evolution (All Drivers)",
                          labels={'LapTime': 'Lap Time (seconds)'})
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Speed vs Distance Telemetry")
        st.markdown("Compare the exact braking and acceleration points of both drivers on their fastest lap.")
        
        if st.button("Load Telemetry (Takes ~10 seconds)"):
            with st.spinner("Fetching high-frequency telemetry from FastF1..."):
                try:
                    session = fastf1.get_session(selected_year, selected_race, 'R')
                    session.load(telemetry=True, weather=False, messages=False)
                    
                    d1_lap = session.laps.pick_driver(driver1).pick_fastest()
                    d2_lap = session.laps.pick_driver(driver2).pick_fastest()
                    
                    d1_tel = d1_lap.get_car_data().add_distance()
                    d2_tel = d2_lap.get_car_data().add_distance()
                    
                    fig_tel = go.Figure()
                    
                    # Use team colors if available, otherwise defaults
                    c1 = f"#{color_map.get(driver1, 'FFFFFF')}"
                    c2 = f"#{color_map.get(driver2, 'FF0000')}"
                    
                    fig_tel.add_trace(go.Scatter(x=d1_tel['Distance'], y=d1_tel['Speed'], 
                                                 mode='lines', name=f"{driver1} (Fastest)", line=dict(color=c1)))
                    fig_tel.add_trace(go.Scatter(x=d2_tel['Distance'], y=d2_tel['Speed'], 
                                                 mode='lines', name=f"{driver2} (Fastest)", line=dict(color=c2)))
                    
                    fig_tel.update_layout(title=f"Telemetry Comparison: {driver1} vs {driver2}",
                                          xaxis_title="Distance (m)",
                                          yaxis_title="Speed (km/h)",
                                          hovermode="x unified")
                    
                    st.plotly_chart(fig_tel, use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading telemetry: {e}")

    with tab3:
        st.subheader("Auto-Generated Race Summary")
        st.markdown("Extracting insights directly from the database...")
        with st.spinner("Generating summary..."):
            summary_text = generate_summary(selected_year, selected_race)
            st.info(summary_text)
