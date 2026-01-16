import streamlit as st
import pandas as pd
import altair as alt
from datetime import date




st.set_page_config(page_title="Axial Length Growth Curve", layout="wide")
st.title("Axial Length Growth Curve (Chinese Data)")
st.write('Reference: He, X., Sankaridurg, P., Naduvilath, T., Wang, J., Xiong, S., Weng, R., ... & Xu, X. (2023). Normative data and percentile curves for axial length and axial length/corneal curvature in Chinese children and adolescents aged 4–18 years. British Journal of Ophthalmology, 107(2), 167-175.')




# -----------------------------
# 1. SIDEBAR: GENDER SELECTION
# -----------------------------
st.sidebar.header("Patient information")




gender = st.sidebar.radio(
    "Gender",
    options=["Male", "Female"],
    index=0,
    help="Used to select the appropriate normative growth curve",
)


# Map gender to file name (change if your filenames differ)
GENDER_FILES = {
    "Male":   "male.csv",
    "Female": "female.csv",
}




# -----------------------------
# 2. LOAD GROWTH CURVE FOR SELECTED GENDER
# -----------------------------
@st.cache_data
def load_growth_curve(gender: str):
    file = GENDER_FILES[gender]
    df = pd.read_csv(file)
    # Fix column names (remove BOM and spaces)
    df.columns = [c.strip().replace("�", "") for c in df.columns]
    df = df.dropna(how="all")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df = df.dropna(subset=["Age"])
    return df

df = load_growth_curve(gender)

#st.subheader(f"Raw Growth-Curve Data ({gender})")
#st.dataframe(df)

# Long format for plotting
df_long = df.melt(id_vars="Age", var_name="Percentile", value_name="AxialLength")


# Normalize percentiles so they are plain strings like "3","5","10",...
df_long["Percentile"] = (
    df_long["Percentile"]
    .astype(str)
    .str.replace("th", "", regex=False)  # just in case
    .str.strip()
)

# Define the exact order you want
percentile_order = ["3", "5", "10", "25", "50", "75", "90", "95"]



# -----------------------------
# 3. SESSION STATE FOR VISITS
# -----------------------------
EXPECTED_COLUMNS = ["Gender", "DateOfBirth", "Visit", "VisitDate", "Age", "Eye", "AxialLength"]



if "visits" not in st.session_state:
    st.session_state.visits = pd.DataFrame(columns=EXPECTED_COLUMNS)
else:
    for col in EXPECTED_COLUMNS:
        if col not in st.session_state.visits.columns:
            st.session_state.visits[col] = None


# -----------------------------
# 4. SIDEBAR FORM: MULTIPLE VISITS
#    (NO GENDER FIELD HERE)
# -----------------------------
st.sidebar.header("Add visit")


if "dob" not in st.session_state:
    st.session_state.dob = date(2015, 1, 1)
if "visit_date" not in st.session_state:
    st.session_state.visit_date = date.today()

with st.sidebar.form("visit_form", clear_on_submit=True):
    dob = st.date_input(
        "Date of birth",
        value=st.session_state.dob,
        min_value=date(1990, 1, 1),
        max_value=date.today(),
        key="dob_input",
        help="Used to calculate age at visit",
    )

    # Validate visit_date: if it's before dob, reset to dob
    if st.session_state.visit_date < dob:
        st.session_state.visit_date = dob

    visit_label = st.text_input("Visit label (e.g., baseline, 6M, 1Y)", value="baseline", key="visit_label_input")

    visit_date = st.date_input(
        "Visit date",
        value=st.session_state.visit_date,
        min_value=dob,
        max_value=date.today(),
        key="visit_date_input",
        help="Age is calculated from DOB and visit date",
    )

    # Age in years
    age_days = (visit_date - dob).days
    age_years = round(age_days / 365.25, 2)
    st.markdown(f"**Calculated age:** {age_years:.2f} years")

    axial_right = st.number_input(
        "Right eye (OD) axial length (mm)",
        min_value=18.0, max_value=30.0, step=0.01, value=23.5, key="axial_right_input"
    )
    axial_left = st.number_input(
        "Left eye (OS) axial length (mm)",
        min_value=18.0, max_value=30.0, step=0.01, value=23.3, key="axial_left_input"
    )

    submitted = st.form_submit_button("Add visit")

    if submitted:
        # Update session state so next time the form uses the last entered values
        st.session_state.dob = dob
        st.session_state.visit_date = visit_date

        new_rows = pd.DataFrame([
            {
                "Gender": gender,
                "DateOfBirth": dob,
                "Visit": visit_label,
                "VisitDate": visit_date,
                "Age": age_years,
                "Eye": "OD",
                "AxialLength": axial_right,
            },
            {
                "Gender": gender,
                "DateOfBirth": dob,
                "Visit": visit_label,
                "VisitDate": visit_date,
                "Age": age_years,
                "Eye": "OS",
                "AxialLength": axial_left,
            },
        ])
        st.session_state.visits = pd.concat(
            [st.session_state.visits, new_rows],
            ignore_index=True
        )



