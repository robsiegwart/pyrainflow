'''
pyrainflow

Rainflow counting of time-history data in Python.

Based on the method described here:
    https://community.sw.siemens.com/s/article/rainflow-counting
'''

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def round_nearest(value, lst):
    '''
    Round ``value`` to the nearest number in list ``lst``. In cases where a
    list value is equidistant the min of the two is returned.

    Source: https://www.geeksforgeeks.org/python-find-closest-number-to-k-in-given-list/
    '''
    return lst[min(range(len(lst)), key=lambda i: abs(lst[i]-value))]


def hysteresis(signal, ratio=0.02, gate=None):
    '''
    Remove small fluctuations in a signal.

    :param Series signal:   The input data as a Pandas Series with the index as
                            the timeseries
    :param num ratio:       The fraction of the signals max range to use as the
                            gate, defaults to 2%
    :param num gate:        The small fluctuation cutoff as a fixed value, if
                            specified used in place of ``ratio``.
    '''
    gate_ = gate if gate else ratio*(max(signal) - min(signal))
    drop = []
    for i,v in enumerate(signal.iloc[:-3]):
        v0 = v
        v1 = signal.iat[i+1]
        v2 = signal.iat[i+2]
        
        if abs(v1-v0) > gate_:
            continue
        
        if v1 < v0 and v2 > v1:
            if v0 - v1 < gate_:
                drop.append(i+1)
        
        elif v1 > v0 and v2 < v1:
            if v1 - v0 < gate_:
                drop.append(i+1)
    
    idx = signal.iloc[drop].index
    return signal.drop(idx)


def peak_valley(signal):
    '''Return only the peaks and valleys'''
    drop = []
    for i,v in enumerate(signal.iloc[:-3]):
        v0 = v
        v1 = signal.iat[i+1]
        v2 = signal.iat[i+2]

        if v2 > v1 > v0 or v2 < v1 < v0:
            drop.append(i+1)
        
    idx = signal.iloc[drop].index
    return signal.drop(idx)


def discretize(signal, bins=128):
    '''
    Discretize the signal into discrete bins.

    :param Series signal:   The input ``Series`` data
    :param int bins:        The number of bins to divide the data into, defaults
                            to 128.
    '''
    bins_list = np.linspace(min(signal), max(signal), bins).round(4)
    discretized = []
    for i,v in signal.iteritems():
        discretized.append(round_nearest(v,bins_list))
    
    return pd.Series(data=discretized, index=signal.index), bins_list


def merge_plateus(signal, tratio=0.0005):
    '''
    Average any flat plateaus in the signal.

    ``peak_valley()`` is called at the end because there may be a single
    point (the merged point) remaining between a peak and valley.

    :param float tratio:    Tolerance ratio for what is deemed "flat". Is a
                            multiplier to (max()-min()). Defaults to 0.05%.
    '''
    idx_list = signal.index.tolist()
    tol = tratio*(max(signal)-min(signal))
    drop = []

    for i,v in enumerate(signal.iloc[:-1]):
        v0 = v
        v1 = signal.iat[i+1]
        if abs(v0-v1) <= tol:
            idx_list[i] = (idx_list[i] + idx_list[i+1])/2
            drop.append(i+1)
    
    signal2 = signal.copy()
    signal2.index = idx_list
    idx = signal2.iloc[drop].index
    return peak_valley(signal2.drop(idx))


def count4pt(signal, bins):
    '''
    Count cycles by the Four-Point Counting Method.
    '''
    rm = pd.DataFrame(0, index=bins, columns=bins)
    sgnl = signal.copy()
    i = 0

    while True:
        try:
            s1 = sgnl.iloc[i + 0]
            s2 = sgnl.iloc[i + 1]
            s3 = sgnl.iloc[i + 2]
            s4 = sgnl.iloc[i + 3]
        except IndexError:
            break
    
        sr_i = abs(s2 - s3)
        sr_o = abs(s1 - s4)

        if sr_i <= sr_o and s4 >= max(s2,s3) and s1 <= min(s2,s3):
            rm.at[s2,s3] += 1
            s2_idx = sgnl.index[i + 1]
            s3_idx = sgnl.index[i + 2]

            sgnl.drop([s2_idx, s3_idx], inplace=True)
            i = 0

        else:
            i += 1
        
    return rm, sgnl


def plot_rm(rm, bins):
    '''
    Plot a rainflow cycles matrix as a 2D grid of values mapping the "From"
    stress to the "To" stress.
    '''
    fig, ax = plt.subplots()
    im = ax.pcolormesh(bins, bins, rm, shading='nearest', cmap='binary')
    fig.colorbar(im)
    ax.set_xlabel('To Stress')
    ax.set_ylabel('From Stress')
    ax.set_title('Cycles')
    ax.set_aspect('equal')
    ax.grid()
    plt.show()


def table(rm):
    '''
    Return a DataFrame of stress ranges and their cycles.

    Table data is of the form:

        Cycles  Range  Mean

    '''
    idx_lst = rm.index
    data = []
    for fromstr, row in rm.iterrows():
        for col,cycles in enumerate(row):
            if cycles:
                tostr = idx_lst[col]
                range = abs(fromstr - tostr)
                mean = (fromstr + tostr)/2
                data.append([cycles, range, mean])

    df = pd.DataFrame(data, columns=['Cycles','Range','Mean'])
    return df.sort_values('Cycles', ascending=False)


def preprocess(signal):
    '''Wrapper to call all preprocessing functions'''
    signal = hysteresis(signal)
    signal = peak_valley(signal)
    signal, bins = discretize(signal)
    return merge_plateus(signal), bins