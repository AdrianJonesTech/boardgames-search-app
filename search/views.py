from django.shortcuts import render
from django.db.models import Q
from django.http import HttpResponse
from .forms import SearchForm
from .models import Game

def index(request):
    form = SearchForm(request.GET if request.method == 'GET' else {})  # Use GET for consistency
    games = []
    if request.GET:  # Trigger search on any GET params
        if form.is_valid():
            cleaned = form.cleaned_data
            games = Game.objects.all()

            # Player count
            if cleaned['min_players']:
                games = games.filter(min_players__gte=cleaned['min_players'])
            if cleaned['max_players']:
                games = games.filter(max_players__lte=cleaned['max_players'])

            # Playing time
            if cleaned['min_playing_time']:
                games = games.filter(playing_time__gte=cleaned['min_playing_time'])
            if cleaned['max_playing_time']:
                games = games.filter(playing_time__lte=cleaned['max_playing_time'])

            # Weight
            if cleaned['min_weight']:
                games = games.filter(weight__gte=cleaned['min_weight'])
            if cleaned['max_weight']:
                games = games.filter(weight__lte=cleaned['max_weight'])

            # Rating
            if cleaned['min_rating']:
                games = games.filter(rating__gte=cleaned['min_rating'])
            if cleaned['max_rating']:
                games = games.filter(rating__lte=cleaned['max_rating'])

            # Mechanics
            if cleaned['mechanics']:
                games = games.filter(mechanics__in=cleaned['mechanics']).distinct()

            # Serialize
            games_list = []
            for game in games:
                games_list.append({
                    'id': game.bgg_id,
                    'name': game.name,
                    'year': game.year,
                    'min_players': game.min_players,
                    'max_players': game.max_players,
                    'playing_time': game.playing_time,
                    'weight': game.weight,
                    'rating': game.rating,
                    'thumbnail': game.thumbnail,
                    'description': game.description[:200] + '...' if game.description and len(game.description) > 200 else game.description,
                })
            games = games_list

    return render(request, 'search/index.html', {'form': form, 'games': games})

def search_partial(request):
    # Same logic, but return only partial HTML (no full page)
    form = SearchForm(request.GET)
    games = []
    if form.is_valid():
        cleaned = form.cleaned_data
        games = Game.objects.all()

        # Player count
        if cleaned['min_players']:
            games = games.filter(min_players__gte=cleaned['min_players'])
        if cleaned['max_players']:
            games = games.filter(max_players__lte=cleaned['max_players'])

        # Playing time
        if cleaned['min_playing_time']:
            games = games.filter(playing_time__gte=cleaned['min_playing_time'])
        if cleaned['max_playing_time']:
            games = games.filter(playing_time__lte=cleaned['max_playing_time'])

        # Weight
        if cleaned['min_weight']:
            games = games.filter(weight__gte=cleaned['min_weight'])
        if cleaned['max_weight']:
            games = games.filter(weight__lte=cleaned['max_weight'])

        # Rating
        if cleaned['min_rating']:
            games = games.filter(rating__gte=cleaned['min_rating'])
        if cleaned['max_rating']:
            games = games.filter(rating__lte=cleaned['max_rating'])

        # Mechanics
        if cleaned['mechanics']:
            games = games.filter(mechanics__in=cleaned['mechanics']).distinct()

        # Serialize
        games_list = []
        for game in games:
            games_list.append({
                'id': game.bgg_id,
                'name': game.name,
                'year': game.year,
                'min_players': game.min_players,
                'max_players': game.max_players,
                'playing_time': game.playing_time,
                'weight': game.weight,
                'rating': game.rating,
                'thumbnail': game.thumbnail,
                'description': game.description[:200] + '...' if game.description and len(game.description) > 200 else game.description,
            })
        games = games_list
    return render(request, 'search/partials/results.html', {'games': games})