# Show only visits for the currently selected gender
visits_current_gender = st.session_state.visits[
    st.session_state.visits["Gender"] == gender
].copy()




# -----------------------------
# 5. SHOW STORED VISITS
# -----------------------------
st.subheader(f"Stored visits for this patient ({gender})")
if visits_current_gender.empty:
    st.info("No visits added yet for this gender. Use the form in the sidebar to add visits.")
else:
    st.dataframe(visits_current_gender)


# -----------------------------
# 6. PLOT GROWTH CURVE + VISITS
# -----------------------------
base = alt.Chart(df_long).mark_line(size=2).encode(
    x=alt.X("Age:Q", title="Age (years)"),
    y=alt.Y(
        "AxialLength:Q",
        title="Axial length (mm)",
        scale=alt.Scale(domain=[21, 28])
    ),
    color=alt.Color(
        "Percentile:N",
        title="Percentile",
        scale=alt.Scale(domain=percentile_order),  # force legend order
    ),
    tooltip=["Age", "Percentile", "AxialLength"]
).properties(
    width=800,
    height=500,
    title=f"Axial Length Growth Curves ({gender}) with Visits"
)


if not visits_current_gender.empty:
    # One chart for visits: line + points
    visits_chart = alt.Chart(visits_current_gender).mark_line(
        point=alt.OverlayMarkDef(size=120)
    ).encode(
        x=alt.X("Age:Q", title="Age at visit (years)"),
        y="AxialLength:Q",
        color=alt.Color("Eye:N", title="Eye (OD/OS)"),
        tooltip=[
            "Gender",
            "DateOfBirth",
            "Visit",
            "VisitDate",
            "Eye",
            "Age",
            "AxialLength",
        ],
        detail="Eye:N",
    )


    # Independent color scale for curves vs visits
    chart = (base + visits_chart).resolve_scale(color="independent")
else:
    chart = base


st.altair_chart(chart, use_container_width=True)


# -----------------------------
# 7. APPROXIMATE PERCENTILE
# -----------------------------
# 7. APPROXIMATE PERCENTILE
# -----------------------------
if not visits_current_gender.empty:
    # Get the last visit for each eye (OD and OS)
    for eye in ["OD", "OS"]:
        eye_data = visits_current_gender[visits_current_gender["Eye"] == eye]
        if not eye_data.empty:
            last = eye_data.iloc[-1]
            nearest_age = df.iloc[(df["Age"] - last["Age"]).abs().argsort()[0]]["Age"]
            row = df[df["Age"] == nearest_age].iloc[0]
            percentile_cols = [c for c in df.columns if c != "Age"]
            differences = {p: abs(row[p] - last["AxialLength"]) for p in percentile_cols}
            approx_percentile = min(differences, key=differences.get)
            approx_value = row[approx_percentile]

            st.markdown(f"### Approximate percentile (for last added {eye} eye)")
            st.write(
                f"Gender **{last['Gender']}**, DOB **{last['DateOfBirth']}**, "
                f"visit **{last['Visit']}** on **{last['VisitDate']}**, eye **{last['Eye']}**: "
                f"age **{last['Age']:.2f}** years (nearest table age {nearest_age:.0f}), "
                f"axial length **{last['AxialLength']:.2f} mm** ≈ **{approx_percentile}th percentile** "
                f"(curve value {approx_value:.2f} mm)."
            )
