#!/bin/bash

# Generate a fake datetime and value pair and append it as the last row
datetime=$(date '+%Y-%m-%dT%H:%M:%SZ')
value=$(awk -v min=0 -v max=100 'BEGIN{srand(); print min+(rand()*(max-min))}') #

echo "$datetime,$value"