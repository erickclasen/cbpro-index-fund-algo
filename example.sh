#!/bin/bash

# Copy the portfolio size from the json file to a log first.
# This is optional but, nice to have a log of the portfolio size 
#to monitor performance.

# This will not run this on the first run, but all thereafter it will find the json file
# created by the index-balancer code.
portfolio-size-cp.py

# Call the code with the real credentials...
# Use the sim version for a dry run testing. It just has the API calls commented out.
python3 sim-index-balancer.py 'key goes here' 'b64secret goes here' 'passphrase goes here'
