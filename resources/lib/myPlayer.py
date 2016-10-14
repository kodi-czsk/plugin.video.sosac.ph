# -*- coding: UTF-8 -*-
import xbmc
import xbmcgui
import json
import time
from datetime import datetime, timedelta
import buggalo

# import pydevd
# pydevd.settrace(stdoutToServer=True,
#           stderrToServer=True,trace_only_current_thread=False)


class MyPlayer(xbmc.Player):

    def __init__(self, itemType=None, itemDBID=None):
        try:
            xbmc.Player.__init__(self)
            self.estimateFinishTime = 0
            self.realFinishTime = 0
            self.itemDuration = 0
            self.itemDBID = itemDBID
            self.itemType = itemType
            # dummy call to fix weird error see:
            # http://bugs.python.org/issue7980
            try:
                datetime.strptime('2012-01-01', )
            except TypeError:
                datetime(*(time.strptime('2012-01-01', '%Y-%m-%d')[0:6]))
        except Exception:
            buggalo.onExceptionRaised({'self.itemDBID: ': self.itemDBID,
                                       'self.itemType: ': self.itemType})

    @staticmethod
    def executeJSON(request):
        # =================================================================
        # Execute JSON-RPC Command
        # Args:
        # request: Dictionary with JSON-RPC Commands
        # Found code in xbmc-addon-service-watchedlist
        # =================================================================
        rpccmd = json.dumps(request)  # create string from dict
        json_query = xbmc.executeJSONRPC(rpccmd)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        return json_response

    @staticmethod
    def get_sec(time_str):
        # nasty bug appears only for 2nd and more attempts during session
        # workaround from: http://forum.kodi.tv/showthread.php?tid=112916
        try:
            t = datetime.strptime(time_str, "%H:%M:%S")
        except TypeError:
            t = datetime(*(time.strptime(time_str, "%H:%M:%S")[0:6]))
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    def setWatched(self):
        if self.itemType == u'episode':
            metaReq = {"jsonrpc": "2.0",
                       "method": "VideoLibrary.SetEpisodeDetails",
                       "params": {"episodeid": self.itemDBID,
                                  "playcount": 1},
                       "id": 1}
            self.executeJSON(metaReq)
        elif self.itemType == u'movie':
            metaReq = {"jsonrpc": "2.0",
                       "method": "VideoLibrary.SetMovieDetails",
                       "params": {"movieid": self.itemDBID,
                                  "playcount": 1},
                       "id": 1}
            self.executeJSON(metaReq)

    def onPlayBackStarted(self):
        try:
            # ListItem.Duration je z databáze, bývá nepřesná v řádech minut
            # Player.TimeRemaining je přesnější
            while True:
                xbmc.sleep(1000)
                self.itemDuration = xbmc.getInfoLabel(
                    'Player.TimeRemaining(hh:mm:ss)')
                if self.itemDuration != '':
                    self.itemDuration = self.get_sec(self.itemDuration)
                    break
            # plánovaný čas dokončení 100 % přehrání
            self.estimateFinishTime = xbmc.getInfoLabel(
                'Player.FinishTime(hh:mm:ss)')
        except Exception:
            buggalo.onExceptionRaised({'self.itemDuration: ': self.itemDuration,
                                       'self.estimateFinishTime: ': self.estimateFinishTime})

    def onPlayBackEnded(self):
        self.setWatched()

    def onPlayBackStopped(self):
        try:
            # Player.TimeRemaining  - už zde nemá hodnotu
            # Player.FinishTime - kdy přehrávání skutečně zkončilo
            self.realFinishTime = xbmc.getInfoLabel(
                'Player.FinishTime(hh:mm:ss)')
            timeDifference = self.get_sec(self.estimateFinishTime) - \
                self.get_sec(self.realFinishTime)
            timeRatio = timeDifference.seconds / \
                float((self.itemDuration).seconds)
            # upravit podmínku na 0.05 tj. zbývá shlédnout 5%
            if abs(timeRatio) < 0.1:
                self.setWatched()
        except Exception:
            buggalo.onExceptionRaised({'self.itemDuration: ': self.itemDuration,
                                       'self.estimateFinishTime: ': self.estimateFinishTime,
                                       'self.realFinishTime: ': self.realFinishTime,
                                       'timeDifference: ': timeDifference,
                                       'timeRatio: ': timeRatio, })

    def waitForChange(self):
        xbmc.sleep(2000)
        while True:
            pom = xbmc.getInfoLabel('Player.FinishTime(hh:mm:ss)')
            if pom != self.estimateFinishTime:
                self.estimateFinishTime = pom
                break
            xbmc.sleep(100)

    def onPlayBackResumed(self):
        self.waitForChange()

    def onPlayBackSpeedChanged(self, speed):
        self.waitForChange()

    def onPlayBackSeek(self, time, seekOffset):
        self.waitForChange()
