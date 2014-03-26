#!/usr/bin/env python

# Generate speed/bearing info from gpx to annotate a video 
# Put together by Michael Cassera

# Mapping help by ossum: http://www.instructables.com/id/Animated-Watercolour-Map-for-Cycle-TourRace-Video/

import math
import logging
import sys
import gpxpy
import gpxpy.gpx
import time
import os
import datetime
import subprocess
import os.path
import urllib


### Function to Read in trace from GPX ###
def traceImportGPX(fname):
    import re
    trace = []
    for line in open(fname,'r'):
        # This will match "lat" and "lon" flags as long as they are on the same line.
        # Does not differentiate between trkpt and other points,so make sure that 
        # the file is just the track you are interested in.
        matchLat = re.search(r'.* lat=\"(\S*)\".*',line)
        matchLon = re.search(r'.* lon=\"(\S*)\".*',line)                
        if matchLat != None and matchLon != None:
            lat = matchLat.group(1)
            lon = matchLon.group(1)
            trace.append([float(lat),float(lon)])
            #print trace
            #time.sleep(1)

    return trace

### Function to get trace boundries ###
def traceBoundaries(trace):

    lat = zip(*trace)[0]
    lon = zip(*trace)[1]

    return {"north":max(lat),"south":min(lat),"east":max(lon),"west":min(lon)}


### Function to convert lat,lon degrees to tile x/y number ### 
def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
  return (xtile, ytile)

### Function to convert xy tile to NW corner of tile ###
def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)

### Determine tile range given boundaries and zoom ###
def determineTileRange(boundaries,zoom):
    Xmax,Ymin = deg2num(boundaries["north"],boundaries["east"],zoom)
    Xmin,Ymax = deg2num(boundaries["south"],boundaries["west"],zoom)
    return {"xMin":Xmin,"xMax":Xmax,"yMin":Ymin,"yMax":Ymax}

### Take a tile range and download them (if not locally present) ###
def getTiles(xyRange,zoom):
    #set acive directory to that of the script
    currentdir = os.curdir
    tileDir = os.path.join(currentdir,"tiles")

    tileServerUrl = "http://tile.stamen.com/terrain/"

    #create a list of all the x and y coordinates to download
    xRange = range(xyRange["xMin"],xyRange["xMax"]+1)
    yRange = range(xyRange["yMin"],xyRange["yMax"]+1)

    for x in xRange:
        for y in yRange:
            #define the file name
            tileFileName = str(y)+".jpg"

            #define the local path as well as the complete path to the local and remote files
            localPath = os.path.join(tileDir,str(zoom),str(x))
            localFile = os.path.join(localPath,tileFileName)
            remoteFile = tileServerUrl+str(zoom)+"/"+str(x)+"/"+str(y)+".jpg"

            #check if the file exists locally
            if not os.path.isfile(localFile):                
                print "retrieving "+remoteFile
                #if local directory doesn't yet exist, make itluc
                if not os.path.isdir(localPath):
                    os.makedirs(localPath)
                #retrieve the file from the server and save it    
                urllib.urlretrieve(remoteFile,localFile)

### Merge tiles into one image ###
def mergeTiles(xyRange,zoom,filename):
    import Image
    tileSize = 256
    tileDir = os.path.join(os.curdir,"tiles",str(zoom))

    out = Image.new( 'RGB', ((xyRange["xMax"]-xyRange["xMin"]+1) * tileSize, (xyRange["yMax"]-xyRange["yMin"]+1) * tileSize) ) 

    imx = 0;
    for x in range(xyRange["xMin"], xyRange["xMax"]+1):
        imy = 0
        for y in range(xyRange["yMin"], xyRange["yMax"]+1):
            tileFile = os.path.join(tileDir,str(x),str(y)+".jpg")
            tile = Image.open(tileFile)
            out.paste( tile, (imx, imy) )
            imy += tileSize
        imx += tileSize

    out.save(os.path.join(os.curdir,filename))

