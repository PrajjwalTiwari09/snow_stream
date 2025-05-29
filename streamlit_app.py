import streamlit as st
import pandas as pd
import snowflake.connector
import altair as alt
import pydeck as pdk

st.markdown("""
<h1 style='text-align: center; font-size: 36px; color: #2c3e50;'>
🌟 Celebrating India's Cultural Legacy <br>
<small style='font-size:20px; color: #555;'>Art • Heritage • Tourism • Tradition</small>
</h1>
""", unsafe_allow_html=True)

import streamlit as st
import snowflake.connector

# Access Snowflake credentials from secrets
sf_creds = st.secrets["snowflake"]

# Connect to Snowflake
conn = snowflake.connector.connect(
    user=sf_creds["user"],
    password=sf_creds["password"],
    account=sf_creds["account"],
    warehouse=sf_creds["warehouse"],
    database=sf_creds["database"],
    schema=sf_creds["schema"]
)

# Load data
@st.cache_data
def load_data(table_name):
    query = f"SELECT * FROM {table_name}"
    return pd.read_sql(query, conn)

# Load all datasets
df_states = load_data("TOURIST_VISITS_STATE")
df_monuments = load_data("TOURIST_VISITS_MONUMENTS")
df_heritage = load_data("INTANGIBLE_HERITAGE")
df_swadesh = load_data("SWADESH_DARSHAN_SUMMARY")

# Clean column names
df_states.columns = df_states.columns.str.strip().str.upper()
df_monuments.columns = df_monuments.columns.str.strip().str.upper()
df_heritage.columns = df_heritage.columns.str.strip().str.upper()

# Melt state data
df_states_long = df_states.melt(
    id_vars=["STATE"],
    value_vars=["DOMESTIC_2020", "FOREIGN_2020", "DOMESTIC_2021", "FOREIGN_2021"],
    var_name="TYPE_YEAR",
    value_name="VISITORS"
)
df_states_long[["VISITOR_TYPE", "YEAR"]] = df_states_long["TYPE_YEAR"].str.split("_", expand=True)
df_states_long["YEAR"] = df_states_long["YEAR"].astype(int)

# ✅ Clean numeric data
df_states_long["VISITORS"] = df_states_long["VISITORS"].astype(str).str.replace(",", "")
df_states_long["VISITORS"] = pd.to_numeric(df_states_long["VISITORS"], errors="coerce").fillna(0).astype(int)

df_states_long[["VISITOR_TYPE", "YEAR"]] = df_states_long["TYPE_YEAR"].str.split("_", expand=True)
df_states_long["YEAR"] = df_states_long["YEAR"].astype(int)

# Tabs for insights
tab1, tab2, tab3= st.tabs(["📈 Tourism Insights", "🏛️ Monuments", "🎭 Heritage"])

