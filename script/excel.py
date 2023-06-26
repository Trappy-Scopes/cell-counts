import openpyxl
import numpy as np
import pandas as pd
import os
from datetime import datetime

import yaml
from hasher import hashfile

def extract_sheets(excel_file, sheet_general_name):
    '''
    Returns a list of the desired sheet names
    '''
    list_sheets = []
    excel_sheets = excel_file.sheet_names # all the sheets in the excel 
    word_len = len(sheet_general_name) # to compare

    for sheet in excel_sheets:
        if sheet[:word_len] == sheet_general_name: # if the beginning matches the general name
            list_sheets.append(sheet)
    print(list_sheets)
    
    return list_sheets

def find_rows (excel_file, sheet, interest_data):
    '''
    TODO: generalize 'Headers'
    Finds desired rows of a certain excel file sheet, given their headers
    '''
    df = pd.read_excel(excel_file, sheet)
    headers = df['Headers'] # column of headers 
    pos_rows = []
    for row in interest_data:
        pos_rows.append(np.where(df['Headers']==row)[0][0]) # search for the rows in 'Headers'
    
    return pos_rows


def flush_row_data(excel_file, sheet, pos_rows):
    '''
    Reads data from specific rows of an excel file sheet 
    '''
    data = []
    df = pd.read_excel(excel_file, sheet)
    for row in pos_rows:
        data.append(df.values[row][:])  
    return data

def clean_data (data): 
    '''
    Removes the header and footer nan values in the end of the row
    '''
    data_new = []
    for var in data:
        var_new = []
        for el in var[1:]:
            if np.isnan(el):
                break
            else:
                var_new.append(el)
        data_new.append(var_new)
    
    return data_new

def process_excel(excel_filename):
    """
    Processes Excel files by extracting each sheet and plotting it.
    """
    excel_file = pd.ExcelFile(excel_filename) # create a dataframe
    sheet_general_name = 'Hemocytometer_t' # the types of sheets we want
    interest_data = ['Day_fraction', 'Density (cells/mL)'] # the data we want
    list_sheets = extract_sheets(excel_file, sheet_general_name)
    rows = find_rows (excel_file, list_sheets[0], interest_data)

    # TODO: organize the first sheet '0' - now it's mixing tube 1 and tube 2
    for sheet in list_sheets[1:]: 
        data = flush_row_data (excel_file, sheet, rows)
        data_new = clean_data(data)
        fit_exponential (data_new[0], data_new[1], sheet, save=True, savefile=os.path.join("/plots/", f"{sheet}.png"))