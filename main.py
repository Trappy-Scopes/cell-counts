import openpyxl
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt


#from plot import fit_exponential

from analysis import *
from script.hasher import *


files = []
dfs = []
files = check_modified("./data", "./filelogs.yml")

# 1. Extract data from files
for file in files:
    file = os.path.join("./data", file)
    print(f"Processing file: {file}")
    #continue
    if file.endswith(".xls") or file.endswith(".xlsx"):
        extractor.process_excel(file) # TODO !!!
    elif file.endswith(".csv"):
        dfs.append(pd.read_csv(file))
    else:
        print("[ERROR] Invalid filename!")


# 2. Pr-process data from files (only CSV)

for i, df in enumerate(dfs):
    print(f"File: {files[i]}")
    # 2.1 Average counts
    col = df.loc[: , "count1":"count4"]
    #df['avg_count'] = col.mean(axis=1)
    df.avg_count =  [np.mean([row[0], row[1],row[2],row[3]]) for row in \
                       zip(df[df.count1], df[df.count2], df[df.count3], df[df.count4],)]

    pprint(list(df['avg_count']))
    # 2.2 Convert Counts to Cells per mL
    perml = [normalize_cells_per_ml(row[0], row[1], row[2]) \
             for row in zip(df['avg_count'], df['v_sample_ul'], df['v_etoh_ul'])]
    df["counts_per_ml"] = perml

    # 2.3 Dump files back
    if files[i].endswith(".xls") or files[i].endswith(".xlsx"):
        pass # Dump to excel
        
    else: # Its a CSV file
        df.to_csv(files[i])


# Plot and save

# 2 plots:

for i, df in enumerate(dfs):
    try:
        fig, axes = plt.subplots(2)
        first_row = df.to_dict(df.iloc[0])
        fig.suptitle(f'Cell counts for \"{file}\" ({first_row["strain"]})')

        # counts per mL on log-linear with fit
        axes[0].plot(list(df['exp_time']), list(df['counts_per_ml']))
        axes[0].title.set_text('Counts per mL')
        axes[0].set_yscale("log")
        axes[0].ylim(1, 10**7)
        axes[0].set_xlabel(f"time ({first_row['time_units']})")

        # Do Fits for axes 0

        # raw counts on linear with fit
        axes[1].plot(list(df['exp_time']), list(df['avg_counts']))
        axes[1].title.set_text('Counts per Quadrant of Haemocytometer')

        # Do Fits for axes 1


        # Save Plots
        plotfilename = files[i].split(".")[0] + ".png"
        plotfilename = os.path.join("./plots", plotfilename)
        fig.savefig(plotfilename)   # save the figure to file
        print(f"Saved plot: {plotfilename}")

    except KeyError:
        print(f"Keyerror for file: {files[i]}")

