import streamlit as st

import pandas as pd

# Replace with your actual raw GitHub URL
excel_url = '/workspaces/axial_length/Axial length norm excel (Chinese data).xlsx'

# Read the Excel file directly from GitHub
df = pd.read_excel(excel_url)

# Display the DataFrame in Streamlit
st.title("Excel Data from GitHub")
st.dataframe(df)



