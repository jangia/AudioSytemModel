#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 17:15:24 2017

@author: jangia
"""
import datetime
import os
import pandas as pd
import numpy as np
from pymongo import MongoClient
from keras.models import Sequential
from keras.layers import Dense
import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft
from scipy.io import wavfile as wav

NUM_SAMPLES_IN = 2500
NUM_SAMPLES_OUT = 10000

DATA_RANGE = 112
# create DB connection
client = MongoClient()
db = client.amp

AMPS = [0.90 ** i for i in range(0, 26)]

model_real = Sequential()
model_real.add(Dense(units=NUM_SAMPLES_IN, input_dim=NUM_SAMPLES_IN+2, kernel_initializer='normal'))
model_real.add(Dense(units=int(NUM_SAMPLES_OUT/2), kernel_initializer='normal'))
model_real.add(Dense(units=NUM_SAMPLES_OUT, kernel_initializer='normal'))
model_real.compile(loss='mean_squared_error', optimizer='adam')

model_imag = Sequential()
model_imag.add(Dense(units=NUM_SAMPLES_IN, input_dim=NUM_SAMPLES_IN+2, kernel_initializer='normal'))
model_imag.add(Dense(units=int(NUM_SAMPLES_OUT/2), kernel_initializer='normal'))
model_imag.add(Dense(units=NUM_SAMPLES_OUT, kernel_initializer='normal'))
model_imag.compile(loss='mean_squared_error', optimizer='adam')

cnt = 0

for amp in AMPS:

    print('Started at: ' + str(datetime.datetime.now()))

    # Get all FFTs
    fft_ref_all = pd.DataFrame(list(db.fft_ref.find({'amp': str(amp)})))
    fft_all = pd.DataFrame(list(db.fft.find({'amp': str(amp)})))

    print('I have data from database at:' + str(datetime.datetime.now()))

    dataset = pd.merge(fft_all, fft_ref_all, how='inner', on=['amp', 'frequency'])

    f = dataset.iloc[:, 3].values

    print('Working for amp={amp}'.format(amp=amp))

    # Set amplitude and input FFT as input data
    gain = np.float64(dataset.iloc[:, -5].values)[0]
    volume = np.float64(dataset.iloc[:, -3].values)[0]

    X3 = dataset.iloc[:, -1].values

    # Initialize X
    X_re = np.empty([DATA_RANGE, NUM_SAMPLES_IN+2])
    X_im = np.empty([DATA_RANGE, NUM_SAMPLES_IN+2])

    # Set output FFT
    Y1 = dataset.iloc[:, 2].values

    # Initialize real and imag array of output FFT
    Y_re = np.empty([DATA_RANGE, NUM_SAMPLES_OUT])
    Y_im = np.empty([DATA_RANGE, NUM_SAMPLES_OUT])

    Y_test = np.empty([DATA_RANGE, NUM_SAMPLES_OUT], dtype='complex128')
    X_test = np.empty([DATA_RANGE, NUM_SAMPLES_OUT], dtype='complex128')

    print('X and Y initialized')
    print('Filling X and Y with values from database')
    # Convert from string to complex and amplitude
    for i in range(0, len(X3)):

        X_re[i][0] = gain
        X_re[i][1] = volume
        X_im[i][0] = gain
        X_im[i][1] = volume

        for j in range(0, NUM_SAMPLES_OUT):

            Y_re[i][j] = np.real(np.char.replace(Y1[i][j], '', '').astype(np.complex128))
            Y_im[i][j] = np.imag(np.char.replace(Y1[i][j], '', '').astype(np.complex128))
            Y_test[i][j] = np.char.replace(Y1[i][j], '', '').astype(np.complex128)

            if j < NUM_SAMPLES_IN:
                X_re[i][j + 2] = np.real(np.char.replace(X3[i][j], '', '').astype(np.complex128))
                X_im[i][j + 2] = np.imag(np.char.replace(X3[i][j], '', '').astype(np.complex128))
                X_test[i][j] = np.char.replace(X3[i][j], '', '').astype(np.complex128)

    # fig = plt.figure()
    #
    # plt.subplot(2, 1, 1)
    # plt.semilogy(abs(X_test[0]), 'r')
    # plt.title('Original vs Modeled')
    # plt.ylabel('Amplitude')
    #
    # plt.subplot(2, 1, 2)
    # plt.semilogy(abs(Y_test[0]))
    # plt.xlabel('Frequency (Hz)')
    # plt.ylabel('Amplitude')
    #
    # plt.show()
    # Fit model
    print('Fit model')
    model_real.fit(X_re, Y_re, batch_size=DATA_RANGE, epochs=12)
    model_imag.fit(X_im, Y_im, batch_size=DATA_RANGE, epochs=6)
    #
    # y_pred_im = model_imag.predict(X_im[cnt:cnt+1])
    # y_pred_re = model_real.predict(X_re[cnt:cnt+1])
    #
    # y_pred = np.empty([NUM_SAMPLES], dtype='complex128')
    # y_meas = np.empty([NUM_SAMPLES], dtype='complex128')
    #
    # for i in range(0, NUM_SAMPLES):
    #     y_pred[i] = y_pred_re[0][i] + 1j * y_pred_im[0][i]
    #     y_meas[i] = Y_re[cnt][i] + 1j * Y_im[cnt][i]
    #
    # fig = plt.figure()
    #
    # plt.subplot(2, 1, 1)
    # plt.semilogy(abs(y_meas), 'r')
    # plt.title('Measured Output VS Predicted Output')
    # plt.ylabel('Amplitude')
    #
    # plt.subplot(2, 1, 2)
    # plt.semilogy(abs(y_pred))
    # plt.xlabel('Frequency (Hz)')
    # plt.ylabel('Amplitude')
    #
    # filename = 'g{0}v{1}f{2}a{3}'.format(str(gain), str(volume), str(f[cnt]), str(amp)).replace('.', '_')
    # plt.savefig('/home/jangia/Documents/Mag/MaisterAmpSim/neural_network/plots/{0}.png'.format(filename))
    #
    # plt.close(fig)

    cnt += 1

    if cnt == 25:
        for h in range(0, len(X_im)):
            # Predicting the Test set results
            y_pred_im = model_imag.predict(X_im[h:h + 1])
            y_pred_re = model_real.predict(X_re[h:h + 1])

            y_pred = np.empty([NUM_SAMPLES_OUT], dtype='complex128')
            y_meas = np.empty([NUM_SAMPLES_OUT], dtype='complex128')

            for i in range(0, NUM_SAMPLES_OUT):
                y_pred[i] = y_pred_re[0][i] + 1j * y_pred_im[0][i]
                y_meas[i] = Y_re[h][i] + 1j * Y_im[h][i]

            fig = plt.figure()

            plt.subplot(2, 1, 1)
            plt.semilogy(abs(y_meas), 'r')
            plt.title('Measured Output VS Predicted Output')
            plt.ylabel('Amplitude')

            plt.subplot(2, 1, 2)
            plt.semilogy(abs(y_pred))
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Amplitude')

            filename = 'g{0}v{1}f{2}a{3}'.format(str(gain), str(volume), str(f[h]), str(amp)).replace('.', '_')
            plt.savefig('/home/jangia/Documents/Mag/MaisterAmpSim/neural_network/plots/{0}.png'.format(filename))

            plt.close(fig)

    print('Finished at: ' + str(datetime.datetime.now()))

# Predicting the Test set results
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath('audio_processing.py')))
REC_PATH = os.path.join(BASE_DIR, 'guitar', 'sine.wav')
rate, audio_data = wav.read(os.path.join(BASE_DIR, REC_PATH))

FS = 48000
T_END = 1

f = 440 * (2 ** (1 / 12)) ** 0
t = np.arange(FS * T_END)
chunk = 0.5 * np.sin(2 * np.pi * f * t / FS)
fft_data = fft(chunk[:40000])[:NUM_SAMPLES_IN]

# fft_data = fft(audio_data[40000:60000])[:10000]

fft_data_re = np.empty([1, NUM_SAMPLES_IN + 2])
fft_data_re[0][0] = np.float64(4)
fft_data_re[0][1] = np.float64(4)
fft_data_re[0][2:] = np.real(fft_data)

fft_data_imag = np.empty([1, NUM_SAMPLES_IN + 2])
fft_data_imag[0][0] = np.float64(4)
fft_data_imag[0][1] = np.float64(4)
fft_data_imag[0][2:] = np.imag(fft_data)

y_pred_im = model_imag.predict(fft_data_imag)
y_pred_re = model_real.predict(fft_data_re)

y_pred = np.empty([NUM_SAMPLES_OUT], dtype='complex128')
y_meas = fft_data

for i in range(0, NUM_SAMPLES_OUT):
    y_pred[i] = y_pred_re[0][i] + 1j * y_pred_im[0][i]

fig = plt.figure()

plt.subplot(2, 1, 1)
plt.semilogy(abs(y_meas), 'r')
plt.title('Original vs Modeled')
plt.ylabel('Amplitude')

plt.subplot(2, 1, 2)
plt.semilogy(abs(y_pred))
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude')

filename = 'guitar'
plt.savefig('/home/jangia/Documents/Mag/AudioSystemModel/neural_network/plots/{0}.png'.format(filename))

plt.close(fig)

wav.write('/home/jangia/Documents/Mag/AudioSystemModel/guitar/test_model.wav', 48000, np.real(ifft(y_pred)))
# serialize model to JSON
BASE_DIR = os.path.dirname(os.path.abspath('test_model_amp_complex.py'))
model_real.save(os.path.join(BASE_DIR, 'models', 'test_model_real.h5'))
model_imag.save(os.path.join(BASE_DIR, 'models', 'test_model_imag.h5'))