# --- TAB 1: Tourism Insights ---
with tab1:
    st.subheader("📊 Tourism Insights by State & Year")

    # Extract filters
    years = sorted(df_states_long["YEAR"].unique(), reverse=True)
    states = sorted(df_states_long["STATE"].unique())

    with st.expander("📌 Filters for Tourism", expanded=True):
        selected_year = st.selectbox("Select Year", years, key="tourism_year")
        selected_state = st.selectbox("Select State", states, key="tourism_state")

    # Filter for current and previous year
    filtered_df = df_states_long[
        (df_states_long["YEAR"] == selected_year) &
        (df_states_long["STATE"] == selected_state)
    ]

    prev_year = selected_year - 1
    prev_df = df_states_long[
        (df_states_long["YEAR"] == prev_year) &
        (df_states_long["STATE"] == selected_state)
    ]

    def get_kpi_data(visitor_type):
        current_val = filtered_df[filtered_df["VISITOR_TYPE"] == visitor_type]["VISITORS"].sum()
        current_val = int(str(current_val).replace(",", "")) if not pd.isna(current_val) else 0

        if not prev_df.empty:
            previous_val = prev_df[prev_df["VISITOR_TYPE"] == visitor_type]["VISITORS"].sum()
            previous_val = int(str(previous_val).replace(",", "")) if not pd.isna(previous_val) else 0
        else:
            previous_val = 0

        diff = current_val - previous_val
        pct_change = (diff / previous_val * 100) if previous_val != 0 else 100.0

        return current_val, previous_val, diff, pct_change

    # KPI Metrics
    st.markdown("### ✨ Key Metrics Overview")
    col1, col2 = st.columns(2)

    for col, vtype in zip([col1, col2], ["DOMESTIC", "FOREIGN"]):
        cur, prev, diff, pct = get_kpi_data(vtype)
        color = "green" if diff > 0 else "red"
        symbol = "🔺" if diff > 0 else "🔻"

        with col:
            st.markdown(f"#### {vtype.capitalize()} Visitors")
            st.markdown(f"""
                <div style='background-color:#f0f2f6;padding:10px;border-radius:10px'>
                    <h1 style='margin-bottom:0'>{cur:,}</h1>
                    <p style='margin:0;color:gray;'>Last year: {prev:,}</p>
                    <p style='margin:0;color:{color};'>{symbol} {abs(diff):,} ({abs(pct):.2f}%) vs last year</p>
                </div>
            """, unsafe_allow_html=True)

    # Visitor breakdown bar charts
    st.markdown("### 📊 Visitor Breakdown by Type")

    domestic_visitors = filtered_df[filtered_df["VISITOR_TYPE"] == "DOMESTIC"]["VISITORS"].sum()
    foreign_visitors = filtered_df[filtered_df["VISITOR_TYPE"] == "FOREIGN"]["VISITORS"].sum()

    bar_data = pd.DataFrame({
        "Type": ["Domestic", "Foreign"],
        "Visitors": [domestic_visitors, foreign_visitors]
    })

    dom_chart = alt.Chart(bar_data[bar_data["Type"] == "Domestic"]).mark_bar(color="#1f77b4").encode(
        x=alt.X('Type:N'),
        y=alt.Y('Visitors:Q', scale=alt.Scale(domain=[0, domestic_visitors * 1.2])),
        tooltip=["Type", alt.Tooltip("Visitors", format=",")]
    ).properties(
        width=300,
        height=300,
        title="Domestic Visitors"
    )

    foreign_chart = alt.Chart(bar_data[bar_data["Type"] == "Foreign"]).mark_bar(color="#ff7f0e").encode(
        x=alt.X('Type:N'),
        y=alt.Y('Visitors:Q', scale=alt.Scale(domain=[0, max(1, foreign_visitors * 1.5)])),
        tooltip=["Type", alt.Tooltip("Visitors", format=",")]
    ).properties(
        width=300,
        height=300,
        title="Foreign Visitors"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(dom_chart, use_container_width=True)
    with col2:
        st.altair_chart(foreign_chart, use_container_width=True)

    # Growth Trends
    st.markdown("### 🚀 Tourism Growth Trends by State")

    df_states["DTV_GROWTH_PCT"] = pd.to_numeric(df_states["DTV_GROWTH_PCT"], errors="coerce")
    df_states["FTV_GROWTH_PCT"] = pd.to_numeric(df_states["FTV_GROWTH_PCT"], errors="coerce")

    growth_df = df_states.melt(
        id_vars=["STATE"],
        value_vars=["DTV_GROWTH_PCT", "FTV_GROWTH_PCT"],
        var_name="Visitor_Type",
        value_name="Growth_Pct"
    )

    growth_df = growth_df.dropna(subset=["Growth_Pct"])

    growth_chart = alt.Chart(growth_df).mark_bar().encode(
        x=alt.X('STATE:N', sort='-y'),
        y=alt.Y('Growth_Pct:Q', title="Growth (%)"),
        color='Visitor_Type:N',
        tooltip=['STATE', 'Visitor_Type', 'Growth_Pct']
    ).properties(
        width=900,
        height=400,
        title="Tourism Growth by State and Type"
    ).interactive()

    st.altair_chart(growth_chart, use_container_width=True)


# --- TAB 2: Monuments ---
with tab2:
    st.subheader("🏛️ Monuments Visitor Insights")

    # Let user select year range
    year_option = st.selectbox("Select Year Range", ["2020_21", "2021_22"], key="monument_year")
    dom_col = f"DOMESTIC_{year_option}"
    for_col = f"FOREIGN_{year_option}"

    # Ensure columns are uppercase and cleaned
    df_monuments.columns = df_monuments.columns.str.strip().str.upper()

    if dom_col in df_monuments.columns and for_col in df_monuments.columns:
        df_monuments[dom_col] = df_monuments[dom_col].replace(",", "", regex=True).astype(int)
        df_monuments[for_col] = df_monuments[for_col].replace(",", "", regex=True).astype(int)
        df_monuments["TOTAL_VISITORS"] = df_monuments[dom_col] + df_monuments[for_col]

        # 🟦 PART 1: Top 10 Overall Monuments
        st.markdown("### 🌐 Overall Top 10 Monuments by Total Visitors")

        top_monuments_overall = df_monuments.sort_values(by="TOTAL_VISITORS", ascending=False).head(10)

        bar_chart = alt.Chart(top_monuments_overall).mark_bar(color="#007acc").encode(
            x=alt.X('TOTAL_VISITORS:Q', title="Total Visitors"),
            y=alt.Y('MONUMENT_NAME:N', sort='-x', title="Monument"),
            tooltip=[
                alt.Tooltip('MONUMENT_NAME', title="Monument"),
                alt.Tooltip('STATE', title="State"),
                alt.Tooltip('TOTAL_VISITORS', title="Total Visitors", format=',')
            ]
        ).properties(width=800, height=400)

        st.altair_chart(bar_chart, use_container_width=True)

        # 🟨 PART 2: Split by State
        st.markdown("### 📍 State-wise Monument Insights")

        state_option = st.selectbox("Select State", sorted(df_monuments["STATE"].unique()), key="monument_state")

        state_filtered = df_monuments[df_monuments["STATE"] == state_option]
        top_monuments_state = state_filtered.sort_values(by="TOTAL_VISITORS", ascending=False).head(10)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Domestic Visitors")
            dom_chart = alt.Chart(top_monuments_state).mark_bar(color="#1f77b4").encode(
                x=alt.X(f'{dom_col}:Q', title="Domestic Visitors"),
                y=alt.Y('MONUMENT_NAME:N', sort='-x'),
                tooltip=[
                    alt.Tooltip('MONUMENT_NAME', title="Monument"),
                    alt.Tooltip(f'{dom_col}', title="Domestic Visitors", format=',')
                ]
            ).properties(width=400, height=400)
            st.altair_chart(dom_chart, use_container_width=True)

        with col2:
            st.markdown("#### Foreign Visitors")
            for_chart = alt.Chart(top_monuments_state).mark_bar(color="#ff7f0e").encode(
                x=alt.X(f'{for_col}:Q', title="Foreign Visitors"),
                y=alt.Y('MONUMENT_NAME:N', sort='-x'),
                tooltip=[
                    alt.Tooltip('MONUMENT_NAME', title="Monument"),
                    alt.Tooltip(f'{for_col}', title="Foreign Visitors", format=',')
                ]
            ).properties(width=400, height=400)
            st.altair_chart(for_chart, use_container_width=True)

    else:
        st.warning(f"Data columns for year {year_option} not found.")

# --- TAB 3: Heritage ---
# --- TAB 3: Heritage and Swadesh Darshan ---
with tab3:
    st.subheader("📈 Growth of Recognized Intangible Cultural Heritage Over Time")

    # Count practices by year
    year_counts = df_heritage["YEAR_LISTED"].value_counts().reset_index()
    year_counts.columns = ["Year", "Count"]
    year_counts = year_counts.sort_values("Year")

    # Line chart
    line_chart = alt.Chart(year_counts).mark_line(point=True).encode(
        x=alt.X("Year:O", title="Year Listed"),
        y=alt.Y("Count:Q", title="Number of Practices Recognized"),
        tooltip=["Year", "Count"]
    ).properties(
        width=800,
        height=400,
        title="Recognition Trend Over the Years"
    )
    st.altair_chart(line_chart, use_container_width=True)

    # Dropdown + Table of heritage names
    st.markdown("### 🔎 See Practices Listed by Year")
    selected_year_for_names = st.selectbox(
        "Select Year",
        sorted(df_heritage["YEAR_LISTED"].unique()),
        key="heritage_year_select"
    )
    names_for_selected_year = df_heritage[df_heritage["YEAR_LISTED"] == selected_year_for_names][["NAME", "TYPE", "REGION"]]

    st.dataframe(
        names_for_selected_year.reset_index(drop=True),
        use_container_width=True,
        height=300
    )

    # ----------------- SWADESH DARSHAN MAP -----------------
    st.subheader("🗺️ Swadesh Darshan Project Locations")

    # Coordinates per state
    state_coords = {
        "Andhra Pradesh": [15.9129, 79.7400],
        "Arunachal Pradesh": [28.2180, 94.7278],
        "Assam": [26.2006, 92.9376],
        "Bihar": [25.0961, 85.3131],
        "Chhattisgarh": [21.2787, 81.8661],
        "Goa": [15.2993, 74.1240],
        "Gujarat": [22.2587, 71.1924],
        "Haryana": [29.0588, 76.0856],
        "Himachal Pradesh": [31.1048, 77.1734],
        "Jammu & Kashmir and Ladakh": [33.7782, 76.5762],
        "Jharkhand": [23.6102, 85.2799],
        "Kerala": [10.8505, 76.2711],
        "Madhya Pradesh": [22.9734, 78.6569],
        "Maharashtra": [19.7515, 75.7139],
        "Manipur": [24.6637, 93.9063],
        "Meghalaya": [25.4670, 91.3662],
        "Mizoram": [23.1645, 92.9376],
        "Nagaland": [26.1584, 94.5624],
        "Odisha": [20.9517, 85.0985],
        "Punjab": [31.1471, 75.3412],
        "Rajasthan": [26.9124, 75.7873],
        "Sikkim": [27.5330, 88.5122],
        "Tamil Nadu": [11.1271, 78.6569],
        "Telangana": [18.1124, 79.0193],
        "Tripura": [23.9408, 91.9882],
        "Uttar Pradesh": [26.8467, 80.9462],
        "Uttarakhand": [30.0668, 79.0193],
        "West Bengal": [22.9868, 87.8550],
        "Andaman & Nicobar Islands": [11.7401, 92.6586],
        "Puducherry": [11.9416, 79.8083],
        "Wayside Amenities Uttar Pradesh and Bihar": [25.5, 82.0],
    }

    # Clean numeric columns
    for col in ["AMOUNT_SANCTIONED", "AMOUNT_UTILISED", "NUM_PROJECTS"]:
        df_swadesh[col] = (
            df_swadesh[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df_swadesh[col] = pd.to_numeric(df_swadesh[col], errors="coerce")

    # Add coordinates
    df_swadesh["LAT"] = df_swadesh["STATE_UT"].map(lambda x: state_coords.get(x, [None, None])[0])
    df_swadesh["LON"] = df_swadesh["STATE_UT"].map(lambda x: state_coords.get(x, [None, None])[1])
    df_map = df_swadesh.dropna(subset=["LAT", "LON"])

    # Filter by state
    state_options = ["All"] + sorted(df_map["STATE_UT"].unique())
    selected_state = st.selectbox("Select a State/UT", state_options, key="swadesh_state_select")

    if selected_state != "All":
        df_map = df_map[df_map["STATE_UT"] == selected_state]

    # Build Pydeck Map Layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[LON, LAT]',
        get_radius=7000,
        get_fill_color=[30, 144, 255],  # Dodger blue
        pickable=True,
        opacity=0.9,
    )

    view_state = pdk.ViewState(
        latitude=22.5,
        longitude=80,
        zoom=4,
        pitch=0,
    )

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[layer],
        tooltip={
            "text": "State: {STATE_UT}\nProjects: {NUM_PROJECTS}\nSanctioned: ₹{AMOUNT_SANCTIONED}\nUtilized: ₹{AMOUNT_UTILISED}"
        }
    ))

