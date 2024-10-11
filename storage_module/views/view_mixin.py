import csv
from datetime import datetime

from django.http import HttpResponse

from storage_module.models import DimSample


class ViewMixin:

    def export_samples_as_csv(self, sample_ids):
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        response = HttpResponse(content_type='text/csv')
        response[
            'Content-Disposition'] = f'attachment; filename=samples_{timestamp_str}.csv'

        writer = csv.writer(response)
        headers = ['Sample ID', 'Sample Type', 'Source File Name', 'Condition',
                   'Created By', 'Participant ID', 'Gender', 'Date of Birth',
                   'Date Sampled', 'Time Sampled', 'Requisition ID', 'Protocol Number',
                   'Facility Name', 'Freezer Name','Box Name', 'Sample Status']
        writer.writerow(headers)

        samples = DimSample.objects.filter(sample_id__in=sample_ids)
        for sample in samples:
            writer.writerow([
                sample.sample_id,
                sample.sample_type.sample_type if sample.sample_type else "",
                sample.source_file.source_file_name if sample.source_file else "",
                sample.sample_condition if sample.sample_condition else "",
                sample.user_created if sample.user_created else "",
                sample.participant_id if sample.participant_id else "",
                sample.gender if sample.gender else "",
                sample.date_of_birth if sample.date_of_birth else "",
                sample.date_sampled if sample.date_sampled else "",
                sample.time_sampled if sample.time_sampled else "",
                sample.requisition_id if sample.requisition_id else "",
                sample.protocol_number if sample.protocol_number else "",
                sample.facility.facility_name if sample.facility else "",
                sample.freezer.freezer_name if sample.freezer else "",
                sample.box.box_name if sample.box else "",
                sample.sample_status.name if sample.sample_status else ""
            ])

        return response
