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

config = {
    "REPORT_SIZE": 100,
    "REPORT_DIR": "./files/reports",
    "LOG_DIR": "./files/log",
    "REPORT_TEMPLATE": "./files/templates/report.html",
    "LOG_FILE": "./files/logfile",
    "REPORT_HISTORY": "./files/report_history",
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

    else:
        try:
            with open(cfg_location, 'r') as f:
                external_config = eval(f.readline())
                merged_config = {**config, **external_config}
                return merged_config
        except:
            logging.info("Could not load external config file")
            return config


def choose_log(config):
    log_folder = config["LOG_DIR"]
    report_history = config["REPORT_HISTORY"]
    if not os.path.isdir(log_folder):
        error("Error loading log. %s folder not found." % log_folder)

    with open(report_history, 'r') as f:
        try:
            report_history = eval(f.readline())
        except:
            logging.error("Report_history не найден или поврежден")
            raise RuntimeError("Report_history не найден или поврежден")

    logs = []
    for log in os.listdir(config["LOG_DIR"]):
        if re.match('nginx\-access\-ui\.log-\d{8}(\.txt|\.gz|\.log)?$', log):
            logs.append(log)
    if len(logs) == 0:
        message = "No logs found"
        logging.error(message)
        raise RuntimeError(message)
    newest_log_name = sorted(logs, reverse=True)[0]
    if newest_log_name in report_history['complete']:
        message = str('The newest log, ' + newest_log_name + ', has been processed. Nothing to process.')
        logging.error(message)
        raise RuntimeError(message)
    return newest_log_name


def open_log(log_path):
    re_gzip = re.compile("\.gz$")
    if re_gzip.search(log_path):
        log_file = gzip.open(log_path, 'r')
    else:
        log_file = open(log_path, 'r')
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
        logging.info("Не удалось распарсить строчку: " + line)
        pass

    return [link, float(request_time)]


def parse_log(iterator):
    report_data = {
        "total_count": 0, "total_req_time": 0, "total_errors": 0
    }

    line_valid_pattern = re.compile(
        '([\.\d]*) ([\-\d\w]*) +([\-\d\w\.]*) (\[.*\]) (\"(GET|POST).*\") (\d*) (\d*) (\".*\") (\".*\") (\".*\") (\".*\") (\".*\") (\d*\.\d*)'
    )

    for line in iterator:

        try:
            line = line.decode("UTF-8").strip()
        except:
            line = line.strip()

        if not line_valid_pattern.match(line):
            report_data["total_errors"] += 1
            continue

        entry = parse_line(line)
        url = entry[0]
        req_time = entry[1]

        report_data["total_count"] += 1
        report_data["total_req_time"] += req_time

        if entry[0] in report_data.keys():
            report_data[url].append(req_time)
        else:
            report_data[url] = [req_time]

    return report_data


def construct_report(config, log_data, report_size):
    error_threshold = config["ERROR_THRESHOLD"]
    if log_data["total_errors"] / log_data["total_count"] > error_threshold:
        error("Error threshold is reached. Data is likely corrupt or in an unsupported format!")

    fin_report = []
    for entry in (log_data.keys()):
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


def mark_complete(log_name, config):
    report_history = config["REPORT_HISTORY"]
    with open(report_history, 'r') as f:
        report_history_data = eval(f.readline())
    if log_name not in report_history_data['complete']:
        report_history_data['complete'].append(log_name)
    with open(report_history, 'w') as f:
        f.write(str(report_history_data))


def set_report_name(log_name):
    re_log_date = re.compile('nginx\-access\-ui\.log-(\d{4})(\d{2})(\d{2})')
    log_date = re_log_date.search(log_name)
    log_name = "report-" + ".".join(log_date.group(1, 2, 3)) + ".html"
    return log_name


def generate_report_html(report_template, output_destination, report_data):
    if not os.path.isfile(report_template):
        error('The report-template is not found in ' + report_template)

    with open(report_template, 'r') as f:
        template = string.Template(f.read())
    report = template.safe_substitute(table_json=json.dumps(report_data))

    with open(output_destination, 'w') as f:
        f.write(report)


def error(message):
    logging.error(message)
    raise RuntimeError(message)


def main(config):
    log_dir = config["LOG_DIR"]
    log_name = choose_log(config)
    if log_name:
        log_path = log_dir + '/' + log_name
        output_destination = config["REPORT_DIR"] + '/' + set_report_name(log_name)
        report_template = config["REPORT_TEMPLATE"]
        report_size = config["REPORT_SIZE"]
        report_data = parse_log(log_path)
        report_summarized = construct_report(config, report_data, report_size)
        generate_report_html(report_template, output_destination, report_summarized)
        mark_complete(log_name, config)


if __name__ == "__main__":
    merged_config = load_config(config)
    if 'LOG_FILE' in config.keys():
        setup_logger(config['LOG_FILE'])
    else:
        setup_logger()

    try:
        main(merged_config)
    except Exception as e:
        logging.exception(str(e))
