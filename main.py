import openpyxl
import numpy as np
import pandas as pd
import os

from plot import fit_exponential








for file in files:
    if file.endswith(".xls") or file.endswith(".xlsx"):
        extractor.process_excel(file)
    elif file.endswith(".csv"):
        pass
    else:
        print("Invalid filename!")