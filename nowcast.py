from pysteps.utils import transformation
from pysteps import motion, nowcasts
import glob
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import matplotlib
import numpy as np
import imageio.v2 as imageio
import os
import datetime
import time

def converter(arr):
    #turn radar composite image into mm hr^{-1}
    new = np.zeros((500,500))
    new = np.where(arr[:,:,2]==254,0.25,new)
    new = np.where((arr[:,:,2]==254)&(arr[:,:,1]==101),0.75,new)
    new = np.where((arr[:,:,2]==0)&(arr[:,:,1]==127),1.5,new)
    new = np.where((arr[:,:,2]==0)&(arr[:,:,1]==203),3,new)
    new = np.where((arr[:,:,2]==0)&(arr[:,:,1]==152),6,new)
    new = np.where((arr[:,:,1]==0)&(arr[:,:,0]==254),12,new)
    new = np.where((arr[:,:,2]==254)&(arr[:,:,0]==254),24,new)
    new = np.where((arr[:,:,2]==224)&(arr[:,:,1]==223),np.nan,new)
    return new

def plot_radar(data,title,fname,north=True,towns=True):
    if north:
        fig = plt.figure(figsize=(7,5),layout='constrained')
    else:
        fig = plt.figure(figsize=(7,7),layout='constrained')
    proj = ccrs.epsg(3857)
    ax=fig.add_subplot(111,projection=proj)
    img_extent = [-12,5,48.5,61.5]
    if north:
        ax.set_extent([-4, 0, 53, 55])
    else:
        ax.set_extent(img_extent)
    ax.coastlines(alpha=.8)
    n=ax.imshow(data,norm=matplotlib.colors.LogNorm(vmin=0.1,vmax=32),
                   extent=img_extent,transform=ccrs.PlateCarree(),cmap=cmap)
    ax.set_title(title)
    fig.colorbar(n,label='Precipitation rate (mm hr$^{-1}$)',ax=ax,ticks=[0.1,1,10,20,30],format='%.2f')    #plt.colorbar(n,ax=ax)
    
    if towns:
        if north:
            locs = pd.read_csv('csv/gb_north.csv')
        else:
            locs = pd.read_csv('csv/gb2.csv')
        xs_towns = list(locs['lng'])
        ys_towns = list(locs['lat'])
        labels = list(locs['city'])
        i=0
        ax.scatter(xs_towns,ys_towns,transform=ccrs.PlateCarree(),zorder=8,c='k')
        while i<len(labels):
            ax.text(xs_towns[i]+0.05,ys_towns[i]-0.01,labels[i],transform=ccrs.PlateCarree(),zorder=20)
            i=i+1
    
    plt.savefig(fname,bbox_inches='tight')
    plt.close()

#delete clutter
old_files = os.listdir('gif/')
for f in old_files:
    os.remove('gif/'+f)


#get available obs (in time order)
year = datetime.datetime.now().strftime('%Y')
base = 'data/'+year+'/*/*/*'
filenames=glob.glob(base)
fnames=[]
images=[]
i=0
for filename in sorted(filenames):
    if '.png' in filename:
        fnames.append(filename)
        images.append(converter(imageio.imread(filename)))
test=converter(imageio.imread(filename))
train = np.array(images)

# Log-transform the data to dBR.
# The threshold of 0.1 mm/h sets the fill value to -15 dBR.
train_precip_dbr, metadata_dbr = transformation.dB_transform(
    train, threshold=0.1, zerovalue=-15.0
)

# Import the Lucas-Kanade optical flow algorithm
oflow_method = motion.get_method("LK")

# Estimate the motion field from the training data (in dBR)
motion_field = oflow_method(train)

start = time.time()
# Extrapolate the last radar observation
extrapolate = nowcasts.get_method("extrapolation")
# You can use the precipitation observations directly in mm/h for this step.
last_observation = test

# We set the number of leadtimes (the length of the forecast horizon) to the
# length of the observed/verification preipitation data. In this way, we'll get
# a forecast that covers these time intervals.

vals=12 #(3 hours)
# Advect the most recent radar rainfall field and make the nowcast.
precip_forecast = extrapolate(test, motion_field, vals)

# This shows the shape of the resulting array with [time intervals, rows, cols]

from string import Template

class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)

cmap = 'Blues'
towns = True
north = True

def mask(arr):
    new = np.where((arr[:,:,2]==193)&(arr[:,:,1]==191),0,1)
    new = np.flip(new,axis=0)
    return new

#plot each observation as mmhr^{-1}
for j in range(len(images)):
    ftime = datetime.datetime.strptime(fnames[j][-21:],'%Y-%m-%dT%H%M%S.png')
    last = datetime.datetime.strptime(fnames[-1][-21:],'%Y-%m-%dT%H%M%S.png')
    tdelta = last-ftime
    valid = (ftime).strftime('%Y-%m-%dT%H:%MZ')
    if j==len(images)-1:
        title = 'Precipitation observation\n Valid '+valid+' (T+'+strfdelta(tdelta,'%H:%M')+')'
    else:    
        title = 'Precipitation observation\n Valid '+valid+' (T-'+strfdelta(tdelta,'%H:%M')+')'
    jj = f'{j:02}'
    fname = 'gif/obs_'+jj+'.png'
    plot_radar(train[j],title,fname,north,towns)
    

#now plot each nowcast 
for j in range(vals):
    tdelta = datetime.timedelta(minutes = 15*(j+1))
    valid = (ftime+tdelta).strftime('%Y-%m-%dT%H:%MZ')
    title = 'Precipitation nowcast\n Valid '+valid+' (T+'+strfdelta(tdelta,'%H:%M')+')'
    jj = f'{(j+1):02}'
    fname = 'gif/'+jj+'.png'
    plot_radar(precip_forecast[j],title=title,fname=fname,north=north,towns=towns)
    
#make animated gif
ofnames=sorted(os.listdir('gif/'))
stills=[]
for f in sorted(ofnames):
   if '.png' in f: 
    stills.append(imageio.imread('gif/'+f))
imageio.mimsave('gif2/forecast_today.gif', stills, duration=2,loop=0)