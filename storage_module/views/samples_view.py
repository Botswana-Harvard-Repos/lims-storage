from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from storage_module.forms import AdvancedSamplesFilterForm
from storage_module.models import DimBox, DimFacility, DimSample, DimSampleStatus, \
    DimSampleType, DimSourceFile,DimFreezer
from storage_module.util import update_sample_status
from storage_module.views.view_mixin import ViewMixin


class SamplesView(LoginRequiredMixin, ViewMixin, TemplateView):
    template_name = 'storage_module/samples.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('search')
        advanced_filter_form = AdvancedSamplesFilterForm(self.request.GET)
        samples_list = self.get_samples_from_db(advanced_filter_form)
        row_number = int(self.request.POST.get('rows', 20))
        total_samples = len(samples_list)
        page_number = self.request.GET.get('page',1)
        paginator = Paginator(samples_list, row_number)
        page_obj = paginator.get_page(page_number)
        # Pagination info
        total_count = paginator.count           # Total number of items
        items_on_current_page = len(page_obj)  # Get the number of items on this page
        start_index = page_obj.start_index()   # First item index
        end_index = start_index + items_on_current_page - 1 

        context.update(
            samples=paginator.get_page(page_number),
            sample_statuses=self.sample_statuses,
            sample_types=self.sample_types,
            boxes=self.boxes,
            facilities=self.facilities,
            freezers=self.freezer_names,
            source_files=self.source_files,
            advanced_filter_form = advanced_filter_form,
            total_samples=total_samples,
            rows_options=[10, 25, 50, 100, 1000, 10000],
            total_count =total_count,
            page_obj=page_obj,
            start_index=start_index,
            end_index=end_index,
            row_number=row_number,
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
    
    @property
    def freezer_names(self):
        return list(set(DimFreezer.objects.values_list('freezer_name', flat=True)))

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
        queryset = DimSample.objects.values(
            'sample_id',
            'sample_type__sample_type',
            'box_position__box__freezer__facility__facility_name',
            'box_position__box__freezer__id',
            'box_position__box__freezer__freezer_name',
            'box_position__box__freezer__facility__id',
            'source_file__source_file_name',
            'box_position__box__box_name',
            'box_position__box__id',
            'date_sampled',
            'sample_status__name'
        ).order_by('-sample_type')

        # Filtering for date ranges
        if advanced_filter_form.is_valid():  # Check if the form is valid
            dob_start = advanced_filter_form.cleaned_data.get('date_of_birth_start')
            dob_end = advanced_filter_form.cleaned_data.get('date_of_birth_end')
            if dob_start and dob_end:
                queryset = queryset.filter(date_of_birth__range=(dob_start, dob_end))
            elif dob_start:
                queryset = queryset.filter(date_of_birth=dob_start)


            date_sampled_start = advanced_filter_form.cleaned_data.get('date_sampled_start')
            date_sampled_end = advanced_filter_form.cleaned_data.get('date_sampled_end')
            if date_sampled_start and date_sampled_end:
                queryset = queryset.filter(date_sampled__range=(date_sampled_start, date_sampled_end))
            elif date_sampled_start:
                queryset = queryset.filter(date_sampled=date_sampled_start)   

        # Apply other filters based on advanced_filter_form fields
        for field in advanced_filter_form:
            if field.value() and field.name not in ['date_of_birth_start', 'date_of_birth_end', 'date_sampled_start', 'date_sampled_end']:
                queryset = queryset.filter(**{field.name: field.value()})


        return queryset
