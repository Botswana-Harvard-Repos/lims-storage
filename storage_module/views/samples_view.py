from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from storage_module.forms import AdvancedSamplesFilterForm
from storage_module.models import DimBox, DimFacility, DimSample, DimSampleStatus, \
    DimSampleType, DimSourceFile
from storage_module.util import update_sample_status
from storage_module.views.view_mixin import ViewMixin


class SamplesView(LoginRequiredMixin, ViewMixin, TemplateView):
    template_name = 'storage_module/samples.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('search')
        advanced_filter_form = AdvancedSamplesFilterForm(self.request.GET)
        samples_list = self.get_samples_from_db(advanced_filter_form)
        row_number = int(self.request.POST.get('rows', 10))
        total_samples = len(samples_list)
        page_number = self.request.GET.get('page')
        paginator = Paginator(samples_list, row_number)

        context.update(
            samples=paginator.get_page(page_number),
            sample_statuses=self.sample_statuses,
            sample_types=self.sample_types,
            boxes=self.boxes,
            facilities=self.facilities,
            source_files=self.source_files,
            advanced_filter_form = advanced_filter_form,
            total_samples=total_samples,
            rows_options=[10, 25, 50, 100, 1000, 10000],
        )
        return context

    @property
    def sample_statuses(self):
        return DimSampleStatus.objects.all()

    @property
    def sample_types(self):
        return list(set(DimSampleType.objects.values_list('sample_type', flat=True)))

    @property
    def boxes(self):
        return list(set(DimBox.objects.values_list('box_name', flat=True)))

    @property
    def facilities(self):
        return list(set(DimFacility.objects.values_list('facility_name', flat=True)))

    @property
    def source_files(self):
        return list(set(DimSourceFile.objects.values_list('source_file_name', flat=True)))

    def post(self, request, *args, **kwargs):
        sample_ids = request.POST.getlist('sample_id')
        action = request.POST.get('action')
        if action == "export":
            return self.export_samples_as_csv(sample_ids)
        elif action and int(action) in self.sample_statuses.values_list('id', flat=True):
            for sample_id in sample_ids:
                update_sample_status(sample_id=sample_id, status=action)
        return self.get(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        sample_id = request.GET.get('sample_id', None)
        new_status_id = request.GET.get('sample_status', None)
        if sample_id and new_status_id:
            sample = get_object_or_404(DimSample, sample_id=sample_id)
            new_status = get_object_or_404(DimSampleStatus, id=new_status_id)
            sample.sample_status = new_status
            sample.save()
        return self.render_to_response(context)

    def get_samples_from_db(self, advanced_filter_form):
        queryset = DimSample.objects.all()

        if advanced_filter_form.is_valid():
            for field in advanced_filter_form:
                if field.value():
                    queryset = queryset.filter(**{field.name: field.value()})

        return queryset
