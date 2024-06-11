import os
from datetime import date

def file_timestamp_graph(dir_="."):

	all_files = list(os.listdir(dir_))
	all_files.sort()

	# Get creation time of each file
	times = [os.path.getctime(file) for file in all_files]

	# Parse ISO time format
	isostamps = [date.fromisoformat(file) for file in times]

	# Parse to millisecond tick
	ms_ticks = [datetime.timestamp(iso) for iso in isostamps]

	return ms_ticks