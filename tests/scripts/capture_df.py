#!/usr/bin/env python
# Author: GPT-4
# Description: Prompt: "write a script using base python to write a csv to stdout"
import csv
import sys

# Fields
fields = ['Name', 'Age', 'Occupation']

# Rows
rows = [ ['Nashit', '25', 'Software Developer'],
         ['John', '30', 'Doctor']]

# CSV writer object
writer = csv.writer(sys.stdout)

# Writing the fields
writer.writerow(fields)

# Writing the data rows
writer.writerows(rows)
