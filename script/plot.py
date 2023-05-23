import numpy as np
import matplotlib.pyplot as plt

def plot_growth_curve (days, dens, title):
    '''
    scatter plot of cells density
    '''
    if len(dens) != len(days):
        print('Warning: data sizes differ!')
    ndays = len(days)
    plt.xticks(days[:],string_array(days[:]))
    plt.plot(days, dens,'-o')
    plt.ylabel('Density (cells/mL)', fontsize=13)
    plt.xlabel('Time (days)', fontsize=13)
    plt.title(title)
    plt.show()
    
def fit_exponential (x, y, title, save=True, savefile=None):
    '''
    fits an exponential 
    '''
    p = np.polyfit(x, np.log(y), 1)
    a = np.exp(p[1])
    b = p[0]
    x_fitted = np.linspace(np.min(x), np.max(x), 100)
    y_fitted = a * np.exp(b * x_fitted)
    ax = plt.axes()
    ax.plot(x, y, '-o',label='Raw data')
    ax.plot(x_fitted, y_fitted, 'k', label='y = {} exp({} t)'.format(round(a,3),round(b,3)))
    ax.set_title(title)
    ax.set_ylabel('Density (cells/mL)')
    #ax.set_ylim(0, 50)
    ax.set_xlabel('Time (days)')
    ax.legend()
    if save:
        plt.savefig(savefile)
    plt.close()