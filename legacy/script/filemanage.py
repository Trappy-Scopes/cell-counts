import yaml


from hasher import hashfile

def check_modified(directory, filelogs):
	
	old_hashes = None
	with open(filelogs, 'r') as f:
	    data = yaml.load(f, Loader=yaml.FullLoader)

	# Get all files listed
	all_files = []
	for entry in os.listdir(directory):
	    if os.path.isfile(os.path.join(directory, entry)):
	        all_files.append(entry)

	# Hash all-files
	new_hashes = {}
	for file in all_files:
		new_hashes[file] = hashfile(file)

	# Isolate files that need to be processed
	to_process = []
	for file in all_files:
		
		# New files
		if file not in old_hashes:
			to_process.append(file)
			print(f"Added new file: {file}")
			continue

		if new_hashes[file] != old_hashes[file]:
			to_process.append(file)
			print(f"Modified file: {file}")


	# Write hashkeys back to the fillog
	with open(filelogs, 'w') as f:
	   yaml.dump(new_hashes ,f)

	return to_process

