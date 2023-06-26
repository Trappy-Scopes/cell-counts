import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from pprint import pprint
from scipy.optimize import curve_fit
import pandas as pd

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

def csv_to_df(filename):
    """
    Load CSV file to a dataframe.
    """
    df = pd.read_csv(filename)
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
def plot_all_curves(df, ylog=True):
    """
    Plots all the replicates.
    Returns the plot object.
    """
    all_replicates = df.replicate.unique()
    print(all_replicates)

    if ylog:
        plt.yscale("log")
        plt.ylim(0, 10**7)

    for rep in all_replicates:
        plt.plot(list(df[df.replicate == rep].exp_time), \
                 list(df[df.replicate == rep].counts_per_ml), "o-", label=rep)
    
    plt.legend()
    plt.title("Growth curves of all replicates")
    plt.ylabel("Cells per mL ->")

    unit = ""
    if "time_units" in df:
        unit = f"({str(df[df.time_units][0])})"

    plt.xlabel(f"Experiment time {unit} ->")
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
        plt.ylim(0, 10**7)


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
    count_norm = lambda N: N * (vsample_ul + veth_ul) / vsample_ul #-> Unitless normalization
    
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
