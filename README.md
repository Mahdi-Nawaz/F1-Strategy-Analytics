# Race Pace Dashboard + Auto Race Summary Report

A full-stack data engineering and analytics project for Formula 1 strategy.

## Features
- Fetches and stores F1 race data locally using `fastf1` and SQLite.
- Interactive Streamlit dashboard to explore lap-time comparisons, tyre degradation, and track evolution.
- Auto-generated race summary reports based on the data.

## Setup
1. Clone this repository
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment
4. Install dependencies: `pip install -r requirements.txt`

## Running the Dashboard
```bash
streamlit run app/dashboard.py
```
