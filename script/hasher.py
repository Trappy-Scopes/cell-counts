import hashlib
import os
from datetime import datetime

import yaml

def hashfile(filename):
   """"
   This function returns the SHA-1 hash
   of the file passed into it.
   """

   # make a hash object
   h = hashlib.sha1()

   # open file for reading in binary mode
   with open(filename, 'rb') as file:

       # loop till the end of the file
       chunk = 0
       while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)
   return h.hexdigest()


def check_modified(directory, filelogs):
    """
    Checks and returns files that were modifed based on their SHA1 hash signature.
    """
    
    old_hashes = {}
    with open(filelogs, 'r') as f:
        dump = yaml.load(f, Loader=yaml.FullLoader)
        if dump != None:
            old_hashes = dump

    # Get all files listed
    all_files = []
    for entry in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, entry)):
            all_files.append(entry)

    # Remove files that are disqualified by a "*" symbol
    all_files_filt = [file for file in all_files if not file.__contains__("*")]
    all_files_filt.remove('.DS_Store')
    diff = [file for file in all_files if file not in all_files_filt]
    print(f"Following files were disqualified by an asterisk: {diff}")

    print(all_files_filt)

    # Hash all-files
    new_hashes = {}
    for file in all_files_filt:
        new_hashes[file] = hashfile(os.path.join(directory, file))

    # Isolate files that need to be processed
    to_process = []
    for file in all_files_filt:
        

        # New files
        if file not in old_hashes:
            to_process.append(file)
            print(f"Added new file: {file}")
            continue

        # Old files
        if new_hashes[file] != old_hashes[file]:
            to_process.append(file)
            print(f"Modified file: {file}")


    # Write hashkeys back to the filelog
    with open(filelogs, 'w') as f:
       yaml.dump(new_hashes, f)

    return to_process