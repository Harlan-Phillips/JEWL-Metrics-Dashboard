from geopy.distance import geodesic
import numpy as np
import pandas as pd
import base64
import matplotlib.pyplot as plt
import scienceplots
from io import BytesIO

# Constants
c = 3 * 10**8  # Speed of light in m/s
f = 5.18 * 10**9  # Default frequency for 5 GHz

# Free Space Path Loss (FSPL) model
def fspl(distance, frequency=f, c=c, offset=30):
    distance = distance[distance > 0] # Avoiding log(0)
    return (20 * np.log10(distance) + 20 * np.log10(frequency) + 20 * np.log10(4 * np.pi / c)) - offset

# Two-Ray Ground Reflection model
def two_ray_model(distance, ht=8, hr=2, offset=30):
    min_distance = 1  # Avoiding extreme curve
    distance = np.where(distance < min_distance, min_distance, distance)
    return offset + 10 * np.log10((ht ** 2 * hr ** 2) / (distance ** 4)) 

# Function to interpolate y values for matching x values
def interpolate_y_values(df, common_x, x_metric, y_metric):
    return np.interp(common_x, df[x_metric], df[y_metric])

# Function to calculate the average difference between two sets of y values
def calculate_avg_difference_interpolated(df1, df2, x_metric, y_metric):
    # Find the overlapping x values
    x_min = max(min(df1[x_metric]), min(df2[x_metric]))
    x_max = min(max(df1[x_metric]), max(df2[x_metric]))
    
    # Generate common x values 
    common_x = np.linspace(x_min, x_max, num=100)  # 100 values between the min and max
    
    # Interpolate y values for both dataframes at the common x values
    y1_interp = interpolate_y_values(df1, common_x, x_metric, y_metric)
    y2_interp = interpolate_y_values(df2, common_x, x_metric, y_metric)
    
    # Calculate the average difference between the two sets of y values
    avg_diff = np.mean(np.abs(y1_interp - y2_interp))
    
    return avg_diff, common_x, y1_interp, y2_interp

def calculate_avg_diff_models(df, model_values, x_metric, y_metric):
    # Ensure only valid non-zero distances are used
    valid_rows = df[x_metric] > 0
    x_values = df[valid_rows][x_metric]
    actual_y_values = df[valid_rows][y_metric]
    # If the y values are not the same interpolate based on x values
    if len(actual_y_values) != len(model_values):
        model_values = np.interp(x_values, x_values, model_values[:len(x_values)]) 
    # Calculate absolute differences between actual and model values
    differences = np.abs(actual_y_values - model_values)
    
    # Calculate the average difference
    avg_diff = np.mean(differences)
    
    # Caculate the mean of the data points
    actual_mean = np.mean(np.abs(actual_y_values))
    
    # Calculate the percent fade rate
    percent_fade_rate = (avg_diff / actual_mean) * 100

    return avg_diff, percent_fade_rate

# Getting distance in meters from lat and lon
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).meters

# Calculating distances from gps data and appending to the dataframe
def add_distances(df, tower_pos="Tower Start"):
    # Get the starting point (tower location)
    # To change -> Set start_lat, start_lon based on the tower pos, three options can be selected the tower (first point), the end tower/ max distance, and manual, any set distance from the tower less than max
    start_lat, start_lon = df.iloc[0]['GPS_LAT_DEG'], df.iloc[0]['GPS_LON_DEG']
    
    # Calculate the distance from the starting point (tower) for each point
    distances_from_tower = []
    for i in range(len(df)):
        lat, lon = df.iloc[i]['GPS_LAT_DEG'], df.iloc[i]['GPS_LON_DEG']
        distance_from_tower = calculate_distance(start_lat, start_lon, lat, lon)
        distances_from_tower.append(distance_from_tower)

    # Add the distance from the starting point to the dataframe
    df['Distance (Meters)'] = distances_from_tower

    # Switching distance reference point
    if tower_pos == "Tower End":
        # Flip the distances so that the farthest point becomes the starting point (max distance becomes 0)
        max_distance = df['Distance (Meters)'].max()
        df['Distance (Meters)'] = max_distance - df['Distance (Meters)']
        return df

    else:
        return df # Tower start

# Convert webp to base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Generating plot using matplotlib for presentations in PDF format
def generate_pdf(df1, df2, x_metric, y_metric, df1_name="file1", df2_name="file2", z_metric=None):
    plt.rcParams['text.usetex'] = False
    plt.style.use(['science','no-latex'])
    plt.figure(figsize=(10, 6))
    
    # Plot the two dataframes
    # If z_metric is provided, use it for the color map
    if z_metric is not None and z_metric != "None":
        scatter = plt.scatter(df1[x_metric], df1[y_metric], c=df1[z_metric], cmap='viridis', label=df1_name)
        plt.colorbar(scatter, label=f'{z_metric}')  # Add colorbar for the Z metric
    else:
        plt.plot(df1[x_metric], df1[y_metric], marker='o', markersize=3, label=df1_name, color='crimson')
    if df2 is not None:
        plt.plot(df2[x_metric], df2[y_metric], marker='o', markersize=3, label=df2_name, color='steelblue')
    
    plt.xlabel(f'{x_metric}')
    plt.ylabel(f'{y_metric}')
    plt.title(f'{x_metric} vs {y_metric}')
    plt.grid(True)
    plt.legend()

    # Save the plot as a PDF using BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format='pdf')
    buf.seek(0)
    return buf