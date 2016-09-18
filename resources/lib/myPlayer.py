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
		xbmc.log('"přehrávač __init__ v myPlayer.py :-)"')
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

	def onPlayBackStarted(self):	# tiskne do logu
		xbmc.log('"Playback started :-)"')
		#pokusy :-)
		pokus = xbmc.getInfoLabel('VideoPlayer.Genre')
		xbmc.log('"VideoPlayer.Genre " ' + pokus)
		xbmc.log('"self.itemType" ' + str(self.itemType))
		xbmc.log('"self.itemDBID" ' + str(self.itemDBID))
		# uchovat délku trvání položky ListItem.Duration je z databáze bývá
		# nepřesná v řádech minut
		# uchovat délku trvání položky Player.TimeRemaining je přesnější v řádu
		# minut
		pom = xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)')
		xbmc.log('"Player.TimeRemaining jako str v onPlayBackStarted :-)"' + pom)
		self.itemDuration = self.get_sec(
				xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)'))
		xbmc.log("'Player.TimeRemaining jako timedelta  v onPlayBackStarted :-)'" +
				str(self.itemDuration))
		# uchovat plánovaný čas dokončení 100 % přehrání
		self.estimateFinishTime = xbmc.getInfoLabel('Player.FinishTime(hh:mm:ss)')
		xbmc.log('"Player.FinishTime v onPlayBackStarted :-)" ' +
				str(self.estimateFinishTime))

	def onPlayBackEnded(self):
		xbmc.log('"Playback ended :-)"')
		self.onPlayBackStopped()

	# OBROVSKÁ chyba !!! onPlaybackStopped(self) opravdu nemohlo fungovat!!!
	def onPlayBackStopped(self):
		xbmc.log('"Playback stopped :-)"')
		# Player.TimeRemaining	- už zde nemá hodnotu
		# Player.FinishTime - kdy přehrávání skutečně zkončilo
		self.realFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')
		xbmc.log("'Player.FinishTime	 ' v onPlayBackStopped :-)" +
				str(self.realFinishTime))
		xbmc.log("'self.estimateFinishTime	 ' v onPlayBackStopped :-)" +
				str(self.estimateFinishTime))
		timeDifference = self.get_sec(self.estimateFinishTime) - \
							self.get_sec(self.realFinishTime)
		xbmc.log('"Rozdíl je : "' + str(timeDifference))
		xbmc.log('" timeDifference.seconds " ' +str(timeDifference.seconds ))
		xbmc.log('" (self.itemDuration).seconds " '+ str((self.itemDuration).seconds))
		timeRatio = timeDifference.seconds / float((self.itemDuration).seconds)
		xbmc.log('"Podíl je : "' + str(timeRatio))
		# upravit podmínku na 0.05 tj. zbývá shlédnout 5% 
		if abs(timeRatio) < 1:
			if self.itemType == u'episode' :
				metaReq = {	"jsonrpc": "2.0",
							"method": "VideoLibrary.SetEpisodeDetails",
							"params": {	"episodeid": self.itemDBID,
										"playcount": 1},
							"id": 1}
				self.executeJSON(metaReq)
				xbmc.log('"Proběhlo nastavení SHLÉDNUTO u EPIZODY :-) "')
			elif self.itemType == u'movie':
				metaReq = {	"jsonrpc": "2.0",
							"method": "VideoLibrary.SetMovieDetails",
							"params": {	"movieid": self.itemDBID,
										"playcount": 1},
							"id": 1}
				self.executeJSON(metaReq)
				xbmc.log('"Proběhlo nastavení SHLÉDNUTO u FILMU :-) "')
			
	def onPlayBackPaused(self):	# tiskne do logu
		xbmc.log('"Playback paused :-)"')
		# stačí uložit plánovaný konec přehrávání v onPlayBackResumed

	def onPlayBackResumed(self):
		xbmc.log('"Playback resumed :-)"')
		# stačí uložit plánovaný konec přehrávání
		self.estimateFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')
		xbmc.log("'Player.FinishTime	 ' v OnPlayBackResumed :-)" +
				str(self.estimateFinishTime))

	def onPlayBackSpeedChanged(self, speed):
		xbmc.log('"Playback speed changed :-)"' + str(speed))
		self.estimateFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')
		# stačí uložit plánovaný konec přehrávání
		xbmc.log("'Player.FinishTime	 ' v onPlayBackSpeedChange :-)" +
				str(self.estimateFinishTime))

	def onPlayBackSeek(self, time, seekOffset):
		# stačí uložit plánovaný konec přehrávání
		self.estimateFinishTime = xbmc.getInfoLabel(
			'Player.FinishTime(hh:mm:ss)')
		xbmc.log("'Player.FinishTime	 ' v onPlayBackSeek :-)" +
				str(self.estimateFinishTime))

	def __del__(self):
		xbmc.log('"přehrávač __del__ v myPlayer.py :-)"')
