import os
import sys
import argparse
import shutil

datadir = "./data"
templates = os.listdir("templates")




parser = argparse.ArgumentParser(description='New Counting')


parser.add_argument('-t', '--template', dest='template', type=str, help='Type of template. Default is template1.', default="template1.csv")
parser.add_argument('-n', '--name', dest='name', type=str, help='Name of the Experiment/Counting.')
args = parser.parse_args()
if not args.name.endswith(".csv"):
	args.name = args.name + ".csv"

if args.template not in templates:
	print("Invalid template! Exiting!")
	exit(1)
elif args.name in os.listdir("./data"):
	print("Data file already exists for this name! Exiting!")
	exit(1)
else:
	print(f"Creating new experiment/counting file: {os.path.join(datadir, args.name)}")
	shutil.copyfile(os.path.join("./templates", args.template), os.path.join("./data", args.name))

