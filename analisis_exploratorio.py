target_file="./SHOOT.2008-11-14T07:09:03.690.fits"
from astropy.io import fits

with fits.open(target_file) as obs:
    hdr = dict(obs[0].header)
    for k,v in hdr.items():
        print("%s: %s" % (k,str(v)))