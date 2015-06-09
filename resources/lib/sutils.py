import util,xbmcprovider,xbmcutil,xbmcvfs,xbmcgui,xbmc
import unicodedata,json,os,re,time,string,datetime

class XBMCSosac(xbmcprovider.XBMCMultiResolverContentProvider):
    last_run = 0
    sleep_time = 600
    
    def __init__(self,provider,settings,addon):
        xbmcprovider.XBMCMultiResolverContentProvider.__init__(self,provider,settings,addon)
        provider.parent = self
        try: 
            import sqlite3
            from sqlite3 import dbapi2 as database
        except Exception, e:
            from pysqlite2 import dbapi2 as database
            
        path = self.addon_dir()
        self.db = os.path.join(path, 'subscription.db')
        print("DB: ", self.db)
        self.dbcon = database.connect(self.db)
        self.dbcon.row_factory = database.Row
        self.dbcon.text_factory = str
        self.dbcur = self.dbcon.cursor()
        self._create_subscription_tables()
    
    def normalize_filename(self,name):
        validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        cleanedFilename = self.encode(name)
        return ''.join(c for c in cleanedFilename if c in validFilenameChars)

    def service(self):
        util.info("Start")
        self.evalSchedules();
        xbmc.sleep(self.sleep_time)
        self.last_run = time.time()
        while(not xbmc.abortRequested):
            if(time.time() > self.last_run + 3600):
                self.evalSchedules()
                self.last_run = time.time()

            xbmc.sleep(self.sleep_time)
        util.info("Koncim")

    def showNotification(self,title,message):
        xbmcgui.Dialog().notification(self.encode(title),self.encode(message),time=1000,icon=xbmc.translatePath(self.addon_dir() + "/icon.png"),sound=False)

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
    
    def run_custom(self, params):
        if 'action' in params.keys():
            icon = os.path.join(self.addon.getAddonInfo('path'),'icon.png')
            if params['action'] == 'add-to-library':
                print("PARAMS: ", params)
                error = False
                arg = {"play": params['url'], 'cp': 'sosac.ph'}
                item_url = util._create_plugin_url(arg, 'plugin://' + self.addon_id + '/')
                new_items = False
                #self.showNotification('Linking', params['name'])
                if "movie" in params['url']:
                    item_dir = self.getSetting('library-movies')
                    (error, new) = self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), self.normalize_filename(params['name'])) + '.strm', item_url)
                else:
                    self.showNotification(params['name'],'Checking new content')
                    subs = self.get_subs()

                    if not params['url'] in subs.keys():
                        subs.update({params['url']: params['name']})
                        self.set_subs(subs)
                        #self.addon.setSetting('tvshows-subs', json.dumps(subs))

                    list = self.provider.list_tv_show(params['url'])
                    for itm in list:
                        arg = {"play": re.sub(r'/cs/', r'/', itm['url']), 'cp': 'sosac.ph'}
                        item_url = util._create_plugin_url(arg, 'plugin://' + self.addon_id + '/')
                        item_dir = self.getSetting('library-tvshows')
                        nfo = re.search('[^\d+](?P<season>\d+)[^\d]+(?P<episode>\d+)', itm['title'], re.IGNORECASE | re.DOTALL)
                        info = ''.join(('<episodedetails><season>',nfo.group('season'),'</season><episode>',nfo.group('episode'),'</episode></episodedetails>'))
                        (err, new) = self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), 'Season ' + nfo.group('season'), "S" + nfo.group('season') + "E" + nfo.group('episode') + '.strm'), item_url)
                        self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), 'Season ' + nfo.group('season'), "S" + nfo.group('season') + "E" + nfo.group('episode') + '.nfo'), info)
                        error |= err
                        if new == True and not err:
                            new_items = True
                    if new_items and not ('update' in params):
                        self.showNotification(params['name'],'New content')
                        xbmc.executebuiltin('UpdateLibrary(video)')
                    else:
                        self.showNotification(params['name'],'No new contents')
                if error:
                    self.showNotification('Failed, Please check kodi.util.info','Linking')
                return new_items

    def add_item_to_library(self, item_path, item_url):
        error = False
        print("path: ", item_path)
        new = False
        if item_path:
            item_path = os.path.normpath(item_path)
            if not xbmcvfs.exists(os.path.dirname(item_path)):
                try:
                    xbmcvfs.mkdirs(os.path.dirname(item_path))
                except Exception, e:
                    print('Failed to create directory', item_path)

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

    def _create_subscription_tables(self):
        sql_create = "CREATE TABLE IF NOT EXISTS subscription (url TEXT, name TEXT, tmstmp TIMESTAMP, UNIQUE(url))"
        self.dbcur.execute(sql_create)
        self.dbcur.execute('CREATE INDEX IF NOT EXISTS subindex on subscription (url);')
        self.dbcur.execute('CREATE INDEX IF NOT EXISTS subtmindex on subscription (tmstmp);')

    def get_subs(self):
        sql_select = "SELECT * FROM subscription ORDER BY tmstmp ASC"
        subs = {}
        
        try:
            self.dbcur.execute(sql_select)
            for matchedrow in self.dbcur.fetchall():
                data = dict(matchedrow)
                subs.update({data['url']: data['name']})
        except Exception, e:
            print('SQL - failure: %s' % e)
            pass
        print('SAVED SUBS: ', subs)
        return subs
    
    def set_subs(self, subs):
        print('SET SUBS: ', subs)
        tmstmp = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        sql_insert = "INSERT INTO subscription( url, name, tmstmp ) VALUES(?, ?, ?)"
        for url, name in subs.iteritems():
            try:
                print('SAVE ITM: ', url, name)
                self.dbcur.execute(sql_insert, (url, name, tmstmp))
                self.dbcon.commit()
            except Exception, e:
                print('SQL - failure: %s' % e )
                pass
    
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

