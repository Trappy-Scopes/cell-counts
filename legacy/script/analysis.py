import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from pprint import pprint
from scipy.optimize import curve_fit
import pandas as pd
from copy import deepcopy

"""
TODO:

Move from dataclass oriented functions to Dataframe oriented functions.
"""

@dataclass
class DensityMeasure:
    counts: list[int]
    date: list[int]
    exp_day: int
    inv_dil: int #1000 means 1:1000 dilution
    strain: str
    replicate: str

# Alias Declaration for Density Measure
DM = DensityMeasure

def dataclass_to_csv(dataclasses, filename):
    """
    Exports a container of data classes to a CSV file using pandas.
    Returns the dataframe object.
    If the filename is passed a `None` value, then no file is created.
    """
    df = pd.DataFrame(dataclasses)
    if filename:
       df.to_csv(filename)
    return df

def csv_to_df(filename, sep=","):
    """
    Load CSV file to a dataframe.
    """
    df = pd.read_csv(filename, sep=sep)
    return df

def plot_individual(curve_id, data, ylog=True):
    """
    Plots Individual Replicate and returns the filtered curve.
    """
    curve = {}
    for point in data:
        if point.replicate == curve_id:
            curve[point.exp_day] = np.mean(point.counts)
    plt.plot(curve.keys(), curve.values())   
    plt.xlabel("Experiment Day")
    plt.ylabel("Average cells per quadrant")
    plt.title(curve_id)

    if ylog:
        plt.yscale("log")
        plt.ylim(0, 10**7)

    plt.show()
    return curve

def plot_avg_replicates(data, ylog=True):
    """
    Plots the average of all replicates based on the exp_day parameter.
    TODO: Remove hardcoded xticks scale.
    """
    curve = {}
    
    for point in data:
        curve[point.exp_day] = 0
    
    for point in data:
        curve[point.exp_day] += np.mean(point.counts)
        
    for day in curve:
        curve[day] = float(curve[day]) / 3
        
    plt.plot(curve.keys(), curve.values())   
    plt.xlabel("Days")
    plt.ylabel("Average cells per quadrant (Replicates Avg)")
    plt.title("Averaged over replicates")
    plt.xticks(list(range(0, 11)))

    if ylog:
        plt.yscale("log")
        plt.ylim(0, 10**7)

    plt.show()
    return curve

# --------- Dataframe based functions --------------
def plot_all_curves(df, ylog=True, dpi=300, title=None):
    """
    Plots all the replicates.
    Returns the plot object.
    """

    all_replicates = df.replicate.unique()
    print(all_replicates)

    if ylog:
        plt.yscale("log")
        plt.ylim(10**3, 10**8)

    for rep in all_replicates:
        strain = list(df[df.replicate == rep].strain)[0]
        plt.plot(list(df[df.replicate == rep].exp_time), \
                 list(df[df.replicate == rep].counts_per_ml), "o-", label=f"{rep} - {strain}")
    
    plt.legend(bbox_to_anchor=(1.5, 1), loc='upper right', borderaxespad=0)
    plt.ylabel("Cells per mL ->")

    unit = ""
    if "time_units" in df:
        unit = f"({list(df.time_units)[0]})"

    plt.xlabel(f"Experiment time {unit} ->")

    if not title:
        plt.title("Growth curves of all replicates")
    else:
        plt.title(title)
    plt.gcf().set_dpi(dpi)
    plt.show()
    return plt

