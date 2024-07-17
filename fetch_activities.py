import requests
import django
import os

# this python file was used to make api requests to strava and gather all the data from my own activities
# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from fitness_web.models import Activity

# Clear all existing activities
deleted_count, _ = Activity.objects.all().delete()
print(f"Cleared {deleted_count} existing activities.")

# access token
access_token = '6e65bc7eabba54d55d5a12a2a90c34d75d963bad'
activities_url = "https://www.strava.com/api/v3/athlete/activities"

header = {'Authorization': 'Bearer ' + access_token}
per_page = 200
page = 1

all_activities = []

while True:
    param = {'per_page': per_page, 'page': page}
    response = requests.get(activities_url, headers=header, params=param)

    if response.status_code != 200:
        print(f"Error: {response.json()}")
        break

    activities = response.json()
    if not activities:
        break

    all_activities.extend(activities)
    page += 1

#  list for activity data
activity_data = []

for activity in all_activities:
    distance_miles = round((activity.get('distance', 0) / 1609.34), 2)
    moving_time_seconds = activity.get('moving_time', 0)
    # Convert seconds to minutes and round to 2 decimal places
    moving_time_minutes = round(moving_time_seconds / 60.0, 2)

    # print to verify conversion
    print(f"Activity: {activity.get('type')}, Moving Time (seconds): {moving_time_seconds}, Moving Time (minutes): {moving_time_minutes}")

    # Collect data in a dictionary
    activity_data.append({
        'activity_type': activity.get('type'),
        'distance_miles': distance_miles,
        'moving_time': moving_time_minutes,
        'average_heartrate': activity.get('average_heartrate', 0),
        'max_heartrate': activity.get('max_heartrate', 0)
    })

# creating each activity object
Activity.objects.bulk_create([Activity(**data) for data in activity_data])

print(f"Stored {len(all_activities)} activities in the database.")
