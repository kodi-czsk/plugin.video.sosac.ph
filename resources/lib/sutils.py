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
import myPlayer
import json
import buggalo


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

    @staticmethod
    def executeJSON(request):
        # =====================================================================
        # Execute JSON-RPC Command
        # Args:
        # request: Dictionary with JSON-RPC Commands
        # Found code in xbmc-addon-service-watchedlist
        # =====================================================================
        rpccmd = json.dumps(request)    # create string from dict
        json_query = xbmc.executeJSONRPC(rpccmd)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        return json_response

    @staticmethod
    def adjustGenre(genre):
        result = ''
        for g in genre:
            result = result + g + u' / '
        return result[:-3]

    @staticmethod
    def adjustCast(cast):
        result = []
        for c in cast:
            result.append((c['name'], c['role']))
        return result

    def play(self, item):
        # ======================================================================
        # Override from xbmcprovider
        # ======================================================================
        buggalo.SUBMIT_URL = 'http://sosac.comli.com/submit.php'
        if 'title' in item['info'].keys():
            try:
                pomTitle = item['info']['title']
                while True:
                    JSON_req = {"jsonrpc": "2.0",
                                "method": "Files.GetFileDetails",
                                "params": {"file": pomTitle,
                                           "media": "video", },
                                "id": "1"}
                    JSON_result = self.executeJSON(JSON_req)
                    if 'result' in JSON_result.keys() and \
                       'id' in JSON_result["result"]["filedetails"].keys():
                        break
                    else:
                        pomTitle = xbmc.translatePath(item['info']['title'])
                pomItemType = JSON_result["result"]["filedetails"]["type"]
                pomItemDBID = JSON_result["result"]["filedetails"]["id"]
            except Exception:
                buggalo.onExceptionRaised({'vstup': '%s' % json.dumps(JSON_req, indent=2),
                                           'vystup': json.dumps(JSON_result, indent=2),
                                           'knihovna': xbmc.translatePath('special://database')})
            if pomItemType == u'episode':
                JSON_req = {"jsonrpc": "2.0",
                            "method": "VideoLibrary.GetEpisodeDetails",
                            "params": {"episodeid": pomItemDBID,
                                       "properties": ["title", "plot", "votes",
                                                      "firstaired", "playcount", "runtime",
                                                      "rating", "director", "userrating",
                                                      "writer", "streamdetails", "cast",
                                                      "productioncode", "season", "episode",
                                                      "originaltitle", "showtitle", "lastplayed",
                                                      "thumbnail", "file", "tvshowid",
                                                      "dateadded", "uniqueid", "art", "fanart"]},
                            "id": "1"}
                JSON_result = self.executeJSON(JSON_req)
                # tvshowtitle in listitem info vs showtitle in database !!!
                JSON_result['result']['episodedetails']['tvshowtitle'] = \
                    JSON_result['result']['episodedetails']['showtitle']
                # for cast list of tuples needed
                JSON_result['result']['episodedetails']['cast'] = self.adjustCast(
                    JSON_result['result']['episodedetails']['cast'])
                item['info'] = JSON_result['result']['episodedetails']
            elif pomItemType == u'movie':
                JSON_req = {"jsonrpc": "2.0",
                            "method": "VideoLibrary.GetMovieDetails",
                            "params": {"movieid": pomItemDBID,
                                       "properties": ["title", "plot", "votes", "rating",
                                                      "studio", "playcount", "runtime", "director",
                                                      "trailer", "tagline", "plotoutline",
                                                      "streamdetails",
                                                      "mpaa", "imdbnumber", "sorttitle", "setid",
                                                      "originaltitle", "lastplayed", "writer",
                                                      "thumbnail", "file",
                                                      "userrating",
                                                      "dateadded", "art", "fanart", "genre",
                                                      "cast"]},
                            "id": "1"}
                JSON_result = self.executeJSON(JSON_req)
                # for cast list of tuples needed
                JSON_result['result']['moviedetails']['cast'] = self.adjustCast(
                    JSON_result['result']['moviedetails']['cast'])
                # for genre one string needed
                JSON_result['result']['moviedetails']['genre'] = self.adjustGenre(
                    JSON_result['result']['moviedetails']['genre'])
                item['info'] = JSON_result['result']['moviedetails']
            super(XBMCSosac, self).play(item)
            mujPlayer = myPlayer.MyPlayer(
                itemType=pomItemType, itemDBID=pomItemDBID)
            c = 0
            while not mujPlayer.isPlaying() and c < 2:
                self.sleep(2000)
                c += 1
            while mujPlayer.isPlaying():
                self.sleep(5000)
        else:
            super(XBMCSosac, self).play(item)

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
                if self.provider.is_tv_shows_url(url):
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
                                'action': 'add-to-library',
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
        sub = {'name': params['name'], 'refresh': params['refresh']}
        sub['last_run'] = time.time()
        item_dir = self.getSetting('library-movies')
        title_pom = os.path.join(item_dir, self.normalize_filename(sub['name']),
                                 self.normalize_filename(params['name'])) + '.strm'
        arg = {"play": params['url'], 'cp': 'sosac.ph', "title": title_pom}
        item_url = xbmcutil._create_plugin_url(
            arg, 'plugin://' + self.addon_id + '/')
        util.info("item: " + item_url + " | " + str(params))
        new_items = False
        # self.showNotification('Linking', params['name'])

        if "movie" in params['url']:
            item_dir = self.getSetting('library-movies')
            (error, new_items) = self.add_item_to_library(title_pom, item_url)
        else:
            if not ('notify' in params):
                self.showNotification(sub['name'], 'Checking new content')

            subs = self.get_subs()
            item_dir = self.getSetting('library-tvshows')

            if not params['url'] in subs.keys():
                subs.update({params['url']: params['name']})
                self.set_subs(subs)
                # self.addon.setSetting('tvshows-subs', json.dumps(subs))

            if not xbmcvfs.exists(os.path.join(item_dir, self.normalize_filename(params['name']),
                                               'tvshow.nfo')):
                tvid = self.getTVDB(params['name'])
                if tvid:
                    self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(
                        params['name']), 'tvshow.nfo'),
                        'http://thetvdb.com/index.php?tab=series&id=' + tvid)

            list = self.provider.list_tv_show(params['url'])
            for itm in list:
                nfo = re.search('[^\d+](?P<season>\d+)[^\d]+(?P<episode>\d+)',
                                itm['title'], re.IGNORECASE | re.DOTALL)
                title_pom = os.path.join(
                    item_dir, self.normalize_filename(params['name']),
                    'Season ' + nfo.group('season'),
                    "S" + nfo.group('season') +
                    "E" + nfo.group('episode') + '.strm')
                arg = {"play": itm['url'], 'cp': 'sosac.ph',
                       "title": title_pom}
                """
                info = ''.join(('<episodedetails><season>', nfo.group('season'),
                                '</season><episode>', nfo.group('episode'),
                                '</episode></episodedetails>'))
                """
                item_url = xbmcutil._create_plugin_url(
                    arg, 'plugin://' + self.addon_id + '/')
                (err, new) = self.add_item_to_library(title_pom, item_url)
                error |= err
                if new is True and not err:
                    new_items = True
        if not error and new_items and not ('update' in params) and not ('notify' in params):
            self.showNotification(params['name'], 'New content')
            xbmc.executebuiltin('UpdateLibrary(video)')
        elif not error and not ('notify' in params):
            self.showNotification(params['name'], 'No new content')
        if error and not ('notify' in params):
            self.showNotification('Failed, Please check kodi logs', 'Linking')
        return new_items

    def run_custom(self, params):
        if 'action' in params.keys():
            icon = os.path.join(self.addon.getAddonInfo('path'), 'icon.png')
            if params['action'] == 'remove-subscription':
                subs = self.get_subs()
                if params['url'] in subs.keys():
                    del subs[params['url']]
                    self.set_subs(subs)
                    self.showNotification(
                        params['name'], 'Removed from subscription')
                    xbmc.executebuiltin('Container.Refresh')
                return False

            if params['action'] == 'add-to-library':
                if self.add_item(params):
                    xbmc.executebuiltin('Container.Refresh')
                    return True
                return False
            if params['action'] == 'add-all-to-library':
                self.dialog.create('sosac', 'Add all to library')
                self.dialog.update(0)
                if params['title'] == 'Movies':
                    self.provider.library_movies_all_xml()
                elif params['title'] == 'Movies - Recently added':
                    self.provider.library_movie_recently_added_xml()
                elif params['title'] == 'TV Shows':
                    self.provider.library_tvshows_all_xml()
                self.dialog.close()
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
                    util.error('Failed to create .strm file: ' + item_path + " | " + str(e))
                    error = True
        else:
            error = True

        return (error, new)

    def get_subs(self):
        if self.subs is not None:
            return self.subs
        data = self.cache.get("subscription")
        try:
            if data == '':
                return {}
            subs = eval(data)
            for url, name in subs.iteritems():
                if not isinstance(name, dict):
                    subs[url] = {'name': name,
                                 'refresh': '1', 'last_run': -1}
            self.set_subs(subs)
            self.subs = subs
        except Exception, e:
            util.error(e)
            subs = {}
        return subs

    def set_subs(self, subs):
        self.subs = subs
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

    def getString(self, string_id):
        return self.addon.getLocalizedString(string_id)

    @staticmethod
    def sleep(sleep_time):
        while not xbmc.abortRequested and sleep_time > 0:
            sleep_time -= 1
            xbmc.sleep(1)
