from unittest import mock

from django.conf import settings
from django.test import TestCase

from storage_module.barcode_printer_helper import BarcodePrinter


class BarcodePrinterTestCase(TestCase):

    def test_generate_label(self):
        """
        Test generation of ZPL label
        """
        sample_id = 'test123'
        label = BarcodePrinter.generate_label(sample_id)
        self.assertIsInstance(label, str)

    @mock.patch('socket.socket')
    def test_print_zpl(self, mock_socket):
        """
        Test sending ZPL to printer
        """
        # Create a mock socket instance
        sock_instance = mock_socket.return_value.__enter__.return_value
        sock_instance.send.return_value = None

        test_zpl_string = '^XA^FO50,50^ADN,36,20^FDZPL test^FS^XZ'
        BarcodePrinter.print_zpl(test_zpl_string)

        # Assert that the socket was used correctly
        sock_instance.connect.assert_called_once_with((settings.PRINTER_IP_ADDRESS, 9100))
        sock_instance.send.assert_called_once_with(bytes(test_zpl_string, 'utf-8'))

    @mock.patch.object(BarcodePrinter, 'generate_label')
    @mock.patch.object(BarcodePrinter, 'print_zpl')
    def test_print_barcode_for_selected_samples(self, mock_print_zpl,
                                                mock_generate_label):
        """
        Test barcode generation and printing for selected samples
        """
        sample_ids = ['test1', 'test2', 'test3']

        # make generate_label return the same value it was called with
        mock_generate_label.side_effect = lambda x: x

        BarcodePrinter().print_barcode_for_selected_samples(sample_ids)
        calls = [mock.call(sample) for sample in sample_ids]
        mock_generate_label.assert_has_calls(calls)
        mock_print_zpl.assert_has_calls(calls)
