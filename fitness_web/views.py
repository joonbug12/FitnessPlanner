from django.shortcuts import render
from django.http import HttpResponse
import requests
import os
import django
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from fitness_web.models import Activity

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

client_id = '130185'
client_secret = '2055f2442064ab81990e95202f2797ff61fee706'
redirect_uri = 'http://localhost:8080/callback'


# used to get the access token from the strava api
def callback(request):
    code = request.GET.get('code')
    response = requests.post(
        url='https://www.strava.com/oauth/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
    )
    access_token = response.json().get('access_token')
    return HttpResponse(f"Access Token: {access_token}")


# home page
def home(request):
    return render(request, 'fitness_web/home.html')


# loads the csv file and calls the other functions and runs the result page
def run_model_view(request):
    csv_file_path = '/Users/joonsong/Desktop/CS210/FitnessPlanner/activities_updated.csv'
    df = load_data_from_csv(csv_file_path)
    if df is not None:
        model = train_model(df)
        if model is not None:
            daily_plan = create_daily_plan()
            predictions = predict(model, daily_plan)
            if predictions:
                return render(request, 'fitness_web/results.html', {'results': predictions})
            else:
                return HttpResponse("Failed to make predictions")
        else:
            return HttpResponse("Failed to make predictions during model training")
    else:
        return HttpResponse("Failed to make predictions while loading data")


# got the data from strava api, stored the activities into the mysql database. Altered and added data.
# exported the data from sql into a csv file, and now this function loads the file to get the data
def load_data_from_csv(csv_file_path):
    try:
        df = pd.read_csv(csv_file_path)
        if df.empty:
            print("No data found in the CSV file.")
            return None
        print("Data loaded successfully from CSV.")
        print(df.head())
        return df
    except Exception as e:
        print(f"Error loading data from CSV: {e}")
        return None


# prepares data for the model
def prepare_data(df):
    try:
        df = df.dropna()
        df['type_effort'] = pd.Categorical(df['type_effort']).codes
        features = df[['distance_miles', 'calories', 'type_effort']]
        target = df['moving_time']
        print("Data prepared successfully.")
        print("Features:\n", features.head())
        print("Target:\n", target.head())
        return features, target
    except Exception as e:
        print(f"Error preparing data: {e}")
        return None, None


# this plan was made by myself based on a schedule I actually want to do over the rest of the summer into the fall
# well I already started but whatever
def create_daily_plan():
    plan = []
    weekly_mileage = [35, 40, 45, 50, 55, 60, 65, 65, 70, 60, 50, 40, 35]
    easy = 'easy'
    hard = 'workout/hard'
    longrun = 'longrun'
    race = 'race'

    for week_num, mileage in enumerate(weekly_mileage, start=1):
        if week_num <= 4:
            types = [easy, easy, easy, easy, easy, longrun, easy]
        elif 5 <= week_num <= 12:
            types = [hard, easy, easy, hard, easy, longrun, easy]
        elif week_num == 13:
            types = [easy, hard, easy, easy, easy, race, easy]
        else:
            print("Invalid week number")
            continue

        # Calculate daily mileage
        # longrun and workouts are recommended to be 20 percent each of weekly mileage
        # longrun and workout take 20% plus the 8 miles of warmups+cooldowns.
        # Divide the rest into 4 equivalent east days... hashtag no days off
        # for weeks 1-4, it would be 80% of weekly mileage divided by 6 assuming 1 long run per week

        long_run_mileage = mileage * 0.2
        workout_day_mileage = 4 + (long_run_mileage / 2)
        easy_day_mileage_post_week4 = (mileage - (long_run_mileage + 2 * workout_day_mileage)) / 4
        easy_day_mileage_pre_week5 = (mileage - long_run_mileage) / 6
        easy_day_mileage_race_week = (mileage - workout_day_mileage - 3.1) / 5

        for day_num in range(7):
            day_of_week = day_num + 1
            if types[day_num] == hard:
                daily_miles = workout_day_mileage
            elif types[day_num] == longrun:
                daily_miles = long_run_mileage
            elif types[day_num] == race:
                daily_miles = 3.1
            else:
                if week_num < 5:
                    daily_miles = easy_day_mileage_pre_week5
                elif week_num == 13:
                    daily_miles = easy_day_mileage_race_week
                else:
                    daily_miles = easy_day_mileage_post_week4

            plan.append({
                'week': week_num,
                'day': day_of_week,
                'distance_miles': daily_miles,
                'calories': round(daily_miles * 110),
                'type_effort': types[day_num]
            })

    daily_plan = pd.DataFrame(plan)
    return daily_plan


# training the model to teach it my methods :p
def train_model(df):
    features, target = prepare_data(df)
    if features is None or target is None:
        return None

    try:
        X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
        model = GradientBoostingRegressor()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print(f"Mean Squared Error: {mse}")
        return model
    except Exception as e:
        print(f"Error training model: {e}")
        return None


# using the model to make a 90 day/13 week training prediction based off the data and daily plan
def predict(model, daily_plan):
    try:
        effort_labels = pd.Categorical(daily_plan['type_effort'])
        daily_plan['type_effort'] = effort_labels.codes

        predicted_times = model.predict(daily_plan[['distance_miles', 'calories', 'type_effort']])
        daily_plan['predicted_moving_time'] = predicted_times

        daily_plan['type_effort'] = daily_plan['type_effort'].map(
            {code: label for code, label in enumerate(effort_labels.categories)})
        results = daily_plan.to_dict(orient='records')
        print("Predictions made successfully.")
        return results
    except Exception as e:
        print(f"Error predicting data: {e}")
        return []
