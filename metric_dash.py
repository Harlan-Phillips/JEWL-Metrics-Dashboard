import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plot_utils import add_distances, get_base64_of_bin_file, generate_pdf, \
interpolate_y_values, calculate_avg_difference_interpolated, fspl, two_ray_model, \
calculate_avg_diff_models

# Configuring website title, layout, and icon
st.set_page_config(page_title='JEWL Testing Metrics', page_icon='JEWL-logo.png', layout='wide', initial_sidebar_state='auto')

# Custom background using css styling
def set_background_image(url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(25, 24, 41, 0.85), rgba(25, 24, 41, 0.85)), url({url});
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
set_background_image('https://i.imgur.com/oEalvaN.png')

# Columns for horizontal elements
col1, col2 = st.columns([1, 7], gap="small")

# Logo in the first column
with col1:
    st.image("JEWL-logo.png", width=150)

# Title in the second column
with col2:
    st.markdown(
        """
        <div style="display: flex; align-items: center;">
            <h1 style="margin-left: 20px;">JSC Exploration Wireless Laboratory (JEWL) Metrics Dashboard</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

# Dictionary to keep track of the file names
dfs = {}

# Upload one or two CSV files
uploaded_files = st.file_uploader("Upload one or two CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    # Iterate through the uploaded files
    for idx, file in enumerate(uploaded_files):
        original_name = file.name
        # Ask the user to input a name for each file
        custom_name = st.text_input(f"Enter a name for file {original_name}", value=f"File_{original_name}")
        
        # Read the file into a dataframe
        df = pd.read_csv(file)
        # Calculate distances
        df = add_distances(df)  
        # Strip df of any empty columns
        df = df.dropna(axis=1, how='all')
        # Store df in the dictionary with the file name
        dfs[custom_name] = df
        
        # Display a preview of the df
        st.write(f"**{custom_name}** Preview:")
        st.write(df.head())

    # If at least one file has been uploaded
    if len(dfs) > 0:
        # Use the first file for metric options
        first_file_name = list(dfs.keys())[0]
        first_df = dfs[first_file_name]
        
        # Get metric options from the first file's columns
        metric_options = first_df.columns.tolist()

        st.sidebar.header("Test Metrics")
        x_metric = st.sidebar.selectbox("X-Axis", metric_options)
        y_metric = st.sidebar.selectbox("Y-Axis", metric_options)

        # Setting reference point for the distance
        if x_metric == "Distance (Meters)":        
            tower = st.sidebar.checkbox("Reference point: Tower", value=True)
            if not tower:
                first_df = add_distances(first_df, "Tower End")
            else:
                first_df = add_distances(first_df) 


        # Plot for the first file
        st.subheader(f"{x_metric} vs {y_metric} (from {first_file_name})")
        fig1 = px.scatter(first_df, x=x_metric, y=y_metric, title=f'{x_metric} vs {y_metric} ({first_file_name})')
        if x_metric == "Distance (Meters)" and y_metric == "WIFI_RSSI_DBM":
            st.sidebar.header("Model Parameters")
            frequency = st.sidebar.number_input("Frequency (Hz)", value=5.18 * 10**9, format="%e")
            offset = st.sidebar.number_input("Offset (dB)", value=30)
            ht = st.sidebar.number_input("Height of Transmitter (meters)", value=8)
            hr = st.sidebar.number_input("Height of Receiver (meters)", value=2)
            fspl_values = -fspl(first_df[x_metric], frequency=frequency, offset=offset)  # Calculate FSPL values
            fig1.add_trace(go.Scatter(x=first_df[x_metric], y=fspl_values, mode='lines', name='FSPL Prediction', line=dict(dash='dash', color='red')))
            two_ray_values = two_ray_model(first_df[x_metric], ht, hr, offset)  # Calculate two ray values
            fig1.add_trace(go.Scatter(x=first_df[x_metric], y=two_ray_values, mode='lines', name='Two-Ray Ground Reflection Prediction', line=dict(dash='dash', color='green')))
            avg_diff_fspl, percent_fade_fspl = calculate_avg_diff_models(first_df, fspl_values, x_metric, y_metric)
            avg_diff_two_ray, percent_fade_two_ray = calculate_avg_diff_models(first_df, two_ray_values, x_metric, y_metric)
        st.plotly_chart(fig1)
        if x_metric == "Distance (Meters)" and y_metric == "WIFI_RSSI_DBM":
            st.write(f"Average Difference between Actual and FSPL: {avg_diff_fspl:.2f} dB")
            st.write(f"Percent Fade Rate (FSPL): {percent_fade_fspl:.2f}%")
            st.write(f"Average Difference between Actual and Two-Ray: {avg_diff_two_ray:.2f} dB")
            st.write(f"Percent Fade Rate (Two-Ray): {percent_fade_two_ray:.2f}%")

        # Generate PDF for presentations for only one plot
        if len(dfs) == 1:
            z_metric = st.sidebar.selectbox("Z-Axis (Color Map)", ["None"] + metric_options)
            if z_metric != "None":
                fig1 = px.scatter(first_df, x=x_metric, y=y_metric, color=first_df[z_metric], title=f'{x_metric} vs {y_metric} colored by {z_metric}', labels={z_metric: z_metric})
                st.plotly_chart(fig1)
                if st.button('Generate PDF'):
                    pdf_data = generate_pdf(first_df, None, x_metric, y_metric, first_file_name, None, z_metric)
                    
                    # Provide a download link for the generated PDF
                    st.download_button(
                        label="Download PDF",
                        data=pdf_data,
                        file_name="plot.pdf",
                        mime="application/pdf"
                    )
           
            else:
                if st.button('Generate PDF'):
                    pdf_data = generate_pdf(first_df, None, x_metric, y_metric, first_file_name, None)
                    
                    # Provide a download link for the generated PDF
                    st.download_button(
                        label="Download PDF",
                        data=pdf_data,
                        file_name="plot.pdf",
                        mime="application/pdf"
                    )

    # If more than one file is uploaded, allow for overplotting
    if len(dfs) > 1:
        # Get second file name from dictionary
        second_file_name = list(dfs.keys())[1]
        second_df = dfs[second_file_name]

        st.subheader(f"{x_metric} vs {y_metric} (from {second_file_name})")
        fig2 = px.scatter(second_df, x=x_metric, y=y_metric, title=f'{x_metric} vs {y_metric} ({second_file_name})')
        if x_metric == "Distance (Meters)" and y_metric == "WIFI_RSSI_DBM":
            # FSPL and Two-Ray for the second plot
            fspl_values_2 = -fspl(second_df[x_metric], frequency=frequency, offset=offset)  # Calculate FSPL for second file
            two_ray_values_2 = two_ray_model(second_df[x_metric], ht, hr, offset)  # Calculate Two-Ray for second file
            fig2.add_trace(go.Scatter(x=second_df[x_metric], y=fspl_values_2, mode='lines', name='FSPL Prediction (Second)', line=dict(dash='dash', color='red')))
            fig2.add_trace(go.Scatter(x=second_df[x_metric], y=two_ray_values_2, mode='lines', name='Two-Ray Prediction (Second)', line=dict(dash='dash', color='green')))
            avg_diff_fspl_2, percent_fade_fspl_2 = calculate_avg_diff_models(second_df, fspl_values_2, x_metric, y_metric)
            avg_diff_two_ray_2, percent_fade_two_ray_2 = calculate_avg_diff_models(second_df, two_ray_values_2, x_metric, y_metric)
        st.plotly_chart(fig2)
        if x_metric == "Distance (Meters)" and y_metric == "WIFI_RSSI_DBM":
            st.write(f"Average Difference between Actual and FSPL: {avg_diff_fspl_2:.2f} dB")
            st.write(f"Percent Fade Rate (FSPL): {percent_fade_fspl_2:.2f}%")
            st.write(f"Average Difference between Actual and Two-Ray: {avg_diff_two_ray_2:.2f} dB")
            st.write(f"Percent Fade Rate (Two-Ray): {percent_fade_two_ray_2:.2f}%")

        st.subheader(f"{first_file_name} vs. {second_file_name}")
        # Initialize the figure using Plotly's graph_objects
        fig_combined = go.Figure()
        # Add scatter for the first file
        fig_combined.add_trace(go.Scatter(x=first_df[x_metric], y=first_df[y_metric], mode='markers', name=first_file_name))
        # Add scatter for the second file
        fig_combined.add_trace(go.Scatter(x=second_df[x_metric], y=second_df[y_metric], mode='markers', name=second_file_name))
        # Set title and axis labels
        fig_combined.update_layout(
            title=f"{x_metric} vs {y_metric}",
            xaxis_title=x_metric,
            yaxis_title=y_metric
        )
        
        # Add FSPL and Two-Ray for the overplotting graph
        if x_metric == "Distance (Meters)" and y_metric == "WIFI_RSSI_DBM":
            # FSPL and Two-Ray for the second plot
            fig_combined.add_trace(go.Scatter(x=second_df[x_metric], y=fspl_values_2, mode='lines', name='FSPL Prediction (Second)', line=dict(dash='dash', color='red')))
            fig_combined.add_trace(go.Scatter(x=second_df[x_metric], y=two_ray_values_2, mode='lines', name='Two-Ray Prediction (Second)', line=dict(dash='dot', color='green')))

        # Show the combined plot
        st.plotly_chart(fig_combined)

        # Option to display average difference for Signal Strength
        if y_metric == "WIFI_RSSI_DBM":
        # Display average difference
            avg_diff, common_x, y1_interp, y2_interp = calculate_avg_difference_interpolated(first_df, second_df, x_metric, y_metric)
            avg_diff_fspl = calculate_avg_diff_models(first_df, fspl_values, x_metric, y_metric)
            avg_diff_two_ray = calculate_avg_diff_models(first_df, two_ray_values, x_metric, y_metric)
        
            # Display the average difference
            st.write(f"Average Difference between RSSI values: {avg_diff:.2f} dB")
         
        # Generate PDF for presentations
        if st.button('Generate PDF'):
            pdf_data = generate_pdf(first_df, second_df, x_metric, y_metric, first_file_name, second_file_name)
            
            # Provide a download link for the generated PDF
            st.download_button(
                label="Download PDF",
                data=pdf_data,
                file_name="plot.pdf",
                mime="application/pdf"
            )