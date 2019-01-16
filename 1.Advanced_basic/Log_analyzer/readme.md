# Otus PyDev Course Homework
# 01. Log analyzer

## Task description:

A web-interface has been showing signs of slowdowns.  
In order to evaluate the problem, a $request_time property has been introduced to the nginx logs.  
The task is to write a tool that will conduct a preliminary analysis and of the logs to help identify potentially faulty URLs.

## Log analyzer description

### Functionality
- Daily logs should be put into the 'log' folder in either gzip or plain text format.
- Naming format for the logs is 'nginx-access-ui.log-_yyyymmdd_'.
- Upon its launch, script scans the folder for the most recent log, based on the log's name;
- The log is then processed, summarized and then rendered into a report html and put into the "reports" folder (naming format is 'report-_yyyy_._mm_._dd_.html').
- In case of an error, the script exits, leaving a corresponding message it its own log ('logfile' by default).
### Report Structure
![Alt](https://i.imgur.com/RMVn4vL.jpg "Report structure")
__url__ -- URL-address, to which requets were made.  
__count__ -- total number of requests to that URL.  
__count_perc__ -- total number of requests to that URL expressed in % from the total number of requests found in the log file.  
__time_sum__ -- total __$request_time__  for that URL.  
__time_perc__ -- total __$request_time__  for that URL expressed in % from the total __$request_time__ for all requests found in the log file.  
__time_avg__ -- average __$request_time__ for that URL.  
__time_max__ -- maximum __$request_time__ for that URL.  
__time_med__ -- median __$request_time__ for that URL.  

The report displays URLs with the highest __time_sum__ parameter. Number of URLs shown can be adjusted in the config.

### Configuration
The script accepts one command line argument -- a string with a path to an external config file.

A sample config with all the parameters set to default looks like this:
```
{
    "REPORT_SIZE": 100, 
    "REPORT_DIR": "./files/reports",
    "LOG_DIR": "./files/log",
    "REPORT_TEMPLATE": "./files/templates/report.html",
    "LOG_FILE": "./files/logfile",
    "REPORT_HISTORY": "./files/report_history",
    "ERROR_THRESHOLD":0.01
}
```


_REPORT_SIZE_ -- number of URLs with the highest __time_sum__ parameter to be included in the report  
_LOG_DIR_           -- folder with logs to process  
_REPORT_DIR_        -- folder where compiled reports should be put into  
_REPORT_TEMPLATE_   -- path to the report template  
_LOG_FILE_          -- path to the script's own log file  
_REPORT_HISTORY_    -- path to the script's own log file  
_ERROR_THRESHOLD_   -- acceptable ration of errors to the total number of processed lines in the log  

An external log needs to contain.  

### Common Errors ###

Whenever there is a critical errors, the scripts shuts down and records the error to the log.  
__Common reasons for the  script to stop:__  
- No reports to process. Either because the newest report has been processed, or because the 'log' folder is empty.  
- Either 'log' or 'reports' folder doesn't exist.  
- Number of errors above the threshold value 
