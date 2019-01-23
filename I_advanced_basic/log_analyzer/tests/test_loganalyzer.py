import unittest
from unittest.mock import patch, mock_open
from unittest import mock
import loganalyzer
import os
import hashlib
import random
import tempfile

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class Test_functionality(unittest.TestCase):

    def setUp(self):
        self.cfg_default = {
            "REPORT_SIZE": 100,
            "REPORT_DIR": "/test_files/reports",
            "LOG_DIR": "/test_files/log",
            "REPORT_TEMPLATE": "/test_files/templates/report.html",
            "REPORT_HISTORY": "/test_files/report_history",
            "ERROR_THRESHOLD": 0.01
        }

        self.report_history = {
            'failed': [],
            'complete': []
        }

        self.report_history_complete = {
            'failed': [],
            'complete': ['nginx-access-ui.log-20170925.gz',
                         'nginx-access-ui.log-20170926',
                         'nginx-access-ui.log-20170927.gz']
        }

        self.listdir = ['nginx-access-ui.log-20170925.gz',
                        'nginx-access-ui.log-20170926',
                        'nginx-access-ui.log-20170927.gz',
                        'some-other.log-20170928.gz']

        self.listdir_nothing = ['nginx-access-ui.log-20170925.g',
                                'nginx-access-ui.log-20170926.jpg',
                                'nginx-access-db.log-20170927.gz',
                                'some-other.log-20170928.gz']

        self.choose_log_correct = 'nginx-access-ui.log-20170927.gz'

        remote_addr = "1.169.137.128"
        remote_user = "-"
        http_x_real_ip = "-"
        time_local = "[29/Jun/2017:03:50:23 +0300]"
        request = ['"GET /link' + str(i) + '/ HTTP/1.1"' for i in range(1, 11)] * 1000
        status = "200"
        body_bytes_sent = "100"
        http_referer = '"-"'
        http_user_agent = '"watever/agent"'
        http_x_forwarded_for = '"-"'
        http_X_REQUEST_ID = '"whatever"'
        http_X_RB_USER = '"whatever"'
        request_time = [str(float(i + 1)) for i in range(1, 21, 2)] * 1000

        self.log_file = "\n".join(
            [" ".join([remote_addr, remote_user, http_x_real_ip, time_local, request[i], status, body_bytes_sent,
                       http_referer, http_user_agent, http_x_forwarded_for, http_X_REQUEST_ID, http_X_RB_USER,
                       request_time[i]]) for i in range(1000)])

        log_data_summary_correct = {'total_count': 1000, 'total_req_time': 11000.0, 'total_errors': 0}
        log_data_stats_correct = {'/link' + str(i) + '/': [float(i * 2)] * 100 for i in range(1, 11)}
        log_data_stats_errors = {'total_count': 1000, 'total_req_time': 11000.0, 'total_errors': 200}

        self.log_data_correct = {**log_data_summary_correct, **log_data_stats_correct}
        self.log_data_errors = {**log_data_summary_correct, **log_data_stats_errors}
        self.report_10_hash = 18608878

    def test_load_config(self):
        cfg_default = self.cfg_default

        cfg_file = {
            "REPORT_SIZE": 1000,
        }

        merged_cfg = {**cfg_default, **cfg_file}


        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.load",side_effect=[cfg_file]):
                self.assertEqual(loganalyzer.load_config(cfg_default, ["--config", "test-config"]), merged_cfg)
                mock_file.assert_called_with("test-config", 'r')

        with patch("loganalyzer.logging.info") as mock_logger:
            loganalyzer.load_config(cfg_default, ["--config", "nonexistent_cfg"])
            mock_logger.assert_called_with("Could not load external config file")

    def test_choose_log(self):
        listdir = self.listdir
        listdir_nothing = self.listdir_nothing
        config = self.cfg_default
        report_history = self.report_history
        report_history_complete = self.report_history_complete

        with patch('os.listdir') as mocked_listdir:
            with patch('os.path.isdir') as mocked_isdir:

                with patch("builtins.open", mock_open(read_data=str(report_history))) as mock_file:
                    mocked_listdir.return_value = listdir
                    mocked_isdir.return_value = True
                    self.assertEqual(loganalyzer.choose_log(config), self.choose_log_correct)

                    mocked_isdir.return_value = False

                    try:
                        loganalyzer.choose_log(config)
                        self.fail("Exception is not raised by test_choose_log")
                    except RuntimeError as err:
                        self.assertEqual(str(err), "Error loading log. %s folder not found." % config['LOG_DIR'])

                    mock_file.assert_called_with(config["REPORT_HISTORY"], 'r')

                with patch("builtins.open", mock_open(read_data=str(report_history_complete))) as mock_file:
                    mocked_listdir.return_value = listdir
                    mocked_isdir.return_value = True
                    try:
                        loganalyzer.choose_log(config)
                        self.fail("Exception is not raised by test_choose_log")
                    except RuntimeError as err:
                        self.assertEqual(str(err),
                                         'The newest log, nginx-access-ui.log-20170927.gz, has been processed. Nothing to process.')

                    mocked_listdir.return_value = listdir_nothing
                    mocked_isdir.return_value = True
                    try:
                        loganalyzer.choose_log(config)
                        self.fail("Exception is not raised by test_choose_log")
                    except RuntimeError as err:
                        self.assertEqual(str(err),
                                         'No logs found')


    #Probably needs not be reworked to exclude using actual files
    def test_open_log(self):
        log_path = THIS_DIR + "/test_files/log/open_log/nginx-access-ui.log-20170627"
        opened_log = next(loganalyzer.open_log(log_path))
        self.assertEqual(opened_log, "It's a plain text log")
        log_path_gz = THIS_DIR + "/test_files/log/open_log/nginx-access-ui.log-20170927.gz"
        opened_log_gz = (next(loganalyzer.open_log(log_path_gz)).decode('UTF-8'))
        self.assertEqual(opened_log_gz, "It's a gzip text log")

    def test_parse_log(self):

        log_file = self.log_file

        with mock.patch('loganalyzer.open_log') as open_log:
            # Mock open or 'return value' do not provide an iterator. The hack below solves it.
            open_log.__iter__.return_value = log_file.splitlines()
            log_data = loganalyzer.parse_log(open_log)
            log_data_correct = self.log_data_correct
            self.assertEqual(log_data, log_data_correct)

    def test_construct_report(self):
        config = self.cfg_default
        report_data = self.log_data_correct
        report_data_errors = self.log_data_errors
        report_10_hash_correct = self.report_10_hash

        report_10 = loganalyzer.construct_report(config, report_data, 10)
        report_5 = loganalyzer.construct_report(config, report_data, 5)
        report_6 = loganalyzer.construct_report(config, report_data, 6)

        loganalyzer.construct_report(config, report_data, 10)

        # First checking whether the 'report size' variable works
        self.assertEqual(len(report_10), 10)
        self.assertEqual(len(report_5), 5)
        self.assertEqual(len(report_6), 6)

        report_string = str(report_10).encode('utf-8')
        report_10_hash = int(hashlib.sha1(report_string).hexdigest(), 16) % (10 ** 8)
        # Сomparing the hash to that of a known result.
        # Seems to be sufficient for all intents and purposes here.
        self.assertEqual(report_10_hash, report_10_hash_correct)

        try:
            report_10 = loganalyzer.construct_report(config, report_data_errors, 10)
            self.fail("Exception is not raised by test_construct_report")
        except RuntimeError as err:
            self.assertEqual(str(err), "Error threshold is reached. Data is likely corrupt or in an unsupported format!")

    def test_set_report_name(self):
        log_name_gz = loganalyzer.set_report_name("nginx-access-ui.log-20170927.gz")
        reference_log_name_gz = "report-2017.09.27.html"

        log_name_plain = loganalyzer.set_report_name("nginx-access-ui.log-20171027")
        reference_log_name_plain = "report-2017.10.27.html"

        self.assertEqual(log_name_gz, reference_log_name_gz)
        self.assertEqual(log_name_plain, reference_log_name_plain)

    def test_generate_report_html(self):
        config = self.cfg_default
        report_template=str(THIS_DIR+config["REPORT_TEMPLATE"])
        print(report_template)
        randreportvalue=random.randint(100000,1000000)
        report_data=[{"Key":randreportvalue}]
        with mock.patch('os.path.isdir', return_value=True):
            report_path = tempfile.mkstemp()[1]
            try:
                loganalyzer.generate_report_html(report_template,report_path,report_data)
                report_contents = open(report_path).read()
            finally:
                os.remove(report_path)

            #Just checking, whether it's the right html and that the data ends up in it.
            self.assertTrue("rbui log analysis report" in report_contents)
            self.assertTrue(str(randreportvalue) in report_contents)




if __name__ == '__main__':
    unittest.main()
