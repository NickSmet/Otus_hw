#!/usr/bin/env python


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import sys
import os
import argparse
import gzip
import re
import json
import string
import logging
import statistics
from collections import namedtuple
from decimal import Decimal
from datetime import datetime
import tempfile

CONFIG = {
    "REPORT_SIZE": 100,
    "REPORT_DIR": "./files/reports",
    "LOG_DIR": "./files/log",
    "REPORT_TEMPLATE": "./files/templates/report.html",
    "LOG_FILE": "./files/logfile",
    "ERROR_THRESHOLD": 0.01
}


def setup_logger(logfile=None):
    logging.basicConfig(  # type: ignore
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
        filename=logfile)


def load_config(config, args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Load an external log file')
    cfg_location = parser.parse_args(args).config

    if not cfg_location:
        return config

    try:
        with open(cfg_location, 'r') as cfg_file:
            external_config = json.load(cfg_file)
            merged_config = {**config, **external_config}
            return merged_config
    except Exception as e:
        error(e)


def choose_log(log_dir):
    log_info = namedtuple('log_info', 'dir date ext')
    log_name_pattern = re.compile('nginx-access-ui\.log-(?P<date>\d{8})(?P<ext>\.txt|\.gz|\.log)?$')

    if not os.path.isdir(log_dir):
        error("Error loading log. %s folder not found." % log_dir)

    newest_date = datetime(1970, 1, 1)
    for log in os.listdir(log_dir):
        log_re = log_name_pattern.match(log)

        if log_re is None:
            continue

        log_date_str = log_re.group('date')
        try:
            log_ext_str = log_re.group('ext')
        except:
            log_ext_str = None

        log_date_dtime = datetime.strptime(log_date_str, '%Y%m%d')

        if log_date_dtime > newest_date:
            newest_date = log_date_dtime
            newest_log = log_info(log_dir, log_date_dtime, log_ext_str)

    try:
        return newest_log
    except:
        error("No logs found")


def open_log(log_info):
    log_dir = getattr(log_info, "dir")
    log_date = getattr(log_info, "date")
    log_ext = getattr(log_info, "ext")

    log_date_str = log_date.strftime("%Y%m%d")

    if log_ext is None:
        log_name = 'nginx-access-ui.log-' + log_date_str
    else:
        log_name = 'nginx-access-ui.log-' + log_date_str + log_ext

    log_path = os.path.join(log_dir, log_name)

    if log_ext in [".log", ".txt", None]:
        log_file = open(log_path, 'r')
    else:
        log_file = gzip.open(log_path, 'r')

    for line in log_file:
        yield line
    log_file.close()


def parse_line(line):
    link_re = "(GET|POST)\s+(.*)\s+?HTTP\/"
    req_time_re = "(\d+\.\d+)$"
    try:
        link = re.search(link_re, line).group(2)
        request_time = re.search(req_time_re, line).group(1)
    except:
        info("Не удалось распарсить строчку: " + line)
        pass

    return [link, float(request_time)]


def parse_log(iterable):
    report_raw_data = {
        "total_count": 0, "total_req_time": 0, "total_errors": 0
    }

    line_valid_pattern = re.compile(
        '([\.\d]*) ([\-\d\w]*) +([\-\d\w\.]*) (\[.*\]) \"(GET|POST) (?P<href>.*)\" (\d*) (\d*) (\".*\") (\".*\") (\".*\") (\".*\") (\".*\") (?P<request_time>\d*\.\d*)'
    )

    for line in iterable:

        try:
            line = line.decode("UTF-8").strip()
        except:
            line = line.strip()

        if not line_valid_pattern.match(line):
            report_raw_data["total_errors"] += 1
            continue

        entry = parse_line(line)
        url = entry[0]
        req_time = entry[1]

        report_raw_data["total_count"] += 1
        report_raw_data["total_req_time"] += req_time

        if entry[0] in report_raw_data.keys():
            report_raw_data[url].append(req_time)
        else:
            report_raw_data[url] = [req_time]

    return report_raw_data


def set_report_name(log_date):
    log_date_str = log_date.strftime("%Y.%m.%d")
    log_name = "report-" + log_date_str + ".html"
    return log_name


def construct_report(error_threshold, log_data, report_size):
    if Decimal(log_data["total_errors"]) / Decimal(log_data["total_count"]) > error_threshold:
        error("Error threshold is reached. Data is likely corrupt or in an unsupported format!")

    fin_report = []
    for entry in log_data:
        if entry in ('total_count', 'total_req_time', 'total_errors'):
            continue
        entry_data = log_data[entry]
        url_entry = {"count": len(entry_data),
                     "time_avg": round(statistics.mean(entry_data), 3),
                     "time_max": round(max(entry_data), 3),
                     "time_sum": round(sum(entry_data), 3),
                     "url": entry,
                     "time_med": round(statistics.median(entry_data), 3),
                     "time_perc": round((sum(entry_data) / log_data["total_req_time"] * 100), 3),
                     "count_perc": round((len(entry_data) / log_data["total_count"] * 100), 3)}
        fin_report.append(url_entry)
    fin_report_sorted = sorted(fin_report, key=lambda i: i['time_sum'], reverse=True)[0:report_size]
    return fin_report_sorted


def generate_report_html(report_template, report_output_path, report_data):
    if not os.path.isfile(report_template):
        error('The report-template is not found in ' + report_template)

    with open(report_template, 'r') as f:
        template = string.Template(f.read())
    report = template.safe_substitute(table_json=json.dumps(report_data))

    with tempfile.NamedTemporaryFile() as temp:
        with open(temp.name, 'w') as tmp:
            tmp.write(report)
            os.link(temp.name, report_output_path)


def error(message):
    logging.error(message)
    raise RuntimeError(message)


def info(message):
    logging.info(message)


def main(config):
    log_dir = config["LOG_DIR"]
    log_info = choose_log(log_dir)
    log_date = getattr(log_info, "date")

    open_log_iterable = open_log(log_info)

    report_dir = config["REPORT_DIR"]
    if not os.path.isdir(report_dir):
        os.makedirs(report_dir)

    report_output_path = os.path.join(report_dir, set_report_name(log_date))
    if os.path.isfile(report_output_path):
        info("Report for the latest log already exists")
        return

    report_template = config["REPORT_TEMPLATE"]
    report_size = config["REPORT_SIZE"]

    report_raw_data = parse_log(open_log_iterable)
    error_threshold = Decimal(config["ERROR_THRESHOLD"])

    report_data = construct_report(error_threshold, report_raw_data, report_size)

    generate_report_html(report_template, report_output_path, report_data)


if __name__ == "__main__":
    merged_config = load_config(CONFIG)

    if 'LOG_FILE' in merged_config:

        setup_logger(merged_config['LOG_FILE'])
    else:
        setup_logger()


    try:
        main(merged_config)
    except Exception as e:
        logging.exception(str(e))
