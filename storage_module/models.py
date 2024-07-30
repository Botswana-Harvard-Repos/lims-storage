from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class DimFacility(models.Model):
    facility_name = models.CharField(max_length=255)

    def __str__(self):
        return self.facility_name

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimfacility'


class DimSampleType(models.Model):
    sample_type = models.CharField(max_length=255, unique=True)

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimsampletype'


class DimSourceFile(models.Model):
    source_file_name = models.CharField(max_length=100)
    source_file_description = models.TextField(null=True)

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimsourcefile'


class BoxPosition(models.Model):
    sample = models.OneToOneField('DimSample', on_delete=models.CASCADE,
                                  related_name="box_position", to_field='sample_id')
    box = models.ForeignKey('DimBox', on_delete=models.CASCADE)
    x_position = models.IntegerField(verbose_name="X Position",
                                     help_text='Horizontal position in the box grid')
    y_position = models.CharField(verbose_name="Y Position",
                                  max_length=255,
                                  help_text='Vertical position in the box grid')

    class Meta:
        app_label = 'storage_module'
        db_table = 'boxposition'
        unique_together = ('box', 'x_position', 'y_position')


class DimBox(models.Model):
    box_name = models.CharField(max_length=255)
    box_description = models.TextField(null=True, )
    box_capacity = models.IntegerField(default=100, null=True, )
    rack = models.ForeignKey('DimRack', on_delete=models.CASCADE, related_name='boxes',
                             null=True, blank=True)
    shelf = models.ForeignKey('DimShelf', on_delete=models.CASCADE, related_name='boxes',
                              null=True, blank=True)
    freezer = models.ForeignKey('DimFreezer', on_delete=models.CASCADE,
                                related_name='boxes', null=True, blank=True)

    def __str__(self):
        return self.box_name

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimbox'
        unique_together = ('id', 'box_capacity', 'rack', 'shelf', 'freezer')

    @property
    def positions(self):
        return self.boxposition_set.all()

    def get_samples(self):
        return [position.sample for position in self.positions]

    @property
    def location(self):
        if self.rack:
            return {
                'facility': getattr(getattr(self.rack, 'freezer', None), 'facility',
                                    None),
                'freezer': getattr(self.rack, 'freezer', None),
                'shelf': getattr(self.rack, 'shelf', None),
                'rack': self.rack
            }
        if self.shelf:
            return {
                'facility': getattr(getattr(self.shelf, 'freezer', None), 'facility',
                                    None),
                'freezer': getattr(self.shelf, 'freezer', None),
                'shelf': self.shelf
            }
        if self.freezer:
            return {
                'facility': self.freezer.facility,
                'freezer': self.freezer
            }


class DimTime(models.Model):
    time_sampled = models.CharField(max_length=10)
    time_of_day = models.CharField(max_length=50)
    day_of_week = models.CharField(max_length=20)

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimtime'


class DimSampleStatus(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimsamplestatus'


class Note(models.Model):
    sample = models.ForeignKey('DimSample', related_name='notes',
                               on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'storage_module'
        db_table = 'note'

    def __str__(self):
        return self.text


class DimSample(models.Model):
    sample_id = models.CharField(max_length=255, unique=True, db_index=True)
    protocol_number = models.CharField(max_length=255, null=True, )
    tid = models.CharField(max_length=255, null=True, )
    participant_id = models.CharField(max_length=255, null=True, )
    gender = models.CharField(max_length=255, null=True, )
    date_of_birth = models.DateField(null=True, )
    date_sampled = models.DateField(null=True, )
    time_sampled = models.CharField(null=True, max_length=225)
    sample_condition = models.CharField(max_length=255, null=True, )
    user_created = models.CharField(max_length=255, null=True, )
    cinitials = models.CharField(max_length=255, null=True, )
    visit_code = models.CharField(max_length=255, null=True, )
    requisition_id = models.CharField(max_length=255, null=True, )
    sample_type = models.ForeignKey('DimSampleType', on_delete=models.CASCADE, null=True)
    source_file = models.ForeignKey('DimSourceFile', on_delete=models.CASCADE, null=True)
    sample_status = models.ForeignKey('DimSampleStatus', on_delete=models.CASCADE,
                                      null=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if self.sample_status and self.sample_status.name not in ['In Storage',
                                                                  'Archived']:
            BoxPosition.objects.filter(sample_id=self.sample_id).delete()

        return super().save(*args, **kwargs)

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimsample'

    @property
    def box(self):
        return self.box_position.box if hasattr(self, 'box_position') else None

    @property
    def rack(self):
        return self.box.rack if self.box and self.box.rack else None

    @property
    def shelf(self):
        return self.box.shelf if self.box and self.box.shelf else None

    @property
    def freezer(self):
        return self.box.freezer if self.box and self.box.freezer else None

    @property
    def facility(self):
        return self.freezer.facility if self.freezer else None


class DimRack(models.Model):
    rack_name = models.CharField(max_length=50, null=True)
    rack_description = models.TextField(null=True)
    shelf = models.ForeignKey('DimShelf', on_delete=models.CASCADE, related_name='racks',
                              null=True, blank=True)
    freezer = models.ForeignKey('DimFreezer', on_delete=models.CASCADE,
                                related_name='racks', null=True, blank=True)

    def __str__(self):
        return self.rack_name

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimrack'


class DimShelf(models.Model):
    shelf_name = models.CharField(max_length=50)
    shelf_description = models.TextField()
    freezer = models.ForeignKey('DimFreezer', on_delete=models.CASCADE,
                                related_name='shelves', null=True, blank=True)

    def __str__(self):
        return self.shelf_name

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimshelf'


class DimFreezer(models.Model):
    freezer_name = models.CharField(max_length=255)
    freezer_description = models.TextField(null=True)
    facility = models.ForeignKey('DimFacility', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.freezer_name

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimfreezer'


class DimLocation(models.Model):
    freezer = models.ForeignKey('DimFreezer', on_delete=models.CASCADE)
    facility = models.ForeignKey('DimFacility', on_delete=models.CASCADE)
    shelf = models.ForeignKey('DimShelf', on_delete=models.CASCADE)
    rack = models.ForeignKey('DimRack', on_delete=models.CASCADE)

    class Meta:
        app_label = 'storage_module'
        db_table = 'dimlocation'


class MeasureSampleCountsByFacility(models.Model):
    facility = models.ForeignKey('DimFacility', on_delete=models.CASCADE)
    sample_count = models.IntegerField()

    class Meta:
        app_label = 'storage_module'
        db_table = 'measuresamplecounts'


class MeasureSampleTypeCountsByFacility(models.Model):
    facility = models.ForeignKey('DimFacility', on_delete=models.CASCADE)
    sample_type = models.ForeignKey('DimSampleType', on_delete=models.CASCADE)
    sample_type_count = models.IntegerField()

    class Meta:
        app_label = 'storage_module'
        db_table = 'measuresampletypecounts'


class Barcodes(models.Model):
    barcode = models.CharField(max_length=255, unique=True)
    sample_id = models.CharField(max_length=255)
