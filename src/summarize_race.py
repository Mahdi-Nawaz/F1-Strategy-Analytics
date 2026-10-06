import sqlite3
import pandas as pd
import os

def generate_summary(year, race_name, db_path=None):
    if db_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, 'data', 'f1_data.db')
        
    if not os.path.exists(db_path):
        return "Database not found."
        
    conn = sqlite3.connect(db_path)
    
    summary = []
    summary.append(f"### Race Summary: {year} {race_name}\n")
    
    # 1. Fastest Lap
    laps_query = "SELECT Driver, LapTime, LapNumber, Compound, Stint FROM laps WHERE Year = ? AND Race = ?"
    laps = pd.read_sql(laps_query, conn, params=(year, race_name))
    
    if laps.empty:
        return "No lap data available for this race."
        
    laps['LapTime'] = pd.to_numeric(laps['LapTime'], errors='coerce')
    laps = laps.dropna(subset=['LapTime'])
    
    if not laps.empty:
        fastest_lap = laps.loc[laps['LapTime'].idxmin()]
        fastest_time_str = f"{fastest_lap['LapTime']:.3f}s"
        summary.append(f"**Fastest Lap:** {fastest_lap['Driver']} on Lap {fastest_lap['LapNumber']} with {fastest_lap['Compound']} tyres ({fastest_time_str}).\n")
    
    # 2. Results & Biggest Overtake (if Grid and Position exist)
    results_query = "SELECT DriverNumber, Abbreviation, GridPosition, Position FROM results WHERE Year = ? AND Race = ?"
    try:
        results = pd.read_sql(results_query, conn, params=(year, race_name))
        results['GridPosition'] = pd.to_numeric(results['GridPosition'], errors='coerce')
        results['Position'] = pd.to_numeric(results['Position'], errors='coerce')
        results['PositionsGained'] = results['GridPosition'] - results['Position']
        
        if not results.empty:
            biggest_mover = results.loc[results['PositionsGained'].idxmax()]
            summary.append(f"**Biggest Mover:** {biggest_mover['Abbreviation']} started P{int(biggest_mover['GridPosition'])} and finished P{int(biggest_mover['Position'])} (gained {int(biggest_mover['PositionsGained'])} positions).\n")
            
            winner = results.loc[results['Position'] == 1]
            if not winner.empty:
                winner = winner.iloc[0]
                summary.append(f"**Race Winner:** {winner['Abbreviation']} (started P{int(winner['GridPosition'])}).\n")
    except Exception as e:
        summary.append(f"*(Could not load results data: {e})*\n")
        
    # 3. Pit-stop windows (average lap for first pit stop)
    if 'Stint' in laps.columns:
        laps['Stint'] = pd.to_numeric(laps['Stint'], errors='coerce')
        pit_stops = laps[laps['Stint'] > 1].groupby('Driver').first().reset_index()
        if not pit_stops.empty:
            avg_pit_lap = int(pit_stops['LapNumber'].mean())
            summary.append(f"**Average First Pit Stop:** Lap {avg_pit_lap}.\n")
        
    # 4. Key Race Control Events
    messages_query = "SELECT Message FROM messages WHERE Year = ? AND Race = ?"
    try:
        messages = pd.read_sql(messages_query, conn, params=(year, race_name))
        sc_vsc = messages[messages['Message'].str.contains('SAFETY CAR|VIRTUAL SAFETY CAR|RED FLAG', case=False, na=False)]
        
        if not sc_vsc.empty:
            summary.append("**Key Race Control Events:**")
            unique_events = sc_vsc['Message'].unique()
            for event in unique_events:
                summary.append(f"- {event}")
        else:
            summary.append("**Key Race Control Events:** No Safety Cars or Red Flags reported.")
    except Exception as e:
        pass
        
    conn.close()
    return "\n".join(summary)

if __name__ == "__main__":
    print(generate_summary(2024, 'Bahrain'))
