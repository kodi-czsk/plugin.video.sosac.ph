# -*- coding: UTF-8 -*-
#/*
# *      Copyright (C) 2015 Libor Zoubek + jondas
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import re,os,urllib,urllib2,cookielib,json,xbmcaddon
import util
import pprint

from urlparse import urljoin
from provider import ContentProvider,cached,ResolveException

import sys
sys.setrecursionlimit(10000)

MOVIES_BASE_URL = "http://movies.prehraj.me"
TV_SHOWS_BASE_URL = "http://tv.prehraj.me"
MOVIES_A_TO_Z_TYPE = "movies-a-z"
TV_SHOWS_A_TO_Z_TYPE = "tv-shows-a-z"
TV_SHOW_FLAG = "#tvshow#"
ISO_639_1_CZECH = "cs"
MOST_POPULAR_TYPE = "most-popular"
RECENTLY_ADDED_TYPE = "recently-added"

try:
    import xbmc

    def debug(text):
        xbmc.log(str([text]), xbmc.LOGDEBUG)

    def info(text):
        xbmc.log(str([text]))

    def error(text):
        xbmc.log(str([text]), xbmc.LOGERROR)
except:
    def debug(text):
        if LOG > 1:
            print('[DEBUG] ' + str([text]))

    def info(text):
        if LOG > 0:
            print('[INFO] ' + str([text]))

    def error(text):
        print('[ERROR] ' + str([text]))

