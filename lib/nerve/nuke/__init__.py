import nuke
import os

def getTrackData(node, trackID, channel, frame):
	k = node["tracks"]
	
	numColumns=31
	channels = {0:'enable', 1:'name', 2:'track_x', 3:'track_y', 4:'offset_x', 5:'offset_y', 6:'T', 7:'R', 8:'S', 9:'error', 10:'error_min', 11:'error_max', 12:'pattern_x', 13:'pattern_y', 14:'pattern_r', 15:'pattern_t', 16:'search_x', 17:'search_y', 18:'search_r', 19:'search_t'}
	swap = dict( (v,k) for k,v in channels.iteritems() )
	if channel not in swap.keys():
		raise Exception('channel "'+channel+'" not found')
		return False
		
	
	return k.getValueAt(frame, numColumns*trackID + swap[channel] )
	
	
def getTrackNames(node):
	k = node['tracks']
	s = node['tracks'].toScript().split(' \n} \n{ \n ')
	s.pop(0)
	ss = str(s)[2:].split('\\n')
	if ss:
		ss.pop(-1)
	if ss:
		ss.pop(-1)
	outList = []
	for i in ss:
		outList.append(i.split('"')[1])
	return outList
	
def getNumberOfTracks(node):
	return len( getTrackNames(node) )

def setRange(value, min, max, oldmin, oldmax):
	# OutValue = Min + (((Value-OldMin)/(OldMax-OldMin)) * (Max-Min))
	return ( min + (((value-oldmin)/(oldmax-oldmin)) * (max-min)) )
	
	
def trackToSyntheyes():
	def floatToStr(num, pad=3):
		n = str( round(num, pad) )
		n = n.split('.')[0] + '.' + n.split('.')[1].ljust(pad, '0')
		return n
		

	# Frame Range
	vv = nuke.activeViewer().node()
	frameRange = vv.playbackRange()
	startFrame = int(str(frameRange).split('-')[0])
	endFrame = int(str(frameRange).split('-')[1])
	
	# Tracker Node
	sel = nuke.selectedNodes()
	if len(sel) is 0:
		raise Exception("Nothing Selected")
	
	txt = ''
	for node in sel:
	
		if node.Class() != 'Tracker4':
			continue
			
		format = node.format()
		size = format.fromUV(1,1)
			
		tracks = getNumberOfTracks(node)
		for track in range(tracks):
			for i in range(startFrame, endFrame+1):
				if not int( getTrackData( node, track, 'enable', i) ):
					continue
				x = getTrackData(node, track, 'track_x', i)
				x = setRange(x, -1, 1, 0, size[0])
				y = getTrackData(node, track, 'track_y', i)
				y = setRange(y, -1, 1, 0, size[1])*-1
				
				txt+= '%s_%s %s %s %s\n'%(node.name(),str(track), str(i), floatToStr(x), floatToStr(y))
		
	filename = nuke.toNode("root").name()
	filename = filename.replace('.nk', '_syntheyes.txt')
	file = open(filename, 'w')
	file.write(txt)
	file.close()
	
def trackToBoujou():
	def floatToStr(num, pad=2):
		n = str( round(num, pad) )
		n = n.split('.')[0] + '.' + n.split('.')[1].ljust(pad, '0')
		return n

	# Frame Range
	vv = nuke.activeViewer().node()
	frameRange = vv.playbackRange()
	startFrame = int(str(frameRange).split('-')[0])
	endFrame = int(str(frameRange).split('-')[1])
	
	# Tracker Node
	sel = nuke.selectedNodes()
	if len(sel) is 0:
		raise Exception("Nothing Selected")
	
	txt = '# track_id    view      x    y\n'
	for node in sel:
		if node.Class() != 'Tracker4':
			continue
			
		tracks = getNumberOfTracks(node)
		for track in range(tracks):
			for i in range(startFrame, endFrame+1):
				if not int( getTrackData( node, track, 'enable', i) ):
					continue
				x = floatToStr(getTrackData(node, track, 'track_x', i))
				y = floatToStr(getTrackData(node, track, 'track_y', i))
				txt+= '%s_%s  %s  %s  %s\n'%(node.name(),str(track), str(i), x, y)
		
	filename = nuke.toNode("root").name()
	filename = filename.replace('.nk', '_boujou.txt')
	file = open(filename, 'w')
	file.write(txt)
	file.close()

def mkDaily(node):

	# RV
	rviopaths = ["C:/Program Files/Shotgun/RV-7.1.1/bin/rvio_hw.exe", "D:/Program Files/Shotgun/RV-7.1.1/bin/rvio_hw.exe"]
	rvio = None
	for rviopath in rviopaths:
		if os.path.isfile(rviopath):
			rvio = rviopath
	if rvio is None:
		raise Exception("RVIO not found. Cannot create daily.")
		return False
		
	filename = nuke.thisNode().metadata()['input/filename']
	seq  = filename.split('/')[3]
	shot  = filename.split('/')[4]
	# Filepath
	filepath = 'X:/jobs/echoes/' + shot + '/' + seq + '/elements/dailies'
	if not os.path.exists(filepath):
		raise Exception(filepath + ' not found. Cannot create daily')
		return False
		
	# Filename
	print node.knob("dversion").value()
	filename = 'ECS_' + seq + '_' + shot + '_' + node.knob("dname").value() + '_v' + (str(int(node.knob("dversion").value()))).zfill(3) + '.mov'
	if os.path.exists( filepath + '/' + filename):
		raise Exception('Daily already exists, wont overide')
		return False

	with nuke.root():
		write = nuke.createNode("Write")
		
	write.setInput(0, node)
	tmp = os.environ["TEMP"].replace('\\', '/') + '/ndaily'
	if os.path.exists(tmp):
		import shutil
		shutil.rmtree(tmp)	
		
	os.mkdir(tmp)
		
	fileseq = tmp + '/daily.#.jpg'
	write.knob("file").setValue( fileseq )
	write.knob('_jpeg_quality').setValue(1)
	write.knob('_jpeg_sub_sampling').setValue(2)
	
	# Execute
	nuke.execute(write, node.knob("startFrame").value(), node.knob("endFrame").value() )
	
	# Convert
	outfile = filepath + '/' + filename
	fileseq = fileseq.replace('#', '@')
	cmd = '"%s" "%s" -o "%s" -fps 24 -codec libx264'%(rvio, fileseq, outfile)
	batfilepath = tmp + '/daily.bat'
	batfile = open(batfilepath, 'w')
	batfile.write(cmd)
	batfile.close()
	os.system( '"%s"'%batfilepath )
	os.system('"' + outfile + '"')
	
	import shutil
	shutil.rmtree(tmp)
	
	nuke.delete(write)
	