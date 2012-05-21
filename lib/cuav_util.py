#!/usr/bin/env python
'''common CanberraUAV utility functions'''

import numpy, cv, math, sys, os, time

radius_of_earth = 6378100.0 # in meters

class PGMError(Exception):
	'''PGMLink error class'''
	def __init__(self, msg):
            Exception.__init__(self, msg)


class PGM(object):
	'''8/16 bit 1280x960 PGM image handler'''
	def __init__(self, filename):
		self.filename = filename
        
		f = open(filename, mode='r')
		fmt = f.readline()
		if fmt.strip() != 'P5':
			raise PGMError('Expected P5 image in %s' % filename)
		dims = f.readline()
		if dims.strip() != '1280 960':
			raise PGMError('Expected 1280x960 image in %s' % filename)
		line = f.readline()
		self.comment = None
		if line[0] == '#':
			self.comment = line
			line = f.readline()
		line = line.strip()
		if line == "65535":
			self.eightbit = False
		elif line == "255":
			self.eightbit = True
		else:
			raise PGMError('Expected 8/16 bit image image in %s - got %s' % (filename, line))
		ofs = f.tell()
		f.close()
		if self.eightbit:
			rawdata = numpy.memmap(filename, dtype='uint8', mode='c', order='C', shape=(960,1280), offset=ofs)
			self.img = cv.CreateImageHeader((1280, 960), 8, 1)
		else:
			rawdata = numpy.memmap(filename, dtype='uint16', mode='c', order='C', shape=(960,1280), offset=ofs)
			self.img = cv.CreateImageHeader((1280, 960), 16, 1)
		self.rawdata = rawdata.copy()
		del(rawdata)
		self.array = self.rawdata.byteswap(True)
		cv.SetData(self.img, self.array.tostring(), self.array.dtype.itemsize*1*1280)

def key_menu(i, n, image, filename, pgm=None):
    '''simple keyboard menu'''
    while True:
        key = cv.WaitKey()
	key &= 0xFF
        if not key in range(128):
            continue
        key = chr(key)
        if key == 'q':
            sys.exit(0)
        if key == 's':
            print("Saving %s" % filename)
            cv.SaveImage(filename, image)
        if key == 'c' and pgm is not None:
            print("Comment: %s" % pgm.comment)
        if key in ['n', '\n', ' ']:
            if i == n-1:
                print("At last image")
            else:
                return i+1
        if key == 'b':
            if i == 0:
                print("At first image")
            else:
                return i-1


def gps_distance(lat1, lon1, lat2, lon2):
	'''return distance between two points in meters,
	coordinates are in degrees
	thanks to http://www.movable-type.co.uk/scripts/latlong.html'''
	from math import radians, cos, sin, sqrt, atan2
	lat1 = radians(lat1)
	lat2 = radians(lat2)
	lon1 = radians(lon1)
	lon2 = radians(lon2)
	dLat = lat2 - lat1
	dLon = lon2 - lon1
	
	a = sin(0.5*dLat)**2 + sin(0.5*dLon)**2 * cos(lat1) * cos(lat2)
	c = 2.0 * atan2(sqrt(a), sqrt(1.0-a))
	return radius_of_earth * c


def gps_bearing(lat1, lon1, lat2, lon2):
	'''return bearing between two points in degrees, in range 0-360
	thanks to http://www.movable-type.co.uk/scripts/latlong.html'''
	from math import sin, cos, atan2, radians, degrees
	lat1 = radians(lat1)
	lat2 = radians(lat2)
	lon1 = radians(lon1)
	lon2 = radians(lon2)
	dLat = lat2 - lat1
	dLon = lon2 - lon1    
	y = sin(dLon) * cos(lat2)
	x = cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(dLon)
	bearing = degrees(atan2(y, x))
	if bearing < 0:
		bearing += 360.0
	return bearing


def gps_newpos(lat, lon, bearing, distance):
	'''extrapolate latitude/longitude given a heading and distance 
	thanks to http://www.movable-type.co.uk/scripts/latlong.html
	'''
	from math import sin, asin, cos, atan2, radians, degrees

	lat1 = radians(lat)
	lon1 = radians(lon)
	brng = radians(bearing)
	dr = distance/radius_of_earth

	lat2 = asin(sin(lat1)*cos(dr) +
		    cos(lat1)*sin(dr)*cos(brng))
	lon2 = lon1 + atan2(sin(brng)*sin(dr)*cos(lat1), 
			    cos(dr)-sin(lat1)*sin(lat2))
	return (degrees(lat2), degrees(lon2))



def angle_of_view(lens=4.0, sensorwidth=5.0):
    '''
    return angle of view in degrees of the lens

    sensorwidth is in millimeters
    lens is in mm
    '''
    return math.degrees(2.0*math.atan((sensorwidth/1000.0)/(2.0*lens/1000.0)))

