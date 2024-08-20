import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from storage_module.models import (BoxPosition, DimBox, DimFacility, DimFreezer, DimRack,
                                   DimSample, DimSampleType, DimShelf)
from storage_module.util import append_entity_info, append_if_samples
from storage_module.views import SampleMoveWizard


class HomeView(TemplateView):
    template_name = 'storage_module/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_specimen'] = DimSample.objects.all().count()
        context['specimen_types'] = DimSampleType.objects.all().count()
        context['unique_participants'] = DimSample.objects.values(
            'participant_id').distinct().count()
        context['studies'] = DimSample.objects.values(
            'protocol_number').distinct().count()

        return context


class DashboardView(TemplateView):
    template_name = 'storage_module/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['facility_count'] = DimFacility.objects.count()
        context['freezer_count'] = DimFreezer.objects.count()
        context['sample_count'] = BoxPosition.objects.count()

        all_protocol_counts = DimSample.objects.values('protocol_number').annotate(
            count=Count('protocol_number')).order_by('-count')
        context['protocol_counts'] = all_protocol_counts[:5]
        context['total_protocol_count'] = all_protocol_counts.count()

        sample_type_count = DimSample.objects.values_list('sample_type',
                                                          flat=True).distinct().count()
        context['sample_type_count'] = sample_type_count

        study_count = DimSample.objects.values('protocol_number').distinct().count()
        context['study_count'] = study_count

        return context


@login_required
def get_shelves(request):
    freezer_id = request.GET.get('freezer_id')
    shelves = DimShelf.objects.filter(freezer_id=freezer_id).values()
    return JsonResponse(list(shelves), safe=False)


@login_required
def get_racks(request):
    freezer = request.GET.get('freezer_id')
    racks = DimRack.objects.filter(freezer_id=freezer).values()
    return JsonResponse(list(racks), safe=False)


@login_required
def get_freezers(request):
    facility = request.GET.get('facility_id')
    freezers = DimFreezer.objects.filter(facility_id=facility).values()
    return JsonResponse(list(freezers), safe=False)


def get_sample_details(request, sample_id):
    sample = get_object_or_404(DimSample, sample_id=sample_id)
    data = {
        "sample_id": sample.sample_id,
        "protocol_number": sample.protocol_number,
        "tid": sample.tid,
        "sample_type": sample.sample_type.sample_type,
        "source_file": sample.source_file.source_file_name,
        "time_sampled": sample.time_sampled,
        "sample_condition": sample.sample_condition,
        "user_created": sample.user_created,
        "participant_id": sample.participant_id,
        "gender": sample.gender,
        "date_of_birth": sample.date_of_birth,
        "date_sampled": sample.date_sampled,
        "requisition_id": sample.requisition_id,
        "sample_status": sample.sample_status.name,
    }
    return JsonResponse(data)


def freezer_data(request, freezer_id):
    freezer = get_object_or_404(DimFreezer, id=freezer_id)
    box_n_shelves_n_racks_data = []

    for box in freezer.boxes.filter(shelf=None, rack=None):
        append_if_samples(box, box_n_shelves_n_racks_data, 'box_detail', 'fas fa-cube',
                          box.box_name)

    append_entity_info(freezer.shelves.all(), box_n_shelves_n_racks_data, 'shelf_detail',
                       'fas fa-layer-group', 'shelf_name')

    append_entity_info(freezer.racks.all(), box_n_shelves_n_racks_data, 'rack_detail',
                       'fas fa-box-open', 'rack_name')

    html = render_to_string("storage_module/child_box_detail.html",
                            {'inside_freezer': box_n_shelves_n_racks_data})

    return JsonResponse({'html': html})


def ajax_validate_position(request):
    box = request.GET.get('box', None)
    x_position = request.GET.get('x_position', None)
    y_position = request.GET.get('y_position', None)
    sample = request.GET.get('sample', None)

    if SampleMoveWizard().validate_position(box, int(x_position) - 1, y_position):
        error = {
            "error": {
                "message": "The chosen position is already occupied. Please choose a "
                           f"different position at sample {sample}."
            }
        }
        return JsonResponse(error)
    return JsonResponse({"error": None})


def check_barcode(request):
    data = json.loads(request.body)
    sample_id = data.get('barcode')
    exists = DimSample.objects.filter(sample_id=sample_id).exists()
    return JsonResponse({'valid': exists})


def get_sample_position(request):
    barcode = request.GET.get('barcode')

    if barcode is not None:
        try:
            position = BoxPosition.objects.get(sample__sample_id=barcode)
            box_id = position.box.box_name if position.box else None
            x = position.x_position
            y = position.y_position
        except BoxPosition.DoesNotExist:
            return JsonResponse(
                {'success': False,
                 'error': 'This sample was does not exist in the system '
                          'database'})

        return JsonResponse(
            {'success': True, 'box': box_id, 'x': x, 'y': y})

    else:
        return JsonResponse({'success': False, 'error': 'No barcode provided.'})


def add_samples(request):
    data = json.loads(request.body)
    barcode = data.get('scannedBarcode')
    box_id = data.get('box_id')
    x = data.get('x')
    y = data.get('y')

    if not all([barcode, box_id, x, y]):
        return JsonResponse({'success': False, 'error': 'Missing data in request.'})

    try:
        position = BoxPosition.objects.get(sample__sample_id=barcode)
    except BoxPosition.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'This sample was does not exist in the system '
                                        'database'})

    try:
        box = DimBox.objects.get(box_name=box_id)
    except DimBox.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Failed to retrieve box.'})

    position.box = box
    position.x_position = x
    position.y_position = y
    position.save()
    return JsonResponse({'success': True})
