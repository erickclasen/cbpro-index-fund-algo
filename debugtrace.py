#!/usr/bin/python
#title			:debugrace.py
#description	:This code allows breadcrumbs output to a log file to trace variables.
# 
#author			:Erick Clasen
#date			:20210822
#version		:0.1
#usage			:python debugtrace.py
#notes			:
#python_version	: 2.7.6
#python_version	: Python 3.4.3
#==============================================================================
import csv
from datetime import datetime

# DEBUG TRACING
def d_trace(msg,var):
    ''' A debug tracer can be called with a message and a variable to trace and it will record them to the debug log file. 
        Also prints out the results as it runs.'''
    filename = "debug-trace.log"

    out_list = []

    out_list.append(str(datetime.now()))    
    out_list.append(msg)
    out_list.append(var)
    print("---------------------")
    print("----DEBUG TRACE----: ",msg,var)
    print("---------------------")

    # Open the CSV file and output a row using the out_list
    with open(filename, mode='a') as outfile:
        output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        output_writer.writerow(out_list)
