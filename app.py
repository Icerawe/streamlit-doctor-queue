import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os

# File paths
SETTING_FILE = 'setting.csv'
DATA_FILE = 'data.csv'

# Helper functions
def load_settings():
    if os.path.exists(SETTING_FILE):
        return pd.read_csv(SETTING_FILE)
    return pd.DataFrame(columns=['name', 'minimum_queue'])

def save_settings(df):
    df.to_csv(SETTING_FILE, index=False)

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=['date'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def get_month_dates():
    today = date.today()
    first_day = date(today.year, today.month, 1)
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    num_days = (next_month - first_day).days
    return [first_day + timedelta(days=i) for i in range(num_days)]

# Streamlit UI
st.title('Doctor Queue Management')

# Tabs
tab1, tab2 = st.tabs(["Tab Setting", "Day Available Queue"])

with tab1:
    st.header("Settings")
    settings_df = load_settings()
    name = st.text_input("Doctor Name")
    minimum_queue = st.number_input("Minimum Queue", min_value=1, step=1)
    if st.button("Save Setting"):
        if name:
            # Replace if name exists, else add new
            if name in settings_df['name'].values:
                settings_df.loc[settings_df['name'] == name, 'minimum_queue'] = minimum_queue
            else:
                new_row = pd.DataFrame({'name': [name], 'minimum_queue': [minimum_queue]})
                settings_df = pd.concat([settings_df, new_row], ignore_index=True)
            save_settings(settings_df)
            st.success("Setting saved!")
        else:
            st.error("Please enter a name.")

    st.subheader("Raw Settings Data")
    st.dataframe(settings_df)
        # Delete function
    st.subheader("Delete Doctor Setting")
    if not settings_df.empty:
        delete_name = st.selectbox("Select doctor to delete", settings_df['name'])
        if st.button("Delete Setting"):
            settings_df = settings_df[settings_df['name'] != delete_name].reset_index(drop=True)
            save_settings(settings_df)
            st.success(f"Deleted setting for {delete_name}")

with tab2:
    st.header("Day Available for Queue")
    settings_df = load_settings()
    doctor_names = settings_df['name'].tolist()
    doctor_name = st.selectbox("Select Doctor", doctor_names) if doctor_names else None
    # Always select days for next month
    from dateutil.relativedelta import relativedelta
    next_month = date.today() + relativedelta(months=1)
    year = next_month.year
    month = next_month.month
    month_str = next_month.strftime('%Y-%m')
    month_text = next_month.strftime('%Y-%b')
    st.markdown(f"### Queue for {month_text}")
    # Calculate number of days in next month
    if month == 12:
        first_day = date(year, month, 1)
        next_first = date(year + 1, 1, 1)
    else:
        first_day = date(year, month, 1)
        next_first = date(year, month + 1, 1)
    num_days = (next_first - first_day).days
    day_numbers = list(range(1, num_days + 1))
    selected_days = st.multiselect("Select available days (day of month)", day_numbers)
    if st.button("Save Available Days"):
        if selected_days and doctor_name:
            # Load or create queue dict
            queue = {}
            data_df = load_data()
            if not data_df.empty and 'doctor' in data_df.columns and 'date' in data_df.columns:
                for name in data_df['doctor'].unique():
                    queue[name] = [int(d.split('-')[2]) for d in data_df[data_df['doctor'] == name]['date'] if d.startswith(month_str)]
            # Update queue for selected doctor
            queue[doctor_name] = selected_days
            # Save to data.csv
            rows = []
            for name, days in queue.items():
                for d in days:
                    date_str = f"{month_str}-{d:02d}"
                    rows.append({'doctor': name, 'date': date_str})
            new_df = pd.DataFrame(rows)
            save_data(new_df)
            st.success("Available days saved!")
        else:
            st.error("Please select doctor and at least one day.")

    # ...existing code...
    data_df = load_data()
    import random
    if not data_df.empty and 'doctor' in data_df.columns and 'date' in data_df.columns:
        # Verify minimum queue for each doctor
        min_check = []
        for _, row in settings_df.iterrows():
            name = row['name']
            min_queue = row['minimum_queue']
            count = len(data_df[data_df['doctor'] == name])
            status = 'OK' if count >= min_queue else f'Not enough (has {count}, needs {min_queue})'
            min_check.append({'doctor': name, 'assigned_days': count, 'minimum_queue': min_queue, 'status': status})
        st.subheader("Minimum Queue Verification")
        st.dataframe(pd.DataFrame(min_check))

        # Assign one doctor per day (random if multiple, null if none)
        grouped = data_df.groupby('date')['doctor'].apply(list).reset_index()
        assigned = []
        all_dates = grouped['date'].tolist()
        # Fill missing dates for the month
        # Use next_month for month_str
        month_str = next_month.strftime('%Y-%m')
        all_days = [f"{month_str}-{d:02d}" for d in day_numbers]
        for d in all_days:
            doctors = grouped[grouped['date'] == d]['doctor'].values
            if len(doctors) == 0:
                assigned.append({'date': d, 'doctor': None})
            else:
                doc_list = doctors[0]
                chosen = random.choice(doc_list) if len(doc_list) > 0 else None
                assigned.append({'date': d, 'doctor': chosen})
        st.subheader("Doctor Assigned Per Day")
        assigned_df = pd.DataFrame(assigned)
        st.dataframe(assigned_df)

        # Group by doctor name from assigned list
        st.subheader("Assigned Dates Grouped by Doctor Name")
        if not assigned_df.empty:
            grouped_by_doctor = assigned_df.dropna().groupby('doctor')['date'].apply(list).reset_index()
            grouped_by_doctor['count_date'] = grouped_by_doctor['date'].apply(len)
            st.dataframe(grouped_by_doctor)

# Show grouped by date table at the bottom for manual validation
data_df = load_data()
if not data_df.empty and 'doctor' in data_df.columns and 'date' in data_df.columns:
    st.subheader("Result Grouped by Date (Manual Validation)")
    grouped = data_df.groupby('date')['doctor'].apply(list).reset_index()
    st.dataframe(grouped)


st.subheader("Result Grouped by Doctor Name")
data_df['date'] = pd.to_datetime(data_df['date'], errors='coerce')
recheck = (
    data_df
    .dropna(subset=['doctor', 'date'])
    .assign(day=lambda df: df['date'].dt.day)
    .sort_values(['doctor', 'date'])
)

grouped = (
    recheck
    .groupby('doctor', as_index=False)['day']
    .apply(list)
)

st.dataframe(grouped)