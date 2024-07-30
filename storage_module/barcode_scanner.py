import cv2
from pyzbar.pyzbar import decode

from storage_module.models import DimSample


class BarcodeScanner:

    def __init__(self):
        self.cap = cv2.VideoCapture(0)

    def get_barcode(self):
        # Capture frame from camera
        ret, frame = self.cap.read()

        # Process frame
        barcodes = decode(frame)

        for barcode in barcodes:
            barcode_info = barcode.data.decode("utf-8")
            return self.get_sample(barcode_info)
        return None

    def get_sample(self, sample_id):
        """
        Fetch the sample data for a given sample ID
        """
        return DimSample.objects.get(sample_id=sample_id)
