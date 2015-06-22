import util,xbmcprovider,xbmcutil,xbmcvfs,xbmcgui,xbmc
import unicodedata,os,re,time,string,datetime,urllib

class XBMCSosac(xbmcprovider.XBMCMultiResolverContentProvider):
    last_run = 0
    sleep_time = 60
    
    def __init__(self,provider,settings,addon):
        xbmcprovider.XBMCMultiResolverContentProvider.__init__(self,provider,settings,addon)
        provider.parent = self
        try:
            import StorageServer
            self.cache = StorageServer.StorageServer("Downloader")
        except:
            import storageserverdummy as StorageServer
            self.cache = StorageServer.StorageServer("Downloader") 

    def make_name(self, text, lower=True):
        text = self.normalize_filename(text, "-_.' %s%s" % (string.ascii_letters, string.digits))
        word_re = re.compile(r'\b\w+\b')
        text = ''.join([c for c in text if (c.isalnum() or c=="'" or c == '.' or c =='-' or c.isspace())]) if text else ''
        text = '-'.join(word_re.findall(text))
        return text.lower() if lower else text

    def normalize_filename(self,name,validChars=None):
        validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        if (validChars != None):
            validFilenameChars = validChars
        cleanedFilename = self.encode(name)
        return ''.join(c for c in cleanedFilename if c in validFilenameChars)

    def service(self):
        util.info("Start")
        xbmc.sleep(self.sleep_time)
        try:
            self.last_run = float(self.cache.get("subscription.last_run")) #time.time()
        except:
            self.last_run = time.time()
            self.cache.set("subscription.last_run", str(self.last_run))
            pass
        
        if time.time() > self.last_run + 24 * 3600:
            self.evalSchedules();
            
        while(not xbmc.abortRequested):
            if(time.time() > self.last_run + 24 * 3600):
                self.evalSchedules()
                self.last_run = time.time()
                self.cache.set("subscription.last_run", str(self.last_run))

            xbmc.sleep(self.sleep_time)
        util.info("Koncim")

    def showNotification(self,title,message,time=1000):
        xbmcgui.Dialog().notification(self.encode(title),self.encode(message),time=time,icon=xbmc.translatePath(self.addon_dir() + "/icon.png"),sound=False)

    def evalSchedules(self):
        if not self.scanRunning() and xbmc.Player().isPlaying() == False:
            self.showNotification('Subscription','Chcecking')
            util.info("Spustam co mam naplanovane")
            subs = self.get_subs()
            new_items = False
            for url, name in subs.iteritems():
                if self.provider.is_tv_shows_url(url):
                    new = self.run_custom({'action': 'add-to-library', 'name': name, 'url': url, 'update': True})
                    if new:
                        new_items = True
            if new_items:
                xbmc.executebuiltin('UpdateLibrary(video)')
        else:
            util.info("Nieco srotuje, tak nic nerobim")
        
    def scanRunning(self):
        if(xbmc.getCondVisibility('Library.IsScanningVideo') or xbmc.getCondVisibility('Library.IsScanningMusic')):
            return True            
        else:
            return False
    
    def getBBDB(self, name):
        name = util.request('http://csfd.bbaron.sk/find.php?sosac=1;' + urllib.urlencode({'name': name}))
        if name != '':
            return self.getTVDB(name)
        return None
        
    def getTVDB(self, name):
        data = util.request('http://thetvdb.com/api/GetSeries.php?' + urllib.urlencode({'seriesname': name, 'language':'cs'}))
        try:
            tvid = re.search('<id>(\d+)</id>', data).group(1);
        except:
            tvid = self.getBBDB(name)
        return tvid
    
    def run_custom(self, params):
        if 'action' in params.keys():
            icon = os.path.join(self.addon.getAddonInfo('path'),'icon.png')
            if params['action'] == 'add-to-library':
                error = False
                arg = {"play": params['url'], 'cp': 'sosac.ph', "title": params['name']}
                item_url = util._create_plugin_url(arg, 'plugin://' + self.addon_id + '/')
                new_items = False
                #self.showNotification('Linking', params['name'])
                if self.scanRunning():
                    self.showNotification('Library scan or subscription update in progress.', 'Please wait for it to complete.', 5000)
                    return
                if "movie" in params['url']:
                    item_dir = self.getSetting('library-movies')
                    (error, new_items) = self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), self.normalize_filename(params['name'])) + '.strm', item_url)
                else:
                    self.showNotification(params['name'], 'Checking new content')
                    
                    subs = self.get_subs()
                    if not params['url'] in subs.keys():
                        subs.update({params['url']: params['name']})
                        self.set_subs(subs)
                        #self.addon.setSetting('tvshows-subs', json.dumps(subs))

                    item_dir = self.getSetting('library-tvshows')
                    
                    tvid = self.getTVDB(params['name'])
                    if tvid:
                        self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), 'tvshow.nfo'), 'http://thetvdb.com/index.php?tab=series&id=' + tvid)
                        
                    list = self.provider.list_tv_show(params['url'])
                    for itm in list:
                        nfo = re.search('[^\d+](?P<season>\d+)[^\d]+(?P<episode>\d+)', itm['title'], re.IGNORECASE | re.DOTALL)
                        arg = {"play": itm['url'], 'cp': 'sosac.ph', "title": self.normalize_filename(itm['epname'])}
                        #info = ''.join(('<episodedetails><season>',nfo.group('season'),'</season><episode>',nfo.group('episode'),'</episode></episodedetails>'))
                        item_url = util._create_plugin_url(arg, 'plugin://' + self.addon_id + '/')
                        (err, new) = self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), 'Season ' + nfo.group('season'), "S" + nfo.group('season') + "E" + nfo.group('episode') + '.strm'), item_url)
                        #self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), 'Season ' + nfo.group('season'), "S" + nfo.group('season') + "E" + nfo.group('episode') + '.nfo'), info)
                        error |= err
                        if new == True and not err:
                            new_items = True
                if not error and new_items and not ('update' in params):
                    self.showNotification(params['name'],'New content')
                    xbmc.executebuiltin('UpdateLibrary(video)')
                elif not error:
                    self.showNotification(params['name'],'No new contents')
                if error:
                    self.showNotification('Failed, Please check kodi.util.info','Linking')
                return new_items

    def add_item_to_library(self, item_path, item_url):
        error = False
        new = False
        if item_path:
            item_path = os.path.normpath(xbmc.translatePath( item_path ))
            dir = os.path.dirname(item_path) + '/'
            if not xbmcvfs.exists(dir):
                try:
                    xbmcvfs.mkdirs(dir)
                except Exception, e:
                    error = True
                    print('Failed to create directory 1', dir)
                    
            if not xbmcvfs.exists(dir):
                error = True
                print('Failed to create directory 2', dir)
                
            if not xbmcvfs.exists(item_path):
                try:
                    file_desc = xbmcvfs.File(item_path, 'w')
                    file_desc.write(item_url)
                    file_desc.close()
                    new = True
                except Exception, e:
                    print('Failed to create .strm file: ', item_path, e)
                    error = True
        else:
            error = True
            
        return (error, new)

    def get_subs(self):
        data = self.cache.get("subscription")
        try:
            subs = eval(data)
        except:
            subs = {}

        return subs
    
    def set_subs(self, subs):
        self.cache.set("subscription", repr(subs))
    
    @staticmethod
    def encode(string):
        return unicodedata.normalize('NFKD', string.decode('utf-8')).encode('ascii', 'ignore')

    def addon_dir(self):
        return self.addon.getAddonInfo('path')
    
    def data_dir(self):
        return self.addon.getAddonInfo('profile')
    
    def getSetting(self, name):
        return self.addon.getSetting(name)
    
    def getString(self,string_id):
        return self.addon.getLocalizedString(string_id)