### Draw Path Image ###
def drawTraceMask(trace,xResolution,yResolution,traceBoundaries,zoom,filename,tColor):
    import Image
    import ImageDraw

    # Get XY number of NW and SE corner tiles
    xy_nw = deg2num(traceBoundaries["north"],traceBoundaries["west"],zoom)
    xy_se = deg2num(traceBoundaries["south"],traceBoundaries["east"],zoom)

    # get lat,lon of corners
    # (since the function returns the NW corner of a tile,
    # we need lat,lon of X+1,Y+1 for the SE corner)
    NW = num2deg(xy_nw[0],xy_nw[1],zoom)
    SE = num2deg(xy_se[0]+1,xy_se[1]+1,zoom)

    # The image boundaries are actually different, because
    # they are the boundaries of the tiles, not the trace
    # define the new boundaries
    mapBoundaries = {}
    mapBoundaries["north"] = NW[0]
    mapBoundaries["south"] = SE[0]
    mapBoundaries["west"] = NW[1]
    mapBoundaries["east"] = SE[1]

    # Offset to ensure that NW corner is 0,0
    latOffset = -(mapBoundaries["north"])
    latDivisor = mapBoundaries["north"]-mapBoundaries["south"]
    lonOffset = -(mapBoundaries["west"])
    lonDivisor = mapBoundaries["east"]-mapBoundaries["west"]

    #out = Image.new( 'RGB', (xResolution, yResolution) )
    out = Image.open("output-map.jpg")
    draw = ImageDraw.Draw(out)
    
    firstRun = True
    for lat,lon in trace:
        # Convert zeroed lat,lon into x,y coordinates
        # this will need correction for northern hemisphere        
        x = abs(int(xResolution*((lon + lonOffset)/lonDivisor)))
        y = abs(int(yResolution*((lat + latOffset)/latDivisor)))

        if firstRun:
            firstRun = False
        else:
            draw.line((x,y,xPrev,yPrev),fill=tColor,width=10)
        xPrev = x
        yPrev = y
    draw.ellipse((x-7,y-7,x+7,y+7),fill="blue")
    del draw
    out.save(os.path.join(os.curdir,filename))
    return (x,y)

### Get modification date (Obsolete)  ###
def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)
 
### Insert the data bar and map onto each frame ###
def insert_annotation(note, fnumber, frames):
	fcount = 0
	outofframes = 0
	while (fcount < frames):
		frname = "tmp/frame"
		if (fnumber < 1000000):
			frname = frname + "0"
		if (fnumber < 100000):
			frname = frname + "0"
		if (fnumber < 10000):
			frname = frname + "0"
		if (fnumber < 1000):
			frname = frname + "0"
		if (fnumber < 100):
			frname = frname + "0"
		if (fnumber < 10):
			frname = frname + "0"
		frname = frname + str(fnumber) + ".jpg"	
		com = "convert -background \'#00000080\' -font Ubuntu-Mono-Bold -pointsize 42 -fill white label:\'" + note + "\' miff:- | composite -gravity south -geometry +0+3 - " + frname + " " + frname
		os.system(com)
		overlayMap = "convert " + frname + " tmp/output.png -composite -format jpg -quality 90 " + frname
		outofframes = os.system(overlayMap)
		fnumber = fnumber + 1
		fcount = fcount + 1
	return fnumber, outofframes
	
### Calculate offset to calibrate video to gps
### uses vlc to run video
### watch video to see when movement starts, enter that info when requested
### will show offset in seconds, can be changed if needed
### poorly written hack	
def Calibrate(startvid,gpxfname,videoname):
	
	gpx_file = open(gpxfname, 'r')
	gpx = gpxpy.parse(gpx_file)
	
	for track in gpx.tracks:
		for segment in track.segments:
			for point in segment.points:

				p5 = point		# One Point
			
				print
				print "         GPS file: ",gpxfname
				print "      Camera file: ",videoname
				print "   GPS start time: ",str(p5.time)
				print "Camera start time: ",startvid
				print
				print "Camera start time needs to match GPS start time"
				print "Please watch",videoname,"and note when you start moving"
				print 
				target = raw_input("Hit enter to start video with vlc (Quit vlc once you know the time)")
				runVid = "vlc " + videoname
				os.system(runVid)
				print 
				print 
				target = raw_input("Enter time movement started in mm:ss format: ")
				t1 = float(target[0:2])
				t2 = float(target[3:5])
				tSeconds = t1 * 60 + t2
				print tSeconds
				startvid = startvid + datetime.timedelta(0,tSeconds)
				print 
				print "Update info"
				print
				print "         GPS file: ",gpxfname
				print "      Camera file: ",videoname
				print "   GPS start time: ",str(p5.time)
				print "Camera start time: ",startvid
				print
				if (startvid > p5.time):
					calibrate = str(startvid - p5.time)
					print "calibration offset: -",calibrate
					ftr = [3600,60,1]
					c2 = -1 * (sum([a*b for a,b in zip(ftr, map(int,calibrate.split(':')))]))
				else:
					calibrate = str(p5.time - startvid)
					print "calibration offset: ",calibrate
					ftr = [3600,60,1]
					c2 = sum([a*b for a,b in zip(ftr, map(int,calibrate.split(':')))])
				
				print "Calibration offset in seconds: ",c2
				target = raw_input("Enter different offset (Hit enter to use calculated number)  ")
				if (target != ""):
					c2 = int(target)
				print c2
				break
			
	gpx_file.close()
	return c2

    


# define parameters
zoom = 14

### Video and gpx file to work on 														  ###
### Grabs all video files with .MP4 tag on them and lists them in modification date order ###
### only have the files you want worked on in the directory                               ###   

os.system('ls -1dtr *.MP4 >filelist.txt')
with open('filelist.txt') as f:
    vidname = f.read().splitlines()
f.close()

### finds the file with th .gpx tag on it.  Only have one gpx file in the directory.    
gpxname = os.popen('ls *.gpx').read()
gpxname = gpxname.rstrip()
print gpxname


###  Run the full program for each MP4 file  
vidnum = 0 
for item in vidname:
       

	trace = traceImportGPX(gpxname)
	# determine the boundaries of the trace
	boundaries_trace = traceBoundaries(trace)
	# determine xy numbers of boundary tiles
	tileRange = determineTileRange(boundaries_trace,zoom)
	# count number of tiles in x and y direction
	xTiles = tileRange["xMax"]-tileRange["xMin"]
	yTiles = tileRange["yMax"]-tileRange["yMin"]
	numTiles = xTiles*yTiles
	# download tiles if needed
	getTiles(tileRange,zoom)
	# merge tiles into oneimage
	mergeTiles(tileRange,zoom,"output-map.jpg")
	# Draw Green track
	#x, y = drawTraceMask(trace,256*(xTiles+1),256*(yTiles+1),boundaries_trace,zoom,"output-map.jpg","green")

	# Find the creation date of the video file from ffmpeg info
	cmmd = "ffmpeg -i " + vidname[vidnum] + " 2>&1 | grep \"creation_time\"| cut -d \' \' -f 9"
	cmmt = "ffmpeg -i " + vidname[vidnum] + " 2>&1 | grep \"creation_time\"| cut -d \' \' -f 10"
	vid_date = os.popen(cmmd).read()
	vid_time = os.popen(cmmt).read()
	rVid_Start = str(vid_date)[0:10] + " " + str(vid_time)[0:8]
	vidstart = datetime.datetime.strptime(rVid_Start, '%Y-%m-%d %H:%M:%S')
		
	# Get the resolution of the full map
	xRes = (xTiles + 1) * 256
	yRes = (yTiles + 1) * 256 
	
	print "Map Resolution: ",xRes,yRes

	# My Variables (such that they are)
	p1 = 0
	p2 = 0
	p3 = 0
	p4 = 0
	p5 = 0
	grade = 0
	odo = 0
	fnumber = 1
	mike = 0
	if (vidnum == 0):
		calibrate_sec = Calibrate(vidstart,gpxname,vidname[vidnum])
		
		
	compass = ".NW . . . N . . . .NE . . . E . . . .SE . . . S . . . .SW . . . W . . . .NW . . . N . . . .NE . . . E"  #The compass string
	ridetrace = []  
	outofframes = 0
	vidstart = datetime.datetime.strptime(rVid_Start, '%Y-%m-%d %H:%M:%S')
	print "vidstart: ", vidstart, "Before offset"	
	vidstart = vidstart + datetime.timedelta(0,calibrate_sec)
	print "vidstart: ", vidstart, "After offset"	

	# Make tmp directory and Rip the video into frames
	os.system('mkdir tmp')			#Create tmp director to store all the frames
	ripframes = "ffmpeg -i " + vidname[vidnum] + " -f image2 tmp/frame%7d.jpg"	#Make command string to rip frames into pics
	os.system(ripframes)    		#run the rip command

	## Start reading the gpx file one point at a time and calculate
	gpx_file = open(gpxname, 'r')
	gpx = gpxpy.parse(gpx_file)

	for track in gpx.tracks:
		for segment in track.segments:
			for point in segment.points:
				# Move 5 coordinates through time. 
				# Calculate speed and bearing between p1 and p5
				# Elevation is at P3
				# Odometer uses P2 and P3
				p1 = p2			# Where I've been
				p2 = p3
				p3 = p4			# My current Position
				p4 = p5
				p5 = point		# Where I'm going
				if (p4 == 0):  #At the start to avoid divide by 0 error
					p1 = p5
					p2 = p5
					p3 = p5
					p4 = p5 

				ridetrace.append([float(p3.latitude),float(p3.longitude)])

				# To Calculate Speed
				lat1, lon1 = p1.latitude,p1.longitude  #Test info
				lat2, lon2 = p5.latitude,p5.longitude  #Test info
				elevM = p3.elevation

				radius = 3958.76 # Radius of the Earth in Miles
				dlat = math.radians(lat2-lat1)
				dlon = math.radians(lon2-lon1)
				lat1r = math.radians(lat1)
				lat2r = math.radians(lat2)
				#distance formula
				a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon/2) * math.sin(dlon/2)
				c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
				d = radius * c
				
				# determine time gap between points and calculate multiplier for mph
				tm = str(p5.time - p1.time)
				tm2 = tm[5:7]
				tm3 = int(float(tm2))
				if (tm3 == 0):
					multiplier = 0
				else:
					multiplier = 60 / int(float(tm2))
			
				mph = d * multiplier * 60	# distances measured over x seconds of travel * multiplier to make a minute * 60 to make an hour
				elevft = elevM * 3.28084	# 1 meter = 3.28084 feet
			
		
				#bearing formula 
				x = math.sin(dlon) * math.cos(lat2r)
				y = math.cos(lat1r) * math.sin(lat2r) - (math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon))
				mkvid = 1
				initial_bearing = math.atan2(x, y)

				# Now we have the initial bearing but math.atan2 return values
				# from -180 to + 180 which is not what we want for a compass bearing
				# The solution is to normalize the initial bearing as shown below
				initial_bearing = math.degrees(initial_bearing)
				compass_bearing = (initial_bearing + 360) % 360
			
				#Calculate the grade between Point 1 and point 5 and make it xx.x%
				if (d != 0):
					grade = abs(float(int((((p5.elevation * 3.28084) - (p1.elevation * 3.28084)) / d) / 10)) / 10)
			
			
				# Calculate Odometer by using two points next to each other and adding it to a total odo.
				# This should be a function
				lat1, lon1 = p2.latitude,p2.longitude  #Test info
				lat2, lon2 = p3.latitude,p3.longitude  #Test info
				radius = 3958.76 # Miles
				dlat = math.radians(lat2-lat1)
				dlon = math.radians(lon2-lon1)
				lat1r = math.radians(lat1)
				lat2r = math.radians(lat2)
				#distance formula
				a2 = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon/2) * math.sin(dlon/2)
				c2 = 2 * math.atan2(math.sqrt(a2), math.sqrt(1-a2))
				d2 = radius * c2
				odo = odo + d2
				mkvid = 1
			
				# Calculate multiplier for how many frames to write printout
				
				tim = str(p3.time - p2.time)
				tim2s = tim[5:7]
				tim2m = tim[2:4]
				tim3s = int(float(tim2s))
				tim3m = int(float(tim2m))
				tim4 = (tim3m * 60) + tim3s
				frames = tim4 * 30
				if (mike == 0):
					frames = 30
					if (p3.time > vidstart):
						initframe = str(p3.time - vidstart)
						print p3.time, vidstart, initframe
						init2_sec = initframe[5:7]
						init2_min = initframe[2:4]
						init3_sec = int(float(init2_sec))
						init3_min = int(float(init2_min))
						init4_total = (init3_min * 60) + init3_sec  # + calibrate_sec  #calibrate_sec to adjust if timing is off
						fnumber = init4_total * 30	
					
				#Determine if we are heading up or down.
				if (int(mph) == 0):
					grade = 0.0
				if (tim4 > 10):
					grade = 0.0		#We're not going up or down
					mph = 0			#We're not moving
				if (p5.elevation > p1.elevation):
					direction = " UP  "
				else:
					direction = "DOWN "
				if (grade == 0):
					direction = "     "
					
				#Start building display as a string
				#Odometer
				printout = ""
				if (odo < 100):
					printout = printout + " "
				if (odo < 10):
					printout = printout + " "
				printout = printout + ('{0:.2f} mi  ').format(odo)
				#mph
				if (int(mph) < 10):
					printout = printout + " "
				printout = printout + ('{0} mph').format(int(mph))
				#compass
				cb = int(compass_bearing / 5)
				cdisplay = compass[cb+3:cb+17]
				printout = printout + "  [" + cdisplay + "]  "
				#Elevation, Grade, and Up/Down
				if (int(elevft) < 1000):
					printout = printout + " "
				if (int(elevft) < 100):
					printout = printout + " "	
				if (int(elevft) < 10):
					printout = printout + " "	
				printout = printout + ('{0} ft  {2}\\% {1}').format(int(elevft), direction, grade)			
			
				# Send overlay to images
				if (p3.time > vidstart):
					print "Delay", tim, "Frame:", fnumber, frames
					print printout
					# draw the path
					# Note: the range in "tilerange" refers to the NW corner, but our image extends on block further
					x, y = drawTraceMask(ridetrace,256*(xTiles+1),256*(yTiles+1),boundaries_trace,zoom,"output-mask.jpg","red")
					tlx = x - 128
					tly = y - 128
					#Stop map scroll if close to map image edge
					if (tlx < 0):
						tlx = 0
					if (tly < 0):
						tly = 0
					if ((tlx + 256) > xRes):
						tlx = xRes - 256
					if ((tly + 256) > yRes):
						tly = yRes - 256
					#Create Map crop command
					viewMap = "convert output-mask.jpg -crop  256x256+" + str(tlx) + "+" + str(tly) + "\\! -alpha set -channel A -evaluate set 60% tmp/output.png"
					#viewMap = "convert output-mask.jpg -crop  256x256+" + str(tlx) + "+" + str(tly) + "\\! -fuzz 15% -transparent white tmp/output.png"
					os.system(viewMap)
					# send the info to overlay and return current frame number
					fnumber, outofframes = insert_annotation(printout, fnumber, frames)  			
					mike = 1	# Because I'm #1  :)
					print 
				else:
					print "Waiting for Video"
			
				if (outofframes != 0):
					break
			

	#Rip Audio
	raudio = "ffmpeg -i " + vidname[vidnum] + " -vn -ac 2 -ar 44100 -ab 128k -f wav sound.wav"
	os.system(raudio)

	# rebuild the video
	outile = "ADB-" + vidname[vidnum]
	outcommand = "ffmpeg -f image2 -r 30 -i tmp/frame%7d.jpg -i sound.wav -b:v 16384k -y " + outile 
	os.system(outcommand)
	
	# remove old files
	os.system('rm -Rf tmp')
	os.system('rm -f sound.wav')
	
	# Next Video
	vidnum = vidnum + 1



