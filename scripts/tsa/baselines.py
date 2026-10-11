"""Seasonal forecasts built exclusively from observations before the origin."""
import numpy as np

def seasonal_naive(history,horizon,period):
    y=np.asarray(history,dtype=float)
    if len(y)<period:
        raise ValueError("Not enough seasonal history")
    return y[-period:][np.arange(horizon)%period]

def seasonal_mean(history,horizon,period=168,weeks=4):
    y=np.asarray(history,dtype=float)
    if len(y)<period*weeks:
        raise ValueError("Not enough history for seasonal averaging")
    profile=y[-period*weeks:].reshape((weeks,period)+y.shape[1:]).mean(axis=0)
    return profile[np.arange(horizon)%period]

def adaptive_week(history,horizon):
    """Average four weeks, then damp a recent level correction over 48 hours."""
    y=np.asarray(history,dtype=float)
    base=seasonal_mean(y,horizon)
    expected=np.mean([y[-24-period:-period].mean(axis=0) for period in (168,336,504,672)],axis=0)
    # Shrink low-count ratios with one pickup/hour; cap shock extrapolation.
    ratio=np.clip((y[-24:].mean(axis=0)+1)/(expected+1),.5,1.5)
    decay=np.exp(-np.arange(1,horizon+1)/48)
    if y.ndim==2: decay=decay[:,None]
    return base*(1+(ratio-1)*decay)

def tsb(history,horizon,alpha=.1,beta=.05):
    """Teunter-Syntetos-Babai: smoothed occurrence probability x positive size."""
    y=np.asarray(history,dtype=float)
    if y.ndim==1: y=y[:,None]
    probability=(y[0]>0).astype(float)
    size=np.where(y[0]>0,y[0],1.)
    for value in y[1:]:
        occurrence=value>0
        probability+=beta*(occurrence-probability)
        size=np.where(occurrence,size+alpha*(value-size),size)
    return np.repeat((probability*size)[None,:],horizon,axis=0)