class SosacContentProvider(ContentProvider):

    def __init__(self,username=None,password=None,filter=None,reverse_eps=False):
        ContentProvider.__init__(self,name='sosac.ph', base_url=MOVIES_BASE_URL, username=username,password=password,filter=filter)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)
        self.reverse_eps = reverse_eps

    def capabilities(self):
        return ['resolve','categories']

    def categories(self):
        result = []
        for title, url in [("Movies", MOVIES_BASE_URL), ("TV Shows", TV_SHOWS_BASE_URL), ("Movies - Most popular", MOVIES_BASE_URL + "/" + MOST_POPULAR_TYPE), ("TV Shows - Most popular", TV_SHOWS_BASE_URL + "/" + MOST_POPULAR_TYPE), ("Movies - Recently added", MOVIES_BASE_URL + "/" + RECENTLY_ADDED_TYPE), ("TV Shows - Recently added", TV_SHOWS_BASE_URL + "/" + RECENTLY_ADDED_TYPE)]:
            item = self.dir_item(title=title, url=url)
            result.append(item)
        return result

    def a_to_z(self, url_type):
        result = []
        #user_language = 'cs'
        for letter in ['0-9','a','b','c','d','e','f','g','e','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']:
            item = self.dir_item(title=letter.upper())
            #if user_language == ISO_639_1_CZECH:
            # let's hardcode czech language
            item['url'] = self.base_url + "/" + url_type + "/" + letter
            #else:
            #    item['url'] = self.base_url + "/" + url_type + "/" + letter
            result.append(item)
        return result

    @staticmethod
    def remove_flag_from_url(url, flag):
        return url.replace(flag, "", count=1)

    @staticmethod
    def is_base_url(url):
        if url in [MOVIES_BASE_URL, TV_SHOWS_BASE_URL]:
            return True
        else:
            return False

    @staticmethod
    def is_movie_url(url):
        if MOVIES_BASE_URL in url:
            return True
        else:
            return False

    @staticmethod
    def is_tv_shows_url(url):
        if TV_SHOWS_BASE_URL in url:
            return True
        else:
            return False

    @staticmethod
    def is_most_popular(url):
        if MOST_POPULAR_TYPE in url:
            return True
        else:
            return False

    @staticmethod
    def is_recently_added(url):
        if RECENTLY_ADDED_TYPE in url:
            return True
        else:
            return False

    @staticmethod
    def particular_letter(url):
        return "a-z" in url

    def has_tv_show_flag(self, url):
        return TV_SHOW_FLAG in url

    def remove_flags(self, url):
        return url.replace(TV_SHOW_FLAG, "", 1)

    def list(self,url):
        print("Examining url", url)
        if self.is_most_popular(url):
            if "movie" in url:
                return self.list_movies_by_letter(url)
            if "tv" in url:
                return self.list_tv_shows_by_letter(url)
        if self.is_recently_added(url):
            debug("is recently added")
            if "movie" in url:
                return self.list_movie_recently_added(url)
            if "tv" in url:
                debug("is TV")
                return self.list_tv_recently_added(url)
        if self.is_base_url(url):
            self.base_url = url
            if "movie" in url:
                return self.a_to_z(MOVIES_A_TO_Z_TYPE)
            if "tv" in url:
                return self.a_to_z(TV_SHOWS_A_TO_Z_TYPE)

        if self.particular_letter(url):
            if "movie" in url:
                return self.list_movies_by_letter(url)
            if "tv" in url:
                return self.list_tv_shows_by_letter(url)

        if self.has_tv_show_flag(url):
            return self.list_tv_show(self.remove_flags(url))
        
        return [self.dir_item(title="I failed", url="fail")]

    def list_tv_show(self, url):
        result = []
        page = util.request(url)
        data = util.substr(page,'<div class=\"content\">','<script')
        for s in re.finditer('<strong.+?</ul>',data,re.IGNORECASE | re.DOTALL):
            serie = s.group(0)
            serie_name = re.search('<strong>([^<]+)',serie).group(1)
            for e in re.finditer('<li.+?</li>',serie,re.IGNORECASE | re.DOTALL):
                episode = e.group(0)
                item = self.video_item()
                ep_name = re.search('<a href=\"#[^<]+<span>(?P<id>[^<]+)</span>(?P<name>[^<]+)',episode)
                if ep_name:
                    item['title'] = '%s %s %s' % (serie_name,ep_name.group('id'),ep_name.group('name'))
                    item['ep'] = ep_name
                i = re.search('<div class=\"inner-item[^<]+<img src=\"(?P<img>[^\"]+).+?<a href=\"(?P<url>[^\"]+)',episode, re.IGNORECASE | re.DOTALL)
                if i:
                    item['img'] = self._url(i.group('img'))
                    item['url'] = i.group('url')
                if i and ep_name:
                    self._filter(result,item)
        if self.reverse_eps:
            result.reverse()
        return result


    def add_video_flag(self, items):
        flagged_items = []
        for item in items:
            flagged_item = self.video_item()
            flagged_item.update(item)
            flagged_items.append(flagged_item)
        return flagged_items

    def add_directory_flag(self, items):
        flagged_items = []
        for item in items:
            flagged_item = self.dir_item()
            flagged_item.update(item)
            flagged_items.append(flagged_item)
        return flagged_items

    @cached(ttl=24)
    def list_by_letter(self, url):
        result = []
        page = util.request(url)
        data = util.substr(page,'<ul class=\"content','</ul>')
        for m in re.finditer('<a class=\"title\" href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)',data,re.IGNORECASE | re.DOTALL):
            item = {}
            item['url'] = m.group('url')
            item['title'] = m.group('name')
            item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]" : {'url':m.group('url'), 'action':'add-to-library', 'name': m.group('name')}}
            self._filter(result,item)
        paging = util.substr(page,'<div class=\"pagination\"','</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page=(?P<page>\d+)',paging,re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page=(?P<page>\d)',url)
            current_page = 0
            if self.is_most_popular(url) and next_page > 10:
                return result
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$','',url) + '?page='+str(next_page)
                result += self.list_by_letter(url)
        print("RES: ", result)
        return result

    def run_custom(self, params):
        if params['action'] == 'add-to-library':
#            import json
#            url = "http://csfd.bbaron.sk/find.php?json=" + urllib.quote(json.dumps([params['name']])) + ";details=1"
#            print("URL: ", url)
#            data = util.request(url)
#            try:
#                data = json.loads(data)
#                print("Mame data: ", data)
#            except Exception, e:
#                data = {"name_orig": params['name']}
#                print("Nenasli sa data na serveri", params['name'])
            icon = os.path.join(params['__addon__'].getAddonInfo('path'),'icon.png')
            arg = {"play": params['url'], 'cp': 'sosac.ph'}
            item_url = util._create_plugin_url(arg, 'plugin://plugin.video.sosac.ph/')
            new_items = False
            if "movie" in params['url']:
                xbmc.executebuiltin('XBMC.Notification(%s,%s,3000,%s)' % ('Linking',params['name'],icon))
                item_dir = params['__addon__'].getSetting('library-movies')
                self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), self.normalize_filename(params['name'])) + '.strm', item_url)
            else:
                xbmc.executebuiltin('XBMC.Notification(%s,%s,3000,%s)' % ('Linking',params['name'],icon))
                subs = self.get_subs()
                
                if not params['url'] in subs.keys():
                    subs.update({params['url']: params['name']})
                    params['__addon__'].setSetting('tvshows-subs', json.dumps(subs))
                
                list = self.list_tv_show(params['url'])
                for itm in list:
                    arg = {"play": itm['url'], 'cp': 'sosac.ph'}
                    item_url = util._create_plugin_url(arg, 'plugin://plugin.video.sosac.ph/')
                    item_dir = params['__addon__'].getSetting('library-tvshows')
                    nfo = re.search('[^\d+](?P<season>\d+)[^\d]+(?P<episode>\d+)', itm['title'], re.IGNORECASE | re.DOTALL)
                    ret = self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), 'Season ' + nfo.group('season'), "S" + nfo.group('season') + "E" + nfo.group('episode') + '.strm'), item_url)
                    if ret[1] == True:
                        new_items = True
                if new_items and not 'update' in params:
                    xbmc.executebuiltin('UpdateLibrary(video)')
            xbmc.executebuiltin('XBMC.Notification(%s,%s,3000,%s)' % ('Done','Linking',icon))
            return new_items

    @staticmethod
    def normalize_filename(name):
        return name.replace('/','-').replace('\\','-').replace(':', '-').replace('*', '-').replace('!', '').replace('?', '')

    @staticmethod
    def get_subs():
        subs = xbmcaddon.Addon('plugin.video.sosac.ph').getSetting('tvshows-subs')
        if (subs == ""):
            subs = {}
        else:
            subs = json.loads(subs)
        return subs

    @staticmethod
    def add_item_to_library(item_path, item_url):
        error = False
        print("path: ", item_path)
        new = False
        if item_path:
            
            import xbmcvfs
            import os, codecs
            import unicodedata
            
            item_path = os.path.normpath(unicodedata.normalize('NFKD', item_path.decode('utf-8')).encode('ascii', 'ignore'))
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

    @cached(ttl=24)
    def list_tv_recently_added(self, url):
        result = []
        page = util.request(url)
        data = util.substr(page,'<div class=\"content\"','</ul>')
        for m in re.finditer('<a href=\"(?P<url>[^\"]+)[^>]+((?!<strong).)*<strong>S(?P<serie>\d+) / E(?P<epizoda>\d+)</strong>((?!<a href).)*<a href=\"(?P<surl>[^\"]+)[^>]+class=\"mini\">((?!<span>).)*<span>\((?P<name>[^)]+)\)<', data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['url'] = m.group('url')
            item['title'] = "Rada " + m.group('serie') + " Epizoda " + m.group('epizoda') + " - " + m.group('name')
            item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]" : {'url':m.group('url'), 'action':'add-to-library', 'name': m.group('name') + " S" + m.group('serie') + 'E'+m.group('epizoda')}}
            self._filter(result,item)
        paging = util.substr(page,'<div class=\"pagination\"','</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page_1=(?P<page>\d+)',paging,re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page_1=(?P<page>\d)',url)
            current_page = 0
            if next_page > 30:
                return result
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$','',url) + '?page_1='+str(next_page)
                result += self.list_tv_recently_added(url)
        return result

    @cached(ttl=24)
    def list_movie_recently_added(self, url):
        result = []
        page = util.request(url)
        data = util.substr(page,'<div class=\"content\"','</ul>')
        for m in re.finditer('<a class=\"content-block\" href=\"(?P<url>[^\"]+)\" title=\"(?P<name>[^\"]+)', data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['url'] = m.group('url')
            item['title'] = m.group('name')
            item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]" : {'url':m.group('url'), 'action':'add-to-library', 'name': m.group('name')}}
            self._filter(result,item)
        paging = util.substr(page,'<div class=\"pagination\"','</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page=(?P<page>\d+)',paging,re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page=(?P<page>\d)',url)
            current_page = 0
            if next_page > 30:
                return result
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$','',url) + '?page='+str(next_page)
                result += self.list_movie_recently_added(url)
        return result

    def add_flag_to_url(self, item, flag):
        item['url'] = flag + item['url']
        return item

    def add_url_flag_to_items(self, items, flag):
        subs = self.get_subs()
        print("SUBS: ", subs)
        for item in items:
            print("ITEM: ", item)
            if item['url'] in subs:
                item['title'] = '[B][COLOR yellow]*[/COLOR][/B]' + item['title']
                print("MAME SUBS:", item['title'])
            self.add_flag_to_url(item, flag)
        return items

    def _url(self, url):
        return self.base_url + "/" + url.lstrip('./')

    def list_tv_shows_by_letter(self, url):
        print("Getting shows by letter", url)
        shows = self.list_by_letter(url)
        print("Resloved shows", shows)
        shows = self.add_directory_flag(shows)
        return self.add_url_flag_to_items(shows, TV_SHOW_FLAG)

    def list_movies_by_letter(self, url):
        movies = self.list_by_letter(url)
        print("Resolved movies", movies)
        return self.add_video_flag(movies)

    def resolve(self,item,captcha_cb=None,select_cb=None):
        page = util.request(item['url'])
        data = util.substr(page,'<div class=\"bottom-player\"','div>')
        if data.find('<iframe') < 0:
            raise ResolveException('Video is not available.')
        result = self.findstreams(data,['<iframe src=\"(?P<url>[^\"]+)'])
        if len(result)==1:
            return result[0]
        elif len(result) > 1 and select_cb:
            return select_cb(result)
