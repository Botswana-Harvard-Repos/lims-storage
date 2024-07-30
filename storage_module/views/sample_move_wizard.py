from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from formtools.wizard.views import SessionWizardView

from storage_module.forms import (BoxForm, FacilityForm, FreezerForm, SampleMoveForm)
from storage_module.models import BoxPosition, DimBox, DimSample


class SampleMoveWizard(LoginRequiredMixin, SessionWizardView):
    form_list = [FacilityForm, FreezerForm, BoxForm, SampleMoveForm]
    template_name = 'storage_module/wizard/wizard_form.html'

    def get_form_kwargs(self, step=None):
        kwargs = super(SampleMoveWizard, self).get_form_kwargs(step=step)
        sample_ids = self.request.GET.get('sample_ids', '')
        if sample_ids:
            kwargs.update({'sample_ids': sample_ids.split(',')})
        if step == '1':
            selected_facility = self.get_cleaned_data_for_step('0')['facility']
            kwargs.update({'facility': selected_facility})
        elif step == '2':
            selected_freezer = self.get_cleaned_data_for_step('1')['freezer']
            kwargs.update({'freezer': selected_freezer})
        elif step == '3':
            selected_box = self.get_cleaned_data_for_step('2')['box']
            kwargs.update({'box': selected_box})
        return kwargs

    def get_form(self, step=None, data=None, files=None):
        form_kwargs = self.get_form_kwargs(step)
        form = super().get_form(step, data, files)

        if step == '1':
            selected_facility = self.get_cleaned_data_for_step('0')['facility']
            freezer_queryset = list(selected_facility.dimfreezer_set.all())
            form.fields['freezer'].queryset = selected_facility.dimfreezer_set.all()

        elif step == '2':
            selected_freezer = self.get_cleaned_data_for_step('1')['freezer']
            all_shelves = selected_freezer.shelves.all()
            all_boxes = DimBox.objects.filter(
                Q(shelf__freezer=selected_freezer) |
                Q(rack__shelf__freezer=selected_freezer) |
                Q(rack__freezer=selected_freezer) |
                Q(freezer=selected_freezer)
            )
            if selected_freezer:
                form.fields['box'].queryset = all_boxes

        if step == '3':
            sample_ids = form_kwargs.get('sample_ids', [])
            selected_box = self.get_cleaned_data_for_step('2')['box']
            self.request.session['selected_box'] = selected_box.id
            sample_move_form_set = forms.formset_factory(SampleMoveForm, extra=0,
                                                         can_delete=False)
            if data is not None:
                form = sample_move_form_set(data=data, initial=[
                    {'sample_id': sample_id, 'box': selected_box} for sample_id in
                    sample_ids])
            else:
                form = sample_move_form_set(
                    initial=[{'sample_id': sample_id, 'box': selected_box} for sample_id
                             in sample_ids])

        return form

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        sample_id = self.request.GET.get('sample_ids', '')
        sample = DimSample.objects.get(sample_id=sample_id)
        context['sample'] = sample

        selected_box = self.storage.extra_data.get('selected_box')
        context['selected_box'] = selected_box

        return context

    def validate_position(self, box, x_position, y_position):
        """Validates if a BoxPosition is occupied."""
        return BoxPosition.objects.filter(box=box, x_position=x_position,
                                          y_position=y_position).exists()

    def create_box_position(self, sample, box, x_position, y_position):
        """Creates or updates a BoxPosition."""
        try:
            box_position = BoxPosition.objects.get(
                sample=sample)
        except BoxPosition.DoesNotExist:
            BoxPosition.objects.create(sample=sample, box=box, x_position=x_position,
                                       y_position=y_position)
        else:
            box_position.box = box
            box_position.x_position = x_position
            box_position.y_position = y_position
            box_position.save()

    def done(self, form_list, **kwargs):
        new_positions = []
        box = form_list[-1][0].box if len(form_list[-1]) > 0 else None
        for form in form_list[-1]:
            if form.is_valid():
                cleaned_data = form.cleaned_data
                box = form.initial.get('box')
                sample_id = form.initial.get('sample_id')
                sample = DimSample.objects.get(sample_id=sample_id)
                new_positions.append({
                    'sample': sample,
                    'box': box,
                    'x_position': int(cleaned_data.get("new_x_position")) - 1,
                    'y_position': cleaned_data.get("new_y_position")
                })

        for position in new_positions:
            self.create_box_position(position["sample"], position["box"],
                                     position["x_position"], position["y_position"])

        selected_box = self.request.session.pop('selected_box', None)

        return HttpResponseRedirect(reverse('box_detail', args=[box.id]))