def plot_subplots(df, ylog=True, dpi=300, title=None):
    """
    Plots all the replicates.
    Returns the plot object.
    """
    #plt.style.use('fivethirtyeight')
    all_replicates = df.replicate.unique()
    print(all_replicates)

    fig, axes = plt.subplots(int(len(all_replicates)/2), 2, \
                            dpi=dpi, sharex=True, sharey=True)
                            #figsize=(4,int(len(all_replicates))))
    if not title:
        plt.suptitle("Growth curves of all replicates")
    else:
        fig.suptitle(title)

    unit = ""
    if "time_units" in df:
        unit = f"({list(df.time_units)[0]})"
    plt.xlabel(f"Experiment time {unit} ->", fontsize=8)
    plt.ylabel("Cells per mL ->", fontsize=8)

    fig.tight_layout(pad=1.0)


    ##### ROW {0, 1}
    ## COL1
    ## COL2
    ## ..
    ## COLn
    row_fn = lambda x: int(x % 2) # Remainder
    col_fn = lambda y: int(y / 2) # Division Product

    for i, rep in enumerate(all_replicates):
        strain = list(df[df.replicate == rep].strain)[0]
        col = row_fn(i)
        row = col_fn(i)
        #print(col, row)
        # Generate plot
        x = list(df[df.replicate == rep].exp_time)
        y = list(df[df.replicate == rep].counts_per_ml)
        axes[row][col].plot(x, y, "o-", color="green")
        axes[row][col].set_title(f"{rep} - {strain}", fontsize=8)
        axes[row][col].set_xticks(np.arange(np.min(x), np.max(x), 1))
        axes[row][col].yaxis.grid(True, which='minor')


        # Contamination marks
        if "comments" in df:
            c = list(df[df.replicate == rep].comments)
            c = [str(comment).lower() for comment in c]
            if "contamination" in c:
                print(f"{rep} - Contamination!")
                idx  = c.index("contamination")
                c_exp_day = x[idx]
                c_density = 10**6
                axes[row][col].plot(c_exp_day, c_density, marker= "$C$", label="Contamination", color="red")


        if ylog:
            axes[row][col].set_yscale("log")
            axes[row][col].set_ylim(10**3, 10**7)
            axes[row][col].set_yticks([int(10**i) for i in range(3,7,1)])
    
    plt.show()
    return plt

def individual_fit_exp(df, replicate, name=None, ylog=True):
    """
    Does an exponential fit on the replicate ID.
    Returns the fit parameters.
    """
    if not name:
        name = replicate


    curve = dict(zip(df[df.replicate == replicate].exp_day, \
     [np.mean(rep) for rep in df[df.replicate == replicate].counts]))
    
    exp_fn = lambda t, a, b: a*np.exp(b*t)
    popt, pcov = curve_fit(exp_fn,  list(curve.keys()),  list(curve.values()))
    plt.plot(list(curve.keys()), list(curve.values()), "o-", label="data")
    fit = exp_fn(np.array(list(curve.keys()), dtype=float), *popt)
    plt.plot(list(curve.keys()), fit, 'r-', label='fit: a=%5.3f, b=%5.3f' % tuple(popt))
    plt.legend()
    plt.title(f"Exponential fit on replicate: {name}")
    
    if ylog:
        plt.yscale("log")
        plt.ylim(10**3, 10**7)


    plt.show()
    return popt, pcov, curve

def doubling_time(params):
    """
    params should be of the form: (popt, pcov, curve)
    Returns the cell doubling time.
    """
    return (np.log(2)/a2_fit_param[0][1])

# Cell Normalisation Functions
HCM_CONSTANTS = {"Depth_mm": 0.1, "grid_area_mm2":1, "tot_vol_mm3": 0.4, 
                 "total_vol_ml": 0.00040, "total_vol_ul": 0.40000, 
                 "mole": 6.02247*(10**23)  
                }

def normalize_cells_per_ml(graph_, vsample_ul, veth_ul):
    """
    Normalize Cells per quadrant to Cells per mL.
    vsample_ul : Amount of cell sample used during counting.
    veth_ul : Amount of Ethanol used during counting.
    """
    graph = deepcopy(graph_)
    
    # Normalize fluid volume / Cell counts
    count_norm = lambda N: N * (float(vsample_ul) + float(veth_ul)) / float(vsample_ul) #-> Unitless normalization
    
    # Normalize area
    vol_norm = lambda N: N / HCM_CONSTANTS["total_vol_ml"]
    
    if isinstance(graph, dict):
        for point in graph:
            graph[point] = vol_norm(count_norm(graph[point]))
    else:
        graph = vol_norm(count_norm(graph))
    
    return graph
    
def normalize_mol_per_ml(graph_, vsample_ul, veth_ul):
    """
    Normalize cells per quadrant to cells in mol per mL.
    vsample_ul : Amount of cell sample used during counting.
    veth_ul : Amount of Ethanol used during counting.
    """
    
    graph = deepcopy(graph_)
    
    graph = normalize_cells_per_ml(graph, vsample_ul, veth_ul)
    
    for point in graph:
        graph[point] = graph[point] / HCM_CONSTANTS["mole"]
    return graph
