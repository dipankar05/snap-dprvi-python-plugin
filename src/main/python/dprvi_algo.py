import numpy
import numpy as np


class DprviAlgo:

    def __init__(self, low_threshold):
        self.low_threshold = low_threshold
        #self.high_threshold = high_threshold

    def compute_dprvi(self, lower_data, upper_data, lower1_data, upper1_data):
        
        c11s = lower_data
        c12s = upper_data + 1j*lower1_data
        c21s = np.conjugate(c12s)
        c22s = upper1_data
        
        c2_det = (c11s*c22s-c12s*c21s)
        c2_trace = c11s+c22s
        m = (np.sqrt(1.0-(4.0*c2_det/np.power(c2_trace,2))))
        
        #trace = (c11s+c22s)
        #det = c11s*c22s-c12s*c21s
        sqdiscr = np.sqrt(np.abs(c2_trace*c2_trace - 4*c2_det));
        egv1 = (c2_trace + sqdiscr)*0.5;
        egv2 = (c2_trace - sqdiscr)*0.5;
        
        #sqdiscr = np.sqrt(np.abs(c2_trace*c2_trace - 4*c2_det));
        #egv1 = (c2_trace + sqdiscr)*0.5;
        #egv2 = (c2_trace - sqdiscr)*0.5;
        # egf = ([egv1,egv2])
        # egfmax = float(np.max(egf))
        #egfmax = max(egv1,egv2)
        beta = np.abs(egv1/(egv1+egv2))
        
        dprvi = np.abs(1 -(m*beta))
        
        
        #ndvi = (upper_data - lower_data) / (upper_data + lower_data)
        return dprvi
