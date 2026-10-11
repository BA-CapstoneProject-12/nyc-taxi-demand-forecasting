"""Training-only temporal diagnostics. Never decompose test data for fitting."""
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import periodogram
from statsmodels.tsa.seasonal import MSTL
from statsmodels.tsa.stattools import acf, pacf, adfuller, kpss
from .config import TABLES, FIGURES, TARGET, SERIES

plt.rcParams.update({"figure.dpi":120,"savefig.dpi":160,"axes.spines.top":False,
                     "axes.spines.right":False,"axes.grid":True,"grid.alpha":0.18,
                     "font.size":10,"figure.facecolor":"#f7f9fc","axes.facecolor":"#f7f9fc"})

def savefig(name):
    plt.tight_layout()
    plt.savefig(FIGURES/name,bbox_inches="tight")
    plt.close()

def diagnose(hourly):
    stationarity=[]; strengths=[]; correlations=[]; spectra=[]; anomalies=[]; components=[]
    fig, axes=plt.subplots(3,2,figsize=(14,10))
    for ax,sid in zip(axes.flat,SERIES):
        frame=hourly[hourly.series_id.eq(sid)].sort_values("ds").set_index("ds")
        train=frame.loc[frame.split.eq("train"),TARGET]
        y=np.log1p(train)
        result=MSTL(y,periods=(24,168),stl_kwargs={"robust":True}).fit()
        comp=pd.DataFrame({"ds":train.index,"series_id":sid,"log_target":y.to_numpy(),
                           "trend":np.asarray(result.trend),"daily":result.seasonal.iloc[:,0].to_numpy(),
                           "weekly":result.seasonal.iloc[:,1].to_numpy(),"residual":np.asarray(result.resid)})
        components.append(comp)
        resid=np.asarray(result.resid)
        for name,part in [("trend",result.trend),("daily",result.seasonal.iloc[:,0]),("weekly",result.seasonal.iloc[:,1])]:
            strengths.append(dict(series_id=sid,component=name,strength=max(0,1-np.var(resid)/np.var(resid+np.asarray(part)))))
        for name,values in [("level",train),("log1p",y),("log_diff_24",y.diff(24).dropna()),
                            ("log_diff_168",y.diff(168).dropna()),("log_diff_168_1",y.diff(168).diff().dropna())]:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                adf=adfuller(values,maxlag=24,autolag="AIC")
                kp=kpss(values,regression="c",nlags="auto")
            stationarity.append(dict(series_id=sid,transformation=name,n=len(values),
                                     adf_stat=adf[0],adf_p=adf[1],adf_lags=adf[2],
                                     kpss_stat=kp[0],kpss_p=kp[1],kpss_lags=kp[2],
                                     both_support_stationarity=adf[1]<.05 and kp[1]>.05,
                                     warnings=" | ".join(str(w.message) for w in caught)))
        ac=acf(y,nlags=336,fft=True); pa=pacf(y,nlags=48,method="ywm")
        correlations.extend(dict(series_id=sid,lag=i,acf=v,pacf=pa[i] if i<len(pa) else np.nan) for i,v in enumerate(ac))
        freq,power=periodogram(y,fs=1,detrend="linear")
        valid=freq>0
        spec=pd.DataFrame({"series_id":sid,"period_hours":1/freq[valid],"power":power[valid]})
        spectra.append(spec)
        center=np.median(resid); mad=np.median(np.abs(resid-center))
        score=.67448975*(resid-center)/max(mad,1e-12)
        abnormal=comp.loc[np.abs(score)>4,["ds","series_id","residual"]].copy()
        abnormal["robust_z"]=score[np.abs(score)>4]
        anomalies.append(abnormal)
        ax.plot(frame.index,frame[TARGET].rolling(24).mean(),lw=1,color="#1f6e8c")
        ax.axvline(frame.index[frame.split.eq("validation")][0],color="#dd9a20",ls="--",label="Validation")
        ax.axvline(frame.index[frame.split.eq("test")][0],color="#d04a4a",ls="--",label="Test")
        ax.set_title(sid+" | 24-hour moving mean"); ax.tick_params(axis="x",rotation=25)
    axes[0,0].legend(fontsize=8)
    fig.suptitle("Demand history and fixed evaluation boundaries",fontsize=17,y=1.02)
    savefig("01_series_overview.png")
    comp=pd.concat(components,ignore_index=True)
    comp.to_csv(TABLES/"mstl_components.csv",index=False,float_format="%.7g")
    pd.DataFrame(stationarity).to_csv(TABLES/"stationarity.csv",index=False)
    pd.DataFrame(strengths).to_csv(TABLES/"seasonal_strength.csv",index=False)
    corr=pd.DataFrame(correlations); corr.to_csv(TABLES/"acf_pacf.csv",index=False)
    pd.concat(spectra).to_csv(TABLES/"periodogram.csv",index=False)
    pd.concat(anomalies).sort_values("robust_z",key=abs,ascending=False).to_csv(TABLES/"training_anomalies.csv",index=False)
    city=comp[comp.series_id.eq("All zones")].set_index("ds")
    fig,axes=plt.subplots(5,1,figsize=(14,12),sharex=True)
    for ax,col,color in zip(axes,["log_target","trend","daily","weekly","residual"],
                            ["#263859","#1f6e8c","#2e9479","#dd9a20","#bc4749"]):
        ax.plot(city.index,city[col],color=color,lw=.8); ax.set_ylabel(col)
    axes[0].set_title("MSTL: daily + weekly seasonality | training data only",fontsize=16)
    savefig("02_mstl_decomposition.png")
    citycorr=corr[corr.series_id.eq("All zones")]
    spec=spectra[0]
    fig,axes=plt.subplots(1,3,figsize=(16,4))
    axes[0].plot(citycorr.lag,citycorr.acf); axes[0].set(title="Log demand ACF",xlabel="Lag (hours)")
    axes[1].stem(citycorr.lag[:49],citycorr.pacf[:49],basefmt=" "); axes[1].set(title="PACF",xlabel="Lag (hours)")
    axes[2].plot(spec.period_hours,spec.power); axes[2].set(xlim=(2,350),title="Spectral power",xlabel="Period (hours)")
    for period in (24,168): axes[2].axvline(period,color="#d04a4a",ls="--")
    savefig("03_dependence_spectrum.png")
    train=hourly[hourly.split.eq("train")].copy()
    train["day_of_week"]=train.ds.dt.dayofweek; train["hour"]=train.ds.dt.hour
    weekly=train.groupby(["series_id","day_of_week","hour"])[TARGET].mean().reset_index()
    weekly.to_csv(TABLES/"training_weekly_profiles.csv",index=False)
    fig,axes=plt.subplots(3,2,figsize=(14,10))
    for ax,sid in zip(axes.flat,SERIES):
        p=weekly[weekly.series_id.eq(sid)].pivot(index="day_of_week",columns="hour",values=TARGET)
        im=ax.imshow(p,aspect="auto",cmap="YlGnBu")
        ax.set(title=sid,xlabel="Hour",yticks=range(7),yticklabels=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
        fig.colorbar(im,ax=ax,label="Pickups/hour")
    savefig("04_weekly_heatmaps.png")
    print("Training diagnostics and four figures saved",flush=True)

