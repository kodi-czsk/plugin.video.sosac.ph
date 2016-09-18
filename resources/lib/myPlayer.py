# -*- coding: UTF-8 -*-
import xbmc
import xbmcgui
import json
import time
from datetime import datetime,timedelta

# import pydevd
# pydevd.settrace(stdoutToServer=True,
# 			stderrToServer=True,trace_only_current_thread=False)



class MyPlayer(xbmc.Player):
	
	def __init__(self,itemType=None,itemDBID=None):
		xbmc.Player.__init__(self)
		self.estimateFinishTime = 0
		self.realFinishTime = 0
		self.itemDuration = 0
		self.itemDBID = itemDBID
		self.itemType = itemType
		
	@staticmethod	
	def executeJSON(request):
		 #=========================================================================
		 # Execute JSON-RPC Command
		 # Args:
		 #	 request: Dictionary with JSON-RPC Commands
		 # Found code in xbmc-addon-service-watchedlist
		 #=========================================================================
		rpccmd = json.dumps(request)	# create string from dict
		json_query = xbmc.executeJSONRPC(rpccmd)
		json_query = unicode(json_query, 'utf-8', errors='ignore')
		json_response = json.loads(json_query)
		return json_response
	
	@staticmethod
	def get_sec(time_str):
		# nasty bug appears only for 2nd and more attempts during session
		# workaround from: http://forum.kodi.tv/showthread.php?tid=112916
		try:
			t = datetime.strptime(time_str,"%H:%M:%S")
		except TypeError:
			t = datetime(*(time.strptime(time_str,"%H:%M:%S")[0:6]))
		return timedelta(hours=t.hour,minutes=t.minute,seconds=t.second)

	def onPlayBackStarted(self):
		# ListItem.Duration je z databáze, bývá nepřesná v řádech minut
		# Player.TimeRemaining je přesnější
		self.itemDuration = self.get_sec(
				xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)'))
		# plánovaný čas dokončení 100 % přehrání
		self.estimateFinishTime = xbmc.getInfoLabel('Player.FinishTime(hh:mm:ss)')

	def onPlayBackEnded(self):
		self.onPlayBackStopped()

	def onPlayBackStopped(self):
		# Player.TimeRemaining	- už zde nemá hodnotu
		# Player.FinishTime - kdy přehrávání skutečně zkončilo
		self.realFinishTime = xbmc.getInfoLabel('Player.FinishTime(hh:mm:ss)')
		timeDifference = self.get_sec(self.estimateFinishTime) - \
							self.get_sec(self.realFinishTime)
		timeRatio = timeDifference.seconds / float((self.itemDuration).seconds)
		# upravit podmínku na 0.05 tj. zbývá shlédnout 5% 
		if abs(timeRatio) < 0.1:
			if self.itemType == u'episode' :
				metaReq = {	"jsonrpc": "2.0",
							"method": "VideoLibrary.SetEpisodeDetails",
							"params": {	"episodeid": self.itemDBID,
										"playcount": 1},
							"id": 1}
				self.executeJSON(metaReq)
			elif self.itemType == u'movie':
				metaReq = {	"jsonrpc": "2.0",
							"method": "VideoLibrary.SetMovieDetails",
							"params": {	"movieid": self.itemDBID,
										"playcount": 1},
							"id": 1}
				self.executeJSON(metaReq)

	def onPlayBackResumed(self):
		self.estimateFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')

	def onPlayBackSpeedChanged(self, speed):
		self.estimateFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')
		
	def onPlayBackSeek(self, time, seekOffset):
		self.estimateFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')
