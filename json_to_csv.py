# Casey Key
# June 19, 2019

import csv
import json
import os
import sys
argv = sys.argv
json_file = argv[1]
out_file = argv[2]

# open the json file
try:
    with open(json_file) as file:
        json_data = json.load(file)
except:
    sys.exit("JSON file not found.")
# write json data to csv
with open(out_file, "w", newline="") as csv_file:
    header = list(json_data.keys())
    writer = csv.DictWriter(csv_file, fieldnames=header)
    writer.writeheader()
    writer.writerow(json_data)

print("Successfully converted file to CSV!")

open_in_editor = input("View in vim? (Y/n):  ").lower()
if open_in_editor == "y":
    os.system("vim " + out_file)

 
