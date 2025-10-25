from django.contrib import admin
from .models import Mechanic, Game

class MechanicInline(admin.TabularInline):
    model = Game.mechanics.through
    extra = 0

@admin.register(Mechanic)
class MechanicAdmin(admin.ModelAdmin):
    list_display = ['name', 'bgg_id', 'mentions_count', 'is_common']
    list_filter = ['is_common']
    search_fields = ['name']

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'rating', 'playing_time', 'weight']
    list_filter = ['year', 'mechanics']
    search_fields = ['name', 'description']
    inlines = [MechanicInline]