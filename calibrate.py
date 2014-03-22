#!/usr/bin/env python

import os
import datetime
import gpxpy
import gpxpy.gpx


## Video and gpx file to work on 														  ###
### Grabs all video files with .MP4 tag on them and lists them in modification date order ###
### only have the files you want worked on in the directory                               ###   

os.system('ls -1dtr *.MP4 >filelist.txt')
with open('filelist.txt') as f:
    vidname = f.read().splitlines()
f.close()

### finds the file with th .gpx tag on it.  Only have one gpx file in the directory.    
gpxname = os.popen('ls *.gpx').read()
gpxname = gpxname.rstrip()


# Find the creation date of the video file from ffmpeg info
cmmd = "ffmpeg -i " + vidname[0] + " 2>&1 | grep \"creation_time\"| cut -d \' \' -f 9"
cmmt = "ffmpeg -i " + vidname[0] + " 2>&1 | grep \"creation_time\"| cut -d \' \' -f 10"
vid_date = os.popen(cmmd).read()
vid_time = os.popen(cmmt).read()
rVid_Start = str(vid_date)[0:10] + " " + str(vid_time)[0:8]
vidstart = datetime.datetime.strptime(rVid_Start, '%Y-%m-%d %H:%M:%S')


## Start reading the gpx file one point at a time and calculate
gpx_file = open(gpxname, 'r')
gpx = gpxpy.parse(gpx_file)

for track in gpx.tracks:
	for segment in track.segments:
		for point in segment.points:

			p5 = point		# One Point
			
			print
			print "         GPS file: ",gpxname
			print "      Camera file: ",vidname[0]
			print "   GPS start time: ",str(p5.time)
			print "Camera start time: ",vidstart
			print
			print "Camera start time needs to match GPS start time"
			print "Please watch",vidname[0],"and note when you start moving"
			print 
			target = raw_input("Hit enter to start video with vlc (Quit vlc once you know the time)")
			runVid = "vlc " + vidname[0]
			#os.system(runVid)
			print 
			print 
			target = raw_input("Enter time movement started in mm:ss format: ")
			t1 = float(target[0:2])
			t2 = float(target[3:5])
			#print target[0:2],t1
			#print target[3:5],t2
			tSeconds = t1 * 60 + t2
			print tSeconds
			vidstart = vidstart + datetime.timedelta(0,tSeconds)
			print 
			print "Update info"
			print
			print "         GPS file: ",gpxname
			print "      Camera file: ",vidname[0]
			print "   GPS start time: ",str(p5.time)
			print "Camera start time: ",vidstart
			print
			if (vidstart > p5.time):
				calibrate = str(vidstart - p5.time)
				print "calibration offset: -",calibrate
			else:
				calibrate = str(p5.time - vidstart)
				print "calibration offset: ",calibrate
			quit()
