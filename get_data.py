#get precipitation obs from DataPoint

import requests
import os
import shutil
import urllib

#open API key (stored as text file)
with open('API_KEY.txt','r') as f:
    key2=f.read()

#clear downloaded data
shutil.rmtree('data/')

#get available files
link = 'http://datapoint.metoffice.gov.uk/public/data/layer/wxobs/all/datatype/capabilities?key='+key2
webpage=urllib.request.urlopen(link).read()
capabilities = str(webpage).split('RADAR_UK_Composite_Highres')

times = capabilities[1].split('<Time>')
#get each available radar obs composite image
for t in times[1:]:
    t2 = t.split('</Time>')[0]
    t_win = t2.replace(':','')
    base = 'data/'+t_win[0:4]+'/'+t_win[5:7]+'/'+t_win[8:10]+'/'
    if not os.path.isdir(base):
        os.makedirs(base)
    fname = t_win+'.png'
    #if file not in data directory, get from API
    if not fname in os.listdir(base):
        link_radar = 'http://datapoint.metoffice.gov.uk/public/data/layer/wxobs/RADAR_UK_Composite_Highres/png?TIME='+t2+'Z&key='+key2
        img_data = requests.get(link_radar).content
        print(base+fname)
        with open(base+fname, 'wb') as handler:
            handler.write(img_data)
