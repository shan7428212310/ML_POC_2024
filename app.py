from flask import Flask, render_template_string, request
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta
import plotly.express as px
import warnings
import folium
from folium import plugins

# Initialize Flask app
app = Flask(__name__)

# Ignore all warnings
warnings.filterwarnings("ignore")

# Load dataset
df = pd.read_csv(r'uber_data.csv')
rides = df

# Categories reclassification
product_mapping = {'UberX':'UberX','uberX':'UberX','uberX VIP':'UberX','VIP':'UberX','POOL':'Pool','POOL: MATCHED':'Pool','UberBLACK': 'Black',
                   'uberx':'UberX','uberPOOL':'Pool','uberPOOL: MATCHED':'Pool','Pool: MATCHED':'Pool'}
rides['Product Type'].replace(product_mapping, inplace=True)
rides = rides[rides['Product Type']!='UberEATS Marketplace']

# Convert date columns to datetime
def date_convertion(df, cols):
    for col in cols:
        df[col] = df[col].apply(lambda x: x.replace(' +0000 UTC', ''))
        df[col] = pd.to_datetime(df[col])
    return df

# Apply the date conversion
rides = date_convertion(rides, ['Request Time', 'Begin Trip Time', 'Dropoff Time'])
rides['year'] = rides['Request Time'].map(lambda x: datetime.strftime(x,"%Y"))
rides['month'] = rides['Request Time'].map(lambda x: datetime.strftime(x,"%b"))
rides['weekday'] = rides['Request Time'].map(lambda x: datetime.strftime(x,"%a"))
rides['time'] = rides['Request Time'].map(lambda x: datetime.strftime(x,"%H:%M"))

rides['distance_km'] = round(rides['Distance (miles)']*1.60934,2)
rides['amount_km'] = round(rides['Fare Amount']/rides.distance_km,2)

rides['request_lead_time'] = rides['Begin Trip Time'] - rides['Request Time']
rides['request_lead_time'] = rides['request_lead_time'].apply(lambda x: round(x.total_seconds()/60,1))

rides['trip_duration'] = rides['Dropoff Time'] - rides['Begin Trip Time']
rides['trip_duration'] = rides['trip_duration'].apply(lambda x: round(x.total_seconds()/60,1))

# Filter out canceled rides
rides.loc[(rides['Trip or Order Status'] == 'CANCELED') | (rides['Trip or Order Status'] == 'DRIVER_CANCELED'),'request_lead_time']=np.nan
rides.loc[(rides['Trip or Order Status'] == 'CANCELED') | (rides['Trip or Order Status'] == 'DRIVER_CANCELED'),'amount_km']=np.nan
rides.loc[(rides['Trip or Order Status'] == 'CANCELED') | (rides['Trip or Order Status'] == 'DRIVER_CANCELED'),['begin_time','dropoff_time']]= np.nan

completed_rides = rides[(rides['Trip or Order Status']!='CANCELED')&(rides['Trip or Order Status']!='DRIVER_CANCELED')]
completed_rides = completed_rides.dropna(subset=['Dropoff Lat', 'Dropoff Lng'])

# Function to generate analysis results based on user input
def data_analysis_choice(choice):
    result = ""
    if choice == 'a':
        result += f"Total trips: {completed_rides['Trip or Order Status'].count()}\n"
        result += str(completed_rides.year.value_counts().sort_index(ascending=True))
    elif choice == 'b':
        result += f"Total trips: {rides['Trip or Order Status'].count()}\n"
        result += str(round(rides['Trip or Order Status'].value_counts()/rides['Trip or Order Status'].size*100,1))
    elif choice == 'c':
        coord = completed_rides[['Dropoff Lat', 'Dropoff Lng']].values.tolist()
        heatmap = folium.Map(location=[-23.5489, -46.6388], zoom_start=12)
        heatmap.add_child(plugins.HeatMap(coord, radius=10))
        result = "Heatmap created for dropoff locations."
    elif choice == 'd':
        pt_rides = pd.Series(completed_rides['Product Type'].value_counts().sort_index(ascending=False))
        df = pd.DataFrame(pt_rides)
        df['%'] = (completed_rides['Product Type'].value_counts().sort_index(ascending=False)/completed_rides['Product Type'].size*100).round(1)
        df.rename(columns={'Product Type':'Total Rides'}, inplace=True)
        result = str(df)
    elif choice == 'e':
        result += f"Avg. fare: {round(completed_rides['Fare Amount'].mean(),1)} BRL\n"
        result += f"Avg. distance: {round(completed_rides['distance_km'].mean(),1)} km\n"
        result += f"Avg. fare/km: {round(completed_rides['Fare Amount'].sum()/completed_rides['distance_km'].sum(),1)} BRL/km\n"
        result += f"Avg. time spent on trips: {round(completed_rides['trip_duration'].mean(),1)} minutes\n"
        result += f"Total fare amount: {round(completed_rides['Fare Amount'].sum(),1)} BRL\n"
        result += f"Total distance: {round(completed_rides['distance_km'].sum(),1)} km\n"
        result += f"Total time spent on trips: {round(completed_rides['trip_duration'].sum()/60,1)} hours"
    elif choice == 'f':
        amount_table = completed_rides.pivot_table(values='Fare Amount', aggfunc='sum', columns='weekday', index='year').round(1)
        distance_table = completed_rides.pivot_table(values='distance_km', aggfunc='sum', columns='weekday', index='year').round(1)
        result_table = (amount_table / distance_table).round(1)
        result = str(result_table)
    elif choice == 'g':
        max_distance_ride = completed_rides[completed_rides['distance_km'] == completed_rides['distance_km'].max()]
        min_distance_ride = completed_rides[completed_rides['distance_km'] == completed_rides['distance_km'].min()]
        rides_distance = pd.concat([max_distance_ride, min_distance_ride])
        result = str(rides_distance)
    elif choice == 'h':
        result += f"Avg. lead time before requesting a trip: {round(completed_rides['request_lead_time'].mean(),1)} minutes"
    else:
        result = "Invalid Choice! Please Select again."
    return result

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        choice = request.form['choice']
        result = data_analysis_choice(choice)
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Uber Data Analysis</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
            }
            .result {
                margin-top: 20px;
                padding: 10px;
                background-color: #f4f4f4;
                border-radius: 8px;
            }
            select, button {
                padding: 10px;
                margin: 10px;
                font-size: 16px;
            }
        </style>
    </head>
    <body>
        <h1>Uber Data Analysis</h1>
        <form method="POST">
            <label for="choice">Select Analysis Query:</label>
            <select name="choice" id="choice">
                <option value="a">Total trips in the past</option>
                <option value="b">Completed or canceled trips</option>
                <option value="c">Where did most of the layoffs take place?</option>
                <option value="d">Most selected product type</option>
                <option value="e">Average fare, distance, and time spent on trips</option>
                <option value="f">Highest number of rides per kilometer</option>
                <option value="g">Longest / shortest and most expensive / cheapest ride</option>
                <option value="h">Average lead time before requesting a trip</option>
            </select>
            <button type="submit">Submit</button>
        </form>

        {% if result %}
            <div class="result">
                <h3>Analysis Result:</h3>
                <pre>{{ result }}</pre>
            </div>
        {% endif %}
    </body>
    </html>
    """, result=result)

if __name__ == '__main__':
    app.run(debug=True)
