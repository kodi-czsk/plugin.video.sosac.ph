# xbmc
import xbmc
import xbmcaddon
import xbmcgui

import json
import time
import os

sys.path.append( os.path.join ( os.path.dirname(__file__),'resources','lib') )
from sosac import SosacContentProvider

__scriptid__   = 'plugin.video.sosac.ph'
__scriptname__ = 'sosac.ph'
__addon__      = xbmcaddon.Addon(id=__scriptid__)
__language__   = __addon__.getLocalizedString
__set          = __addon__.getSetting
__cwd__	       = __addon__.getAddonInfo('path')

reverse_eps = __set('order-episodes') == '0'

class subs:
    last_run = 0
    sleep_time = 600
    sosac = None
    
    def __init__(self):
        self.sosac = SosacContentProvider(reverse_eps=reverse_eps)
    
    def run(self):
        log("Start")
        self.evalSchedules();
        xbmc.sleep(self.sleep_time)
        self.last_run = time.time()
        while(not xbmc.abortRequested):
            if(time.time() > self.last_run + 3600):
                self.evalSchedules()
                self.last_run = time.time()

            xbmc.sleep(self.sleep_time)
        log("Koncim")
        
    def evalSchedules(self):
        if not self.scanRunning() and xbmc.Player().isPlaying() == False:
            showNotification('Subscription',"Spustam scan")
            log("Spustam co mam naplanovane")
            subs = self.sosac.get_subs()
            new_items = False
            for url, name in subs.iteritems():
                if self.sosac.is_tv_shows_url(url):
                    new = self.sosac.run_custom({'action': 'add-to-library', '__addon__': addon(), 'name': name, 'url': url, 'update': True})
                    if new:
                        new_items = True
            if new_items:
                xbmc.executebuiltin('UpdateLibrary(video)')
        else:
            log("Nieco srotuje, tak nic nerobim")
        
    def scanRunning(self):
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True            
        else:
            return False
        
def data_dir():
    return __addon__.getAddonInfo('profile')

def addon_dir():
    return __addon__.getAddonInfo('path')

def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(encode(__scriptid__ + "-" + __addon__.getAddonInfo('version') + " : " + message),level=loglevel)

def showNotification(title,message):
    xbmcgui.Dialog().notification(encode(title),encode(message),time=4000,icon=xbmc.translatePath(addon_dir() + "/icon.png"),sound=False)

def setSetting(name,value):
    __addon__.setSetting(name,value)

def getSetting(name):
    return __addon__.getSetting(name)
    
def getString(string_id):
    return __addon__.getLocalizedString(string_id)

def encode(string):
    return string.encode('UTF-8','replace')

def addon():
    return __addon__

if __name__ == "__main__":
    subs().run()