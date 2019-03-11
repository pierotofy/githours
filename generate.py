import subprocess
import argparse
from datetime import datetime
import csv
from io import StringIO
import os 

def str_to_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

def str_to_time(s):
    try:
        return datetime.strptime(s, "%H:%M")
    except ValueError:
        msg = "Not a valid time: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

def same_day(d1, d2):
	return to_git_date(d1) == to_git_date(d2)

def to_git_date(d):
	md = {1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN', 7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'}
	return "%s %s %s" % (md[d.month], d.day, d.year)

now = datetime.now()

parser = argparse.ArgumentParser(description='Generate hours report estimate from git log')
parser.add_argument('repo', metavar="GIT_REPO_PATH", type=str,
                    help='path to git repository')
parser.add_argument('output', metavar="OUTPUT", type=str,
                    help='CSV output file')
parser.add_argument('--start-date', '-s', metavar="<YYYY-MM-DD>", type=str_to_date,
                    help='Start Date. Default: %(default)s', default="1970-01-01")
parser.add_argument('--end-date', '-e', metavar="<YYYY-MM-DD>", type=str_to_date,
                    help='End Date. Default: %(default)s', default="%s-%s-%s" % (now.year, now.month, now.day))
parser.add_argument('--author', '-a', metavar="<Author Name>", type=str,
                    help='Author Name. Default: %(default)s', default=None)
parser.add_argument('--skip_commits', '-sm', metavar="<Commit Message>", type=str,
                    help='Skip entries that have this message in the commit. Default: %(default)s', default=None)
parser.add_argument('--estimate-start-time', metavar="<HH:MM>", type=str_to_time,
					help='What time of the day you start working for estimating the time it took to create a commit. Default: %(default)s', default='09:00')
parser.add_argument('--estimate-fallback', metavar="<hours>", type=float,
					help='Default number of hours per commit if the program cannot estimate one. Default: %(default)s', default=1)
parser.add_argument('--verbose', '-v', action='store_true',
					help='Verbose', default=False)


if __name__== "__main__":
	args = parser.parse_args()

	params = ['--since', to_git_date(args.start_date), 
			  '--until', to_git_date(args.end_date), 
			  '--pretty="%ad","%s | %b"']
	if args.author:
		params.append('--author')
		params.append(args.author)

	use_file = os.path.isfile(args.repo)

	if args.verbose:
		if not use_file:
			print("Running git log " + " ".join(params))
			result = subprocess.run(['git', 'log', *params], cwd=args.repo, stdout=subprocess.PIPE)
			scsv = result.stdout.decode("utf-8")
			f = StringIO(scsv)
		else:
			print("Reading from file: %s" % args.repo)
			f = open(args.repo, "r")

	rows = []
	seconds = []
	last_date = None
	last_row_date = None

	for row in csv.reader(f, quotechar='"'):
		if len(row) == 2:
			date, msg = row

			if args.skip_commits and args.skip_commits in msg:
				if args.verbose:
					print("Skipping %s %s" % (date, msg))
				continue

			rows.append((date, msg))

			date = date.strip().replace('"', '')
			msg = msg.strip()
			date = datetime.strptime(date, '%a %b %d %H:%M:%S %Y %z')
			last_row_date = date

			if last_date != None:
				if same_day(date, last_date):
					seconds.append((last_date - date).seconds)
					last_date = date
				else:
					est = args.estimate_start_time.replace(last_date.year, last_date.month, last_date.day, tzinfo=last_date.tzinfo)
					secs = (last_date - est).seconds
					if last_date >= est:
						seconds.append(secs)
					else:
						if args.verbose:
							print("Commit (%s) happened before estimated start time (%s), using fallback of %s" % (last_date, est, args.estimate_fallback))
						seconds.append(args.estimate_fallback * 60 * 60)
					last_date = None
			else:
				last_date = date

	if last_row_date != None:
		est = args.estimate_start_time.replace(last_row_date.year, last_row_date.month, last_row_date.day, tzinfo=last_row_date.tzinfo)
		secs = (last_row_date - est).seconds
		if last_row_date >= est:
			seconds.append(secs)
		else:
			if args.verbose:
				print("Commit (%s) happened before estimated start time (%s), using fallback of %s" % (last_row_date, est, args.estimate_fallback))
			seconds.append(args.estimate_fallback * 60 * 60)

	hours = list(map(lambda s: float(s) / 3600.0, seconds))
	results = list(zip(rows, hours))

	with open(args.output, 'w') as csvfile:
	    csvwriter = csv.writer(csvfile, delimiter=',',
	                            quotechar='"', quoting=csv.QUOTE_ALL)
	    for ((date, msg), hours) in results:
	    	if args.verbose:
	    		print("%s %s %s" % (date, msg, hours))

	    	csvwriter.writerow([date, msg, hours])

	if args.verbose:
		print("Done!")