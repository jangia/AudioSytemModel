#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 17:15:24 2017

@author: jangia
"""
import datetime
import json
import os

import pandas as pd
import numpy as np
from pymongo import MongoClient
from keras.models import Sequential
from keras.layers import Dense
import matplotlib.pyplot as plt

NUM_SMAPLES = 5000
# create DB connection
client = MongoClient()
db = client.amp

AMPS = [0.90**i for i in range(0, 26)]

model = Sequential()
model.add(Dense(units=NUM_SMAPLES, input_dim=NUM_SMAPLES, kernel_initializer='normal'))
model.add(Dense(units=NUM_SMAPLES, kernel_initializer='normal'))
model.compile(loss='mean_squared_error', optimizer='adam')

cnt = 0

for amp in AMPS:
        
    print('Started at: ' + str(datetime.datetime.now()))
    
    # Get all FFTs
    fft_ref_all = pd.DataFrame(list(db.fft.find({'amp': str(AMPS[0])})))
    fft_all = pd.DataFrame(list(db.fft.find({'amp': str(AMPS[0])})))
    
    print('I have data from database at:' + str(datetime.datetime.now()) )
    
    dataset = fft_all.merge(fft_ref_all, how='inner', on=['amp', 'frequency'])
    
    f = dataset.iloc[:, 3].values
    
    print('Working for f={f} and amp={amp}'.format(f=str(f[cnt]), amp=amp))
    
    cnt += 1
    
    # Set amplitude and input FFT as input data
    gain = np.float64(dataset.iloc[:, -3].values)[0]
    volume = np.float64(dataset.iloc[:, -1].values)[0]
    
    X3 = dataset.iloc[:, -4].values
    
    # Initialize X
    X = np.empty([56, 5000])
    
    # Set output FFT
    Y1 = dataset.iloc[:, 2].values
    
    # Initialize real and imag array of output FFT
    Y = np.empty([56, 5000])
    
    print('X and Y initialized')
    print('Filling X and Y with values from database')
    # Convert from string to complex and amplitude
    for i in range(0, len(X3)):
        
        X[i][0] = gain
        X[i][1] = volume
        
        for j in range(0, NUM_SMAPLES):
            
            Y[i][j] = abs(np.char.replace(Y1[i][j], '', '').astype(np.complex128))
            
            if j < NUM_SMAPLES-2:
                X[i][j + 2] = abs(np.char.replace(X3[i][j], '', '').astype(np.complex128))
                
    # Fit model
    print('Fit model')
    model.fit(X, Y, batch_size=56, epochs=12)
    
    print('Draw FFTs')
    # It is for test only
    
    if cnt > 24:
        for h in range(0, len(X)):
    
            # Predicting the Test set results
            y_pred = model.predict(X[h:h+1])
    
            fig = plt.figure()
            
            plt.subplot(2, 1, 1)
            plt.semilogy(abs(Y[h]),'r')
            plt.title('Measured Output VS Predicted Output')
            plt.ylabel('Amplitude')
            
            plt.subplot(2, 1, 2)
            plt.semilogy(abs(np.matrix.transpose(y_pred)))
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Amplitude')
            
            filename = 'g{0}v{1}f{2}a{3}'.format(str(gain), str(volume), str(f[h]), str(amp)).replace('.', '_')
            plt.savefig('/home/jangia/Documents/Mag/MaisterAmpSim/neural_network/plots/{0}.png'.format(filename))
            
            plt.close(fig)
    
    print('Finished at: ' + str(datetime.datetime.now()))
    

# serialize model to JSON
BASE_DIR = os.path.dirname(os.path.abspath('test_model.py'))

model_json = model.to_json()
with open(os.path.join(BASE_DIR, 'models', 'test_model.json'), "w") as json_file:
    json_file.write(json.dumps(json.loads(model_json), indent=4))
model.save(os.path.join(BASE_DIR, 'models', 'test_model.h5'))
