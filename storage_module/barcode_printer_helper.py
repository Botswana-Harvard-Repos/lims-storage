import logging
import socket

import zpl
from django.conf import settings

from storage_module.models import Barcodes, DimSample

logger = logging.getLogger(__name__)


class BarcodePrinter:
    PRINTER_IP = settings.PRINTER_IP_ADDRESS
    PRINTER_PORT = int(settings.PRINTER_PORT)
    SOCKET_TIMEOUT = 10
    LABEL_DIMENSIONS = (100, 60)
    TEXT_SPECIFICATION = {'char_height': 10, 'char_width': 8, 'line_width': 60,
                          'justification': 'C'}

    @staticmethod
    def generate_label(sample):
        """
        Generate a ZPL label for a given sample ID
        """
        lbl = zpl.Label(100, 50)
        lbl.origin(15, 1)
        lbl.write_text("^BY1.5,2.3,100")
        lbl.barcode('3', sample.sample_id, height=60,
                    check_digit='N')
        lbl.endorigin()
        lbl.origin(18, 9)
        lbl.write_text(f"{sample.sample_id} {sample.sample_type.sample_type}",
                       char_height=1,
                       char_width=1.5,
                       line_width=15, justification='C')
        lbl.endorigin()
        lbl.origin(17, 10)
        lbl.write_text(f"{sample.participant_id} {sample.protocol_number}",
                       char_height=1,
                       char_width=1.5,
                       line_width=15, justification='C')
        lbl.endorigin()

        lbl.origin(16.5, 11)
        lbl.write_text(f"DOB:{sample.date_of_birth} {sample.gender}",
                       char_height=1,
                       char_width=1.5,
                       line_width=18, justification='C')
        lbl.endorigin()

        lbl.origin(16.5, 12)
        lbl.write_text(f"{sample.date_sampled} {sample.time_sampled}",
                       char_height=1,
                       char_width=1.5,
                       line_width=20, justification='C')
        lbl.endorigin()

        return lbl.dumpZPL()

    @staticmethod
    def print_zpl(zpl_string):
        """
        Send the ZPL string to the printer
        """
        logger.debug("Attempting to connect to the printer at IP: %s, Port: %s",
                     BarcodePrinter.PRINTER_IP,
                     BarcodePrinter.PRINTER_PORT)

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(BarcodePrinter.SOCKET_TIMEOUT)
                sock.connect((BarcodePrinter.PRINTER_IP, BarcodePrinter.PRINTER_PORT))
                logger.debug("Connected to the printer. Sending data...")
                sock.send(bytes(zpl_string, 'utf-8'))
                logger.debug("Data sent to the printer.")
        except socket.timeout:
            logger.error("Socket timeout when trying to connect to the printer.")
        except Exception as e:
            logger.error("Exception occurred when trying to connect to the printer: %s",
                         str(e))

    def print_barcode_for_selected_samples(self, selected_samples):
        """
        Generate the barcode label for each selected sample and send them to the printer
        """
        for sample_id in selected_samples:
            sample = self.get_sample_data(sample_id)
            label = self.generate_label(sample)
            # self.save_barcode(sample_id, label)
            # breakpoint()
            self.print_zpl(label)

    def save_barcode(self, sample_id, zpl_string):
        """
        Save the barcode and its associated sample id on the database
        """
        # Extract the barcode element from the ZPL string.
        parts = zpl_string.split('^FD')
        barcode_parts = [part.split('^FS')[0] for part in parts if '^FS' in part]

        barcode = None
        for barcode_part in barcode_parts:
            breakpoint()
            if len(barcode_part) == 10:
                barcode = barcode_part

        if barcode:
            # Save to Database
            Barcodes.objects.create(sample_id=sample_id, barcode=barcode)
        else:
            logger.error("No suitable barcode found in ZPL string for sample_id %s",
                         sample_id)

    def get_sample_data(self, sample_id):
        """
        Fetch the sample data for a given sample ID
        """
        return DimSample.objects.get(sample_id=sample_id)