def groundwidth(height, lens=4.0, sensorwidth=5.0):
    '''
    return frame width on ground in meters

    height is in meters
    sensorwidth is in millimeters
    lens is in mm
    '''
    aov = angle_of_view(lens=lens, sensorwidth=sensorwidth)
    return 2.0*height*math.tan(math.radians(0.5*aov))


def pixel_width(height, xresolution=1280, lens=4.0, sensorwidth=5.0):
    '''
    return pixel width on ground in meters

    height is in meters
    xresolution is in pixels
    lens is in mm
    sensorwidth is in mm
    '''
    return groundwidth(height, lens=lens, sensorwidth=sensorwidth)/xresolution

def pixel_height(height, yresolution=960, lens=4.0, sensorwidth=5.0):
    '''
    return pixel height on ground in meters

    height is in meters
    yresolution is in pixels
    lens is in mm
    sensorwidth is in mm
    '''
    return groundwidth(height, lens=lens, sensorwidth=sensorwidth)/yresolution


def ground_offset(height, pitch, roll, yaw):
    '''
    find the offset on the ground in meters of the center of view of the plane
    given height above the ground in meters, and pitch/roll/yaw in degrees.

    The yaw is from grid north. Positive yaw is clockwise
    The roll is from horiznotal. Positive roll is down on the right
    The pitch is from horiznotal. Positive pitch is up in the front

    return result is a tuple, with meters east and north of GPS position

    This is only correct for small values of pitch/roll
    '''

    # x/y offsets assuming the plane is pointing north
    xoffset = -height * math.tan(math.radians(roll))
    yoffset = height * math.tan(math.radians(pitch))

    # convert to polar coordinates
    distance = math.hypot(xoffset, yoffset)
    angle    = math.atan2(yoffset, xoffset)

    # add in yaw
    angle -= math.radians(yaw)

    # back to rectangular coordinates
    x = distance * math.cos(angle)
    y = distance * math.sin(angle)

    return (x, y)


def pixel_position(xpos, ypos, height, pitch, roll, yaw,
                   lens=4.0, sensorwidth=5.0, xresolution=1280, yresolution=960):
    '''
    find the offset on the ground in meters of a pixel in a ground image
    given height above the ground in meters, and pitch/roll/yaw in degrees, the
    lens and image parameters

    The xpos,ypos is from the top-left of the image
    The height is in meters
    
    The yaw is from grid north. Positive yaw is clockwise
    The roll is from horiznotal. Positive roll is down on the right
    The pitch is from horiznotal. Positive pitch is up in the front
    lens is in mm
    sensorwidth is in mm
    xresolution and yresolution is in pixels
    
    return result is a tuple, with meters east and north of current GPS position

    This is only correct for small values of pitch/roll
    '''
    
    (xcenter, ycenter) = ground_offset(height, pitch, roll, yaw)
    
    px = pixel_width(height, xresolution=xresolution, lens=lens, sensorwidth=sensorwidth)
    py = pixel_height(height, yresolution=yresolution, lens=lens, sensorwidth=sensorwidth)

    dx = (xresolution/2) - xpos
    dy = (yresolution/2) - ypos

    range_c = math.hypot(dx * px, dy * py)
    angle_c = math.atan2(dy * py, dx * px)

    # add in yaw
    angle_c += math.radians(yaw)

    # back to rectangular coordinates
    x = - range_c * math.cos(angle_c)
    y = range_c * math.sin(angle_c)

    return (xcenter+x, ycenter+y)


def pixel_coordinates(xpos, ypos, latitude, longitude, height, pitch, roll, yaw,
                      lens=4.0, sensorwidth=5.0, xresolution=1280, yresolution=960):
    '''
    find the latitude/longitude of a pixel in a ground image given
    our GPS position, our height above the ground in meters, and pitch/roll/yaw in degrees,
    the lens and image parameters

    The xpos,ypos is from the top-left of the image
    latitude is in degrees. Negative for south
    longitude is in degrees
    The height is in meters
    
    The yaw is from grid north. Positive yaw is clockwise
    The roll is from horiznotal. Positive roll is down on the right
    The pitch is from horiznotal. Positive pitch is up in the front
    lens is in mm
    sensorwidth is in mm
    xresolution and yresolution is in pixels
    
    return result is a tuple, with meters east and north of current GPS position

    This is only correct for small values of pitch/roll
    '''

    (xofs, yofs) = pixel_position(xpos, ypos, height, pitch, roll, yaw,
                                  lens=lens, sensorwidth=sensorwidth,
                                  xresolution=xresolution, yresolution=yresolution)

    bearing = math.degrees(math.atan2(xofs, yofs))
    distance = math.sqrt(xofs**2 + yofs**2)
    return gps_newpos(latitude, longitude, bearing, distance)

