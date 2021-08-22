#!/usr/bin/python
#title			:portfolio-size-cp.py
#description	:This code is a helper utility that creates a log file
# named under the outfile_name by pulling in the size of the portfolio and 
# logging it to the outfile.
#author			:Erick Clasen
#date			:20210822
#version		:0.1
#usage			:python portfolio-size-cp.py
#notes			:
#python_version	: 2.7.6
#python_version	: Python 3.4.3
#==============================================================================
from datetime import datetime
import coretamodule as cm
import json
import csv

outfile_name = 'portfolio-ttl-in-usd.log'
out_list = []
# Get the portfolio size and the time in.
portfolio_size = cm.read_portfolio_size()
#print(str(datetime.now()),portfolio_size)

out_list.append(str(datetime.now()))
out_list.append(portfolio_size)
# Make a log file of portfolio size

with open(outfile_name, mode = 'a') as outfile:
	output_writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
	output_writer.writerow(out_list)	
#find /home/erick/python/daily/portfoilio_size.json -mtime -1 -exec cat > lsh-portfolio-ttl.csv {}  \;
