from django import forms
from django.db.models import Q
from django.forms import BaseFormSet

from storage_module.models import BoxPosition, DimBox, DimFacility, DimFreezer, DimRack, \
    DimShelf


class MoveSampleForm(forms.Form):
    box = forms.ModelChoiceField(queryset=DimBox.objects.all(),
                                 widget=forms.Select(attrs={"class": "select2"}))
    x_position = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}))
    y_position = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super(MoveSampleForm, self).__init__(*args, **kwargs)
        self.fields['box'].label_from_instance = lambda obj: "{}".format(obj.box_name)


class MoveBoxForm(forms.Form):
    freezer = forms.ModelChoiceField(
        queryset=DimFreezer.objects.all(),
        widget=forms.Select(attrs={"class": "select2"}),
    )
    shelf = forms.ModelChoiceField(queryset=DimShelf.objects.all(),
                                   required=False,
                                   widget=forms.Select(attrs={"class": "select2"}))
    rack = forms.ModelChoiceField(queryset=DimRack.objects.all(),
                                  required=False,
                                  widget=forms.Select(attrs={"class": "select2"}))

    def __init__(self, *args, **kwargs):
        super(MoveBoxForm, self).__init__(*args, **kwargs)
        self.fields['rack'].label_from_instance = lambda obj: "{}".format(obj.rack_name)
        self.fields['shelf'].label_from_instance = lambda obj: "{}".format(obj.shelf_name)
        self.fields['freezer'].label_from_instance = lambda obj: "{}".format(
            obj.freezer_name)


class FacilityForm(forms.Form):
    def __init__(self, *args, sample_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample_ids = sample_ids

    facility = forms.ModelChoiceField(queryset=DimFacility.objects.all())


class FreezerForm(forms.Form):
    def __init__(self, *args, sample_ids=None, **kwargs):
        facility = kwargs.pop('facility', None)
        super().__init__(*args, **kwargs)
        self.sample_ids = sample_ids
        if facility is not None:
            self.fields['freezer'].queryset = facility.dimfreezer_set.all()

    freezer = forms.ModelChoiceField(queryset=DimFreezer.objects.none())


class BoxForm(forms.Form):
    def __init__(self, *args, sample_ids=None, **kwargs):
        freezer = kwargs.pop('freezer', None)
        super().__init__(*args, **kwargs)
        self.sample_ids = sample_ids
        if freezer is not None:
            all_boxes = DimBox.objects.filter(
                Q(shelf__freezer=freezer) |
                Q(rack__shelf__freezer=freezer) |
                Q(rack__freezer=freezer) |
                Q(freezer=freezer)
            )
            self.fields['box'].queryset = all_boxes

    box = forms.ModelChoiceField(queryset=DimBox.objects.none(),
                                 required=False, )


class SampleMoveForm(forms.Form):
    new_x_position = forms.ChoiceField(
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7'),
                 (9, '9')],
        widget=forms.Select(attrs={"class": "form-control form-control-sm select2"}),
        required=False
    )
    new_y_position = forms.ChoiceField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F'),
                 ('G', 'G'), ('H', 'H'), ('I', 'I'), ('J', 'J')],
        widget=forms.Select(attrs={"class": "form-control form-control-sm select2"}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.box = kwargs.pop('box', None)
        sample_ids = kwargs.pop('sample_ids', None)
        super().__init__(*args, **kwargs)
