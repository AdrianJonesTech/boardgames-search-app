from django import forms
from .models import Mechanic

class SearchForm(forms.Form):
    min_players = forms.IntegerField(min_value=1, required=False, label='Min Players')
    max_players = forms.IntegerField(min_value=1, required=False, label='Max Players')
    min_playing_time = forms.IntegerField(min_value=0, required=False, label='Min Playing Time (min)')
    max_playing_time = forms.IntegerField(min_value=0, required=False, label='Max Playing Time (min)')
    min_weight = forms.FloatField(min_value=0, max_value=5, required=False, label='Min Weight')
    max_weight = forms.FloatField(min_value=0, max_value=5, required=False, label='Max Weight')
    min_rating = forms.FloatField(min_value=0, max_value=10, required=False, label='Min Rating')
    max_rating = forms.FloatField(min_value=0, max_value=10, required=False, label='Max Rating')

    def _mechanics_queryset(self):
        qs = Mechanic.objects.filter(is_common=True).order_by('name')
        if qs.exists():
            return qs
        return Mechanic.objects.all().order_by('name')

    mechanics = forms.ModelMultipleChoiceField(
        queryset=Mechanic.objects.none(),  # replaced in __init__ to allow runtime check
        required=False,
        label='Mechanisms',
        widget=forms.SelectMultiple(attrs={'size': 10}),
        help_text='Hold Ctrl/Cmd to select multiple.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mechanics'].queryset = self._mechanics_queryset()
