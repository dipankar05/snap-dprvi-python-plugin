###################################################################################################
# Copyright (C) 2021 by Microwave Remote Sensing Lab, IITBombay http://www.mrslab.in
# 
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option)
# any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, see http://www.gnu.org/licenses/
###################################################################################################

import dprvi_algo
import numpy
import numpy as np
import snappy
#from snappy import FlagCoding

#NDVI_HIGH_THRESHOLD = 0.7
DPRVI_LOW_THRESHOLD = 0.3
DPRVI_LOWER_FACTOR = 3

# If a Java type is needed which is not imported by snappy by default it can be retrieved manually.
# First import jpy
from snappy import jpy

# and then import the type
Float = jpy.get_type('java.lang.Float')
Color = jpy.get_type('java.awt.Color')


class DprviOp:
    def __init__(self):
        self.lower_band = None
        self.upper_band = None
        self.lower1_band = None
        self.upper1_band = None
        self.dprvi_band = None
        #self.ndvi_flags_band = None
        self.algo = None
        self.lower_factor = 3
        #self.upper_factor = 0.0
        
    def conv2d(self, a, f):
        filt = np.zeros(a.shape)
        wspad = int(f.shape[0]/2)
        s = f.shape + tuple(np.subtract(a.shape, f.shape) + 1)
        strd = np.lib.stride_tricks.as_strided
        subM = strd(a, shape = s, strides = a.strides * 2)
        filt_data = np.einsum('i,ik->k', f, subM)
        filt[wspad:wspad+filt_data.shape[0]] = filt_data
        return filt

    def initialize(self, context):
        # Via the context object the source product which shall be processed can be retrieved
        source_product = context.getSourceProduct('source')
        print('initialize: source product location is', source_product.getFileLocation())

        width = source_product.getSceneRasterWidth()
        height = source_product.getSceneRasterHeight()

        # Retrieve a parameters defined in ndvi_op-info.xml
        lower_band_name = context.getParameter('SourceC11')
        upper_band_name = context.getParameter('SourceC12real')
        lower1_band_name = context.getParameter('SourceC12imag')
        upper1_band_name = context.getParameter('SourceC22')
        self.lower_factor = context.getParameter('Windowsize')
        #self.upper_factor = context.getParameter('upperFactor')

        self.lower_band = self._get_band(source_product, lower_band_name)
        self.upper_band = self._get_band(source_product, upper_band_name)
        self.lower1_band = self._get_band(source_product, lower1_band_name)
        self.upper1_band = self._get_band(source_product, upper1_band_name)

        print('initialize: lower_band =', self.lower_band, ', upper_band =', self.upper_band, ', lower1_band =', self.lower1_band, ', upper1_band =', self.upper1_band)
        print('initialize: lower_factor =', self.lower_factor)

        # As it is always a good idea to separate responsibilities the algorithmic methods are put
        # into an other class
        self.algo = dprvi_algo.DprviAlgo(DPRVI_LOW_THRESHOLD,DPRVI_LOWER_FACTOR)

        # Create the target product
        dprvi_product = snappy.Product('py_DPRVI', 'py_DPRVI', width, height)
        # ProductUtils provides several useful helper methods to build the target product.
        # In most cases it is sufficient to copy the information from the source to the target.
        # That's why mainly copy methods exist like copyBand(...), copyGeoCoding(...), copyMetadata(...)
        snappy.ProductUtils.copyGeoCoding(source_product, dprvi_product)
        snappy.ProductUtils.copyMetadata(source_product, dprvi_product)
        snappy.ProductUtils.copyTiePointGrids(source_product, dprvi_product)
        # For copying the time information no helper method exists yet, but will come in SNAP 5.0
        dprvi_product.setStartTime(source_product.getStartTime())
        dprvi_product.setEndTime(source_product.getEndTime())

        # Adding new bands to the target product is straight forward.
        self.dprvi_band = dprvi_product.addBand('dprvi', snappy.ProductData.TYPE_FLOAT32)
        self.dprvi_band.setDescription('Dual-pol Radar Vegetation Index')
        self.dprvi_band.setNoDataValue(Float.NaN)
        self.dprvi_band.setNoDataValueUsed(True)
        #self.ndvi_flags_band = ndvi_product.addBand('ndvi_flags', snappy.ProductData.TYPE_UINT8)
        #self.ndvi_flags_band.setDescription('The flag information')

        # Create a flagCoding for the flag band. This helps to display the information properly within SNAP.
        #ndviFlagCoding = FlagCoding('ndvi_flags')
        # The NDVI_LOW flag shall be at bit position 0 and has therefor the value 1, NDVI_HIGH has the
        # value 2 (bit 1) and so one
        #low_flag = ndviFlagCoding.addFlag("NDVI_LOW", 1, "NDVI below " + str(NDVI_LOW_THRESHOLD))
        #high_flag = ndviFlagCoding.addFlag("NDVI_HIGH", 2, "NDVI above " + str(NDVI_HIGH_THRESHOLD))
        #neg_flag = ndviFlagCoding.addFlag("NDVI_NEG", 4, "NDVI negative")
        #pos_flag = ndviFlagCoding.addFlag("NDVI_POS", 8, "NDVI positive")
        #ndvi_product.getFlagCodingGroup().add(ndviFlagCoding)
        #self.ndvi_flags_band.setSampleCoding(ndviFlagCoding)

        # Also for each flag a layer should be created
        # ndvi_product.addMask('mask_' + low_flag.getName(), 'ndvi_flags.' + low_flag.getName(),
                             # low_flag.getDescription(), Color.YELLOW, 0.3)
        # ndvi_product.addMask('mask_' + high_flag.getName(), 'ndvi_flags.' + high_flag.getName(),
                             # high_flag.getDescription(), Color.GREEN, 0.3)
        # ndvi_product.addMask('mask_' + neg_flag.getName(), 'ndvi_flags.' + neg_flag.getName(),
                             # neg_flag.getDescription(), Color(255, 0, 0), 0.3)
        # ndvi_product.addMask('mask_' + pos_flag.getName(), 'ndvi_flags.' + pos_flag.getName(),
                             # pos_flag.getDescription(), Color.BLUE, 0.3)

        # Provide the created target product to the framework so the computeTileStack method can be called
        # properly and the data can be written to disk.
        context.setTargetProduct(dprvi_product)

    def computeTileStack(self, context, target_tiles, target_rectangle):
        # The operator is asked by the framework to provide the data for a rectangle when the data is needed.
        # The required source data for the computation can be retrieved by getSourceTile(...) via the context object.
        lower_tile = context.getSourceTile(self.lower_band, target_rectangle)
        upper_tile = context.getSourceTile(self.upper_band, target_rectangle)
        lower1_tile = context.getSourceTile(self.lower1_band, target_rectangle)
        upper1_tile = context.getSourceTile(self.upper1_band, target_rectangle)

        # The actual data can be retrieved from the tiles by getSampleFloats(), getSamplesDouble() or getSamplesInt()
        lower_samples = lower_tile.getSamplesFloat()
        upper_samples = upper_tile.getSamplesFloat()
        lower1_samples = lower1_tile.getSamplesFloat()
        upper1_samples = upper1_tile.getSamplesFloat()
        # Values at specific pixel locations can be retrieved for example by lower_tile.getSampleFloat(x, y)
        
        # Filter kernel build
        #kernel = np.ones((self.lower_factor,1),np.float32)/(self.lower_factor*1)
        #kernel = numpy.array([1/self.lower_factor,1/self.lower_factor,1/self.lower_factor], dtype=numpy.float32) 
        
        ls = [1/self.lower_factor]*self.lower_factor
        kernel = np.array(ls,dtype=numpy.float32)


        # Convert the data into numpy data. It is easier and faster to work with as if you use plain python arithmetic
        #lower_data = numpy.array(lower_samples, dtype=numpy.float32) * self.lower_factor
        lower_data1 = numpy.array(lower_samples, dtype=numpy.float32) 
        upper_data1 = numpy.array(upper_samples, dtype=numpy.float32) 
        lower1_data1 = numpy.array(lower1_samples, dtype=numpy.float32) 
        upper1_data1 = numpy.array(upper1_samples, dtype=numpy.float32) 
        
        ## Apply convolution averaging ops
        lower_data = self.conv2d(lower_data1,kernel)
        upper_data = self.conv2d(upper_data1,kernel)
        lower1_data = self.conv2d(lower1_data1,kernel)
        upper1_data = self.conv2d(upper1_data1,kernel)

        # Doing the actual computation
        dprvi = self.algo.compute_dprvi(lower_data, upper_data, lower1_data, upper1_data)
        #ndvi_flags = self.algo.compute_flags(ndvi)

        # The target tile which shall be filled with data are provided as parameter to this method
        dprvi_tile = target_tiles.get(self.dprvi_band)
        #ndvi_flags_tile = target_tiles.get(self.ndvi_flags_band)

        # Set the result to the target tiles
        dprvi_tile.setSamples(dprvi)
        #ndvi_flags_tile.setSamples(ndvi_flags)

    def dispose(self, context):
        pass

    def _get_band(self, product, name):
        # Retrieve the band from the product
        # Some times data is not stored in a band but in a tie-point grid or a mask or a vector data.
        # To get access to this information other methods are exposed by the product class. Like
        # getTiePointGridGroup().get('name'), getVectorDataGroup().get('name') or getMaskGroup().get('name')
        # For bands and tie-point grids a short cut exists. Simply use getBand('name') or getTiePointGrid('name')
        band = product.getBandGroup().get(name)
        if not band:
            raise RuntimeError('Product does not contain a band named', name)
        return band