def gps_position_from_image_region(region, pos, width=640, height=480):
	'''return a GPS position in an image given a MavPosition object
	and an image region tuple'''
	(x1,y1,x2,y2) = region
	x = (x1+x2)*0.5
	y = (y1+y2)*0.5
	return pixel_coordinates(x, y, pos.lat, pos.lon, pos.altitude,
				 pos.pitch, pos.roll, pos.yaw,
				 xresolution=width, yresolution=height)

def mkdir_p(dir):
    '''like mkdir -p'''
    if not dir:
        return
    if dir.endswith("/"):
        mkdir_p(dir[:-1])
        return
    if os.path.isdir(dir):
        return
    mkdir_p(os.path.dirname(dir))
    try:
        os.mkdir(dir)
    except Exception:
        pass

def frame_time(t):
    '''return a time string for a filename with 0.01 sec resolution'''
    hundredths = int(t * 100.0) % 100
    return "%s%02u" % (time.strftime("%Y%m%d%H%M%S", time.localtime(t)), hundredths)

def parse_frame_time(filename):
	'''parse a image frame time from a image filename
	from the chameleon capture code'''
	filename = os.path.basename(filename)
	i = filename.find('201')
	if i == -1:
		raise RuntimeError('unable to parse filename into time')
	tstring = filename[i:]
	t = time.mktime(time.strptime(tstring[:14], "%Y%m%d%H%M%S"))
	# hundredths can be after a dash
	if tstring[14] == '-':
		hundredths = int(tstring[15:17])
	else:
		hundredths = int(tstring[14:16])
	t += hundredths * 0.01
	return t


def polygon_outside(P, V):
	'''return true if point is outside polygon
	P is a (x,y) tuple
	V is a list of (x,y) tuples
	'''
	n = len(V)
	outside = True
	j = n-1
	for i in range(n-1):
		if (((V[i][1]>P[1]) != (V[j][1]>P[1])) and
		    (P[0] < (V[j][0]-V[i][0]) * (P[1]-V[i][1]) / (V[j][1]-V[i][1]) + V[i][0])):
			outside = not outside
		j = i
	return outside


def polygon_load(filename):
	'''load a polygon from a file'''
	ret = []
        f = open(filename)
        for line in f:
		if line.startswith('#'):
			continue
		line = line.strip()
		if not line:
			continue
		a = line.split()
		if len(a) != 2:
			raise RuntimeError("invalid polygon line: %s" % line)
		ret.append((float(a[0]), float(a[1])))
        f.close()
	return ret


def polygon_complete(V):
	'''
	check if a polygon is complete. 

	We consider a polygon to be complete if we have at least 4 points,
	and the first point is the same as the last point. That is the
	minimum requirement for the polygon_outside function to work
	'''
	return (len(V) >= 4 and V[-1][0] == V[0][0] and V[-1][1] == V[0][1])



if __name__ == "__main__":
	pos1 = (-35.36048084339494,  149.1647973335984)
	pos2 = (-35.36594385616202,  149.1656758119368)
	dist = gps_distance(pos1[0], pos1[1],
			    pos2[0], pos2[1])
	bearing = gps_bearing(pos1[0], pos1[1],
			      pos2[0], pos2[1])
	print 'distance %f m' % dist
	print 'bearing %f degrees' % bearing
	pos3 = gps_newpos(pos1[0], pos1[1],
			  bearing, dist)
	err = gps_distance(pos2[0], pos2[1],
			   pos3[0], pos3[1])
	if math.fabs(err) > 0.01:
		raise RuntimeError('coordinate error too large')
	print 'error %f m' % err

	print('Testing polygon_outside()')
	'''
	this is the boundary of the 2010 outback challenge
	Note that the last point must be the same as the first for the
	polygon_outside() algorithm
	'''
	
	OBC_boundary = polygon_load(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'OBC_boundary.txt'))
	test_points = [
		(-26.6398870, 151.8220000, True ),
		(-26.6418700, 151.8709260, False ),
		(-350000000, 1490000000, True ),
		(0, 0,                   True ),
		(-26.5768150, 151.8408250, False ),
		(-26.5774060, 151.8405860, True ),
		(-26.6435630, 151.8303440, True ),
		(-26.6435650, 151.8313540, False ),
		(-26.6435690, 151.8303530, False ),
		(-26.6435690, 151.8303490, True ),
		(-26.5875990, 151.8344049, True ),
		(-26.6454781, 151.8820530, True ),
		(-26.6454779, 151.8820530, True ),
		(-26.6092109, 151.8747420, True ),
		(-26.6092111, 151.8747420, False ),
		(-26.6092110, 151.8747421, True ),
		(-26.6092110, 151.8747419, False ),
		(-26.6092111, 151.8747421, True ),
		(-26.6092109, 151.8747421, True ),
		(-26.6092111, 151.8747419, False )
		]
	if not polygon_complete(OBC_boundary):
		raise RuntimeError('OBC_boundary invalid')
	for lat, lon, outside in test_points:
		if outside != polygon_outside((lat, lon), OBC_boundary):
			raise RuntimeError('OBC_boundary test error', lat, lon)
			