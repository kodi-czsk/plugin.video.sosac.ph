import util
import xbmcprovider
import xbmcutil
import xbmcvfs
import xbmcgui
import xbmc
import unicodedata
import os
import re
import time
import string
import datetime
import urllib
import sosac


class XBMCSosac(xbmcprovider.XBMCMultiResolverContentProvider):
    last_run = 0
    sleep_time = 1000 * 1 * 60
    subs = None

    def __init__(self, provider, settings, addon):
        xbmcprovider.XBMCMultiResolverContentProvider.__init__(
            self, provider, settings, addon)
        provider.parent = self
        self.dialog = xbmcgui.DialogProgress()
        try:
            import StorageServer
            self.cache = StorageServer.StorageServer("Downloader")
        except:
            import storageserverdummy as StorageServer
            self.cache = StorageServer.StorageServer("Downloader")

    def make_name(self, text, lower=True):
        text = self.normalize_filename(
            text, "-_.' %s%s" % (string.ascii_letters, string.digits))
        word_re = re.compile(r'\b\w+\b')
        text = ''.join([c for c in text if (c.isalnum() or c == "'" or c ==
                                            '.' or c == '-' or c.isspace())]) if text else ''
        text = '-'.join(word_re.findall(text))
        return text.lower() if lower else text

    def normalize_filename(self, name, validChars=None):
        validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        if (validChars is not None):
            validFilenameChars = validChars
        cleanedFilename = self.encode(name)
        return ''.join(c for c in cleanedFilename if c in validFilenameChars)

    def service(self):
        util.info("SOSAC Service Started")
        try:
            sleep_time = int(self.getSetting("start_sleep_time")) * 1000 * 60
        except:
            sleep_time = self.sleep_time
            pass

        self.sleep(sleep_time)

        try:
            self.last_run = float(self.cache.get("subscription.last_run"))
        except:
            self.last_run = time.time()
            self.cache.set("subscription.last_run", str(self.last_run))
            pass

        if not xbmc.abortRequested and time.time() > self.last_run:
            self.evalSchedules()

        while not xbmc.abortRequested:
            # evaluate subsciptions every 10 minutes
            if(time.time() > self.last_run + 600):
                self.evalSchedules()
                self.last_run = time.time()
                self.cache.set("subscription.last_run", str(self.last_run))
            self.sleep(self.sleep_time)
        util.info("SOSAC Shutdown")

    def showNotification(self, title, message, time=1000):
        xbmcgui.Dialog().notification(self.encode(title), self.encode(message), time=time,
                                      icon=xbmc.translatePath(
                                          self.addon_dir() + "/icon.png"),
                                      sound=False)

    def evalSchedules(self):
        if not self.scanRunning() and not self.isPlaying():
            notified = False
            util.info("SOSAC Loading subscriptions")
            subs = self.get_subs()
            new_items = False
            for url, sub in subs.iteritems():
                if xbmc.abortRequested:
                    util.info("SOSAC Exiting")
                    return
                if sub['type'] == sosac.LIBRARY_TYPE_TVSHOW:
                    if self.scanRunning() or self.isPlaying():
                        self.cache.delete("subscription.last_run")
                        return
                    refresh = int(sub['refresh'])
                    if refresh > 0:
                        next_check = sub['last_run'] + (refresh * 3600 * 24)
                        if next_check < time.time():
                            if not notified:
                                self.showNotification(
                                    'Subscription', 'Chcecking')
                                notified = True
                            util.debug("SOSAC Refreshing " + url)
                            new_items |= self.run_custom({
                                'action': sosac.LIBRARY_ACTION_ADD,
                                'type': sosac.LIBRARY_TYPE_TVSHOW,
                                'update': True,
                                'url': url,
                                'name': sub['name'],
                                'refresh': sub['refresh']
                            })
                            self.sleep(3000)
                        else:
                            n = (next_check - time.time()) / 3600
                            util.debug("SOSAC Skipping " + url +
                                       " , next check in %dh" % n)
            if new_items:
                xbmc.executebuiltin('UpdateLibrary(video)')
            notified = False
        else:
            util.info("SOSAC Scan skipped")

    def isPlaying(self):
        return xbmc.Player().isPlaying()

    def scanRunning(self):
        return (xbmc.getCondVisibility('Library.IsScanningVideo') or
                xbmc.getCondVisibility('Library.IsScanningMusic'))

    def getBBDB(self, name):
        name = util.request('http://csfd.bbaron.sk/find.php?' +
                            urllib.urlencode({'sosac': 1, 'name': name}))
        if name != '':
            return self.getTVDB(name, 1)
        return None

    def getTVDB(self, name, level=0):
        data = util.request('http://thetvdb.com/api/GetSeries.php?' +
                            urllib.urlencode({'seriesname': name, 'language': 'cs'}))
        try:
            tvid = re.search('<id>(\d+)</id>', data).group(1)
        except:
            if level == 0:
                tvid = self.getBBDB(name)
            else:
                tvid = None
        return tvid

    def add_item(self, params):
        error = False
        if not 'refresh' in params:
            params['refresh'] = str(self.getSetting("refresh_time"))
        sub = {'name': params['name'], 'refresh': params[
            'refresh'], 'type': params['type']}

        sub['last_run'] = time.time()
        arg = {"play": params['url'], 'cp': 'sosac.ph', "title": sub['name']}
        item_url = xbmcutil._create_plugin_url(
            arg, 'plugin://' + self.addon_id + '/')
        util.info("item: " + item_url + " | " + str(params))
        new_items = False
        # self.showNotification('Linking', params['name'])

        if params['type'] == sosac.LIBRARY_TYPE_VIDEO:
            # movies are not stored in subs database
            item_dir = self.getSetting('library-movies')

            nfo_file = os.path.join(item_dir, self.normalize_filename(
                sub['name']), self.normalize_filename(params['name']) + '.nfo')
            if not xbmcvfs.exists(nfo_file):
                metadata = ""
                if 'imdb' in params:
                    metadata += "http://www.imdb.com/title/tt{0}/\n".format(params['imdb'])
                if 'csfd' in params:
                    metadata += "http://www.csfd.cz/film/{0}\n".format(params['csfd'])

                self.add_item_to_library(nfo_file, metadata)

            (error, new_items) = self.add_item_to_library(
                os.path.join(item_dir, self.normalize_filename(sub['name']), self.normalize_filename(params['name'])) + '.strm', item_url)
        elif params['type'] == sosac.LIBRARY_TYPE_TVSHOW:
            if not ('notify' in params):
                self.showNotification(sub['name'], 'Checking new content')

            subs = self.get_subs()
            item_dir = self.getSetting('library-tvshows')

            subs.update({params['url']: sub})
            self.set_subs(subs)
            # self.addon.setSetting('tvshows-subs', json.dumps(subs))
            nfo_file = os.path.join(item_dir, self.normalize_filename(params['name']), 'tvshow.nfo')
            if not xbmcvfs.exists(nfo_file):
                metadata = ""
                if 'imdb' in params:
                    metadata += "http://www.imdb.com/title/tt{0}/\n".format(params['imdb'])
                if 'csfd' in params:
                    metadata += "http://www.csfd.cz/film/{0}\n".format(params['csfd'])
                tvid = self.getTVDB(params['name'])
                if tvid:
                    metadata += "http://thetvdb.com/index.php?tab=series&id={0}\n".format(tvid)
                    self.add_item_to_library(nfo_file, metadata)

            episodes = self.provider.list_episodes(params['url'])
            for itm in episodes:
                arg = {"play": itm['url'], 'cp': 'sosac.ph',
                       "title": itm['title']}
                item_url = xbmcutil._create_plugin_url(
                    arg, 'plugin://' + self.addon_id + '/')
                dirname = "Season " + str(itm['season'])
                epname = "S%02dE%02d.strm" % (itm['season'], itm['episode'])
                filename = os.path.join(item_dir, self.normalize_filename(
                    params['name']), dirname, epname)
                (err, new) = self.add_item_to_library(filename, item_url)
                error |= err
                if new is True and not err:
                    new_items = True
        if not error and new_items and not ('update' in params) and not ('notify' in params):
            self.showNotification(params['name'], 'Found new content')
            xbmc.executebuiltin('UpdateLibrary(video)')
        elif not error and not ('notify' in params):
            self.showNotification(params['name'], 'No new content')
        if error and not ('notify' in params):
            self.showNotification('Failed, Please check kodi logs', 'Linking')
        return new_items

    def run_custom(self, params):
        if 'action' in params:
            icon = os.path.join(self.addon.getAddonInfo('path'), 'icon.png')
            if params['action'] == sosac.LIBRARY_ACTION_REMOVE_SUBSCRIPTION:
                subs = self.get_subs()
                if params['url'] in subs.keys():
                    del subs[params['url']]
                    self.set_subs(subs)
                    self.showNotification(
                        params['name'], 'Removed from subscriptions')
                    xbmc.executebuiltin('Container.Refresh')
                return False

            if params['action'] == sosac.LIBRARY_ACTION_ADD:
                if self.add_item(params):
                    xbmc.executebuiltin('Container.Refresh')
                    return True
                return False
            if params['action'] == sosac.LIBRARY_ACTION_REMOVE_ALL:
                self.set_subs({})
                return True
            if params['action'] == sosac.LIBRARY_ACTION_ADD_ALL:
                self.dialog.create("Sosac", "Adding All Movies to library")
                self.dialog.update(0)
                if params['type'] == sosac.LIBRARY_TYPE_ALL_VIDEOS:
                    self.dialog.create("Sosac", "Adding All Movies to library")
                    self.dialog.update(0)
                    videos = self.provider.library_list_all_videos()
                    for video in videos:
                        if self.dialog.iscanceled():
                            return
                        if 'progress' in video:
                            self.dialog.update(video['progress'])
                        else:
                            item = video['menu'][sosac.LIBRARY_MENU_ITEM_ADD]
                            item["update"] = True
                            item["notify"] = True
                            item["type"] = sosac.LIBRARY_TYPE_VIDEO
                            self.add_item(item)
                    self.dialog.close()
                if params['type'] == sosac.LIBRARY_TYPE_RECENT_VIDEOS:
                    self.dialog.create("Sosac", "Adding Recent Movies to library")
                    self.dialog.update(0)
                    videos = self.provider.library_list_recent_videos()
                    for video in videos:
                        if self.dialog.iscanceled():
                            return
                        if 'progress' in video:
                            self.dialog.update(video['progress'])
                        else:
                            item = video['menu'][sosac.LIBRARY_MENU_ITEM_ADD]
                            item["update"] = True
                            item["notify"] = True
                            item["type"] = sosac.LIBRARY_TYPE_VIDEO
                            self.add_item(item)
                    self.dialog.close()
                elif params['type'] == sosac.LIBRARY_TYPE_ALL_SHOWS:
                    self.dialog.create(
                        "Sosac", "Adding All TV Shows to library")
                    self.dialog.update(0)
                    shows = self.provider.library_list_all_tvshows()
                    for show in shows:
                        if self.dialog.iscanceled():
                            return
                        if 'progress' in show:
                            self.dialog.update(show['progress'])
                        else:
                            item = show['menu'][sosac.LIBRARY_MENU_ITEM_ADD]
                            item["update"] = True
                            item["notify"] = True
                            item["type"] = sosac.LIBRARY_TYPE_TVSHOW
                            self.add_item(item)

                xbmc.executebuiltin('UpdateLibrary(video)')
        return False

    def add_item_to_library(self, item_path, item_url):
        error = False
        new = False
        if item_path:
            item_path = xbmc.translatePath(item_path)
            dir = os.path.dirname(item_path)
            if not xbmcvfs.exists(dir):
                try:
                    xbmcvfs.mkdirs(dir)
                except Exception, e:
                    error = True
                    util.error('Failed to create directory 1: ' + dir)

            if not xbmcvfs.exists(item_path):
                try:
                    file_desc = xbmcvfs.File(item_path, 'w')
                    file_desc.write(item_url)
                    file_desc.close()
                    new = True
                except Exception, e:
                    util.error('Failed to create .strm file: ' +
                               item_path + " | " + str(e))
                    error = True
        else:
            error = True

        return (error, new)

    def get_subs(self):
        if self.subs is not None:
            return self.subs
        data = self.cache.get("subscription-1")
        try:
            if data == '':
                return {}
            self.subs = eval(data)
            return self.subs
        except Exception, e:
            util.error(e)
            return {}

    def set_subs(self, subs):
        self.subs = subs
        self.cache.set("subscription-1", repr(subs))

    @staticmethod
    def encode(string):
        return unicodedata.normalize('NFKD', string.decode('utf-8')).encode('ascii', 'ignore')

    def addon_dir(self):
        return self.addon.getAddonInfo('path')

    def data_dir(self):
        return self.addon.getAddonInfo('profile')

    def getSetting(self, name):
        return self.addon.getSetting(name)

    def getString(self, string_id):
        return self.addon.getLocalizedString(string_id)

    @staticmethod
    def sleep(sleep_time):
        while not xbmc.abortRequested and sleep_time > 0:
            sleep_time -= 1
            xbmc.sleep(1)
