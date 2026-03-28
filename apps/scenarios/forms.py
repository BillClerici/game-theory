from django import forms
from apps.lookup.models import LookupValue
from apps.scenarios.models import Player, PlayerPosition, Scenario, ScenarioIssue


class ScenarioForm(forms.ModelForm):
    scenario_type = forms.ModelChoiceField(
        queryset=LookupValue.objects.none(),
        empty_label="Select type...",
        widget=forms.Select(attrs={"class": "browser-default"}),
    )

    class Meta:
        model = Scenario
        fields = ["title", "description", "scenario_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type_parent = LookupValue.objects.filter(
            parent__isnull=True, code="SCENARIO_TYPE",
        ).first()
        if type_parent:
            self.fields["scenario_type"].queryset = LookupValue.objects.filter(
                parent=type_parent,
            )


class ScenarioIssueForm(forms.ModelForm):
    class Meta:
        model = ScenarioIssue
        fields = [
            "title",
            "description",
            "scale_min_label",
            "scale_max_label",
            "status_quo_position",
            "sort_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status_quo_position"].widget.attrs.update({
            "type": "number", "min": "0", "max": "100",
        })


class PlayerForm(forms.ModelForm):
    player_type = forms.ModelChoiceField(
        queryset=LookupValue.objects.none(),
        empty_label="Select type...",
        widget=forms.Select(attrs={"class": "browser-default"}),
    )

    class Meta:
        model = Player
        fields = ["name", "description", "player_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type_parent = LookupValue.objects.filter(
            parent__isnull=True, code="PLAYER_TYPE",
        ).first()
        if type_parent:
            self.fields["player_type"].queryset = LookupValue.objects.filter(
                parent=type_parent,
            )


class PlayerPositionForm(forms.ModelForm):
    risk_profile = forms.ModelChoiceField(
        queryset=LookupValue.objects.none(),
        empty_label="Select risk profile...",
        widget=forms.Select(attrs={"class": "browser-default"}),
    )

    class Meta:
        model = PlayerPosition
        fields = ["position", "capability", "salience", "flexibility", "risk_profile"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        risk_parent = LookupValue.objects.filter(
            parent__isnull=True, code="RISK_PROFILE",
        ).first()
        if risk_parent:
            self.fields["risk_profile"].queryset = LookupValue.objects.filter(
                parent=risk_parent,
            )
        for field_name in ["position", "capability", "salience", "flexibility"]:
            self.fields[field_name].widget.attrs.update({
                "type": "number", "min": "0", "max": "100", "step": "0.01",
            })
