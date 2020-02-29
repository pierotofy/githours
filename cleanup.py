import argparse
from datetime import datetime
import csv
import os 
import sys

parser = argparse.ArgumentParser(description='Cleanup imprecisions between CSVs')
parser.add_argument('csv', metavar="CSV PATHS", type=str, nargs='+',
                    help='Multiple CSV paths')
parser.add_argument('--output', metavar="OUTPUT", type=str,
                    help='CSV output dir', required=True)
parser.add_argument('--test', '-t', action='store_true',
					help='Do not overwrite files, just print results.', default=False)

HOURS_THRESHOLD = 10.0 # per day
DESCR_BLACKLIST = ['Merge branch']

if __name__== "__main__":
    args = parser.parse_args()

    data = {}
    accum = {}

    for file in args.csv:
        print("Reading %s" % file)

        with open(file) as f:
            data[file] = []
            for row in csv.reader(f, quotechar='"'):
                date_str = row[0].strip().replace("\"", "")
                descr = row[1]
                skip = False

                for d in DESCR_BLACKLIST:
                    if d in descr:
                        print("Skipping %s (blacklist)" % row[1])
                        skip = True
                        break
                if skip:
                    continue
                
                date = datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y %z')
                hours = float(row[2])
                md = date.strftime("%b %d")
                if not md in accum:
                    accum[md] = 0
                accum[md] += hours

                if accum[md] <= HOURS_THRESHOLD:
                    data[file].append(row)
                else:
                    print("Skipping %s (%s)" % (row[1], accum[md]))
        
    for file in data:
        fname = os.path.basename(file)
        print("Writing %s" % fname)

        rows = data[file]

        with open(os.path.join(args.output, fname), 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',',
                                    quotechar='"', quoting=csv.QUOTE_ALL)
            for row in rows:
                csvwriter.writerow(row)

    print("Done!")