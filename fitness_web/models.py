from django.db import models

# Create your models here.

class Activity(models.Model):
    activity_type = models.CharField(max_length=20)
    distance_miles = models.FloatField()
    moving_time = models.FloatField()  # in seconds
    average_heartrate = models.FloatField(null=True, blank=True)
    max_heartrate = models.FloatField(null=True, blank=True)
    calories = models.FloatField(default=0)
    type_effort = models.CharField(max_length=20, default='')

    def __str__(self):
        return f"{self.activity_type} - {self.distance_miles} miles"