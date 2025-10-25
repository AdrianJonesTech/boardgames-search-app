from django.db import models

class Mechanic(models.Model):
    bgg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    mentions_count = models.PositiveIntegerField(default=0)
    is_common = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Game(models.Model):
    bgg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    year = models.PositiveIntegerField(null=True, blank=True)
    min_players = models.PositiveIntegerField(null=True, blank=True)
    max_players = models.PositiveIntegerField(null=True, blank=True)
    playing_time = models.PositiveIntegerField(null=True, blank=True)  # Average
    weight = models.FloatField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)  # Average user rating
    thumbnail = models.URLField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    mechanics = models.ManyToManyField(Mechanic, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-rating']  # Default to highest rated
