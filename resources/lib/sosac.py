# -*- coding: UTF-8 -*-
# /*
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

import urllib
import urllib2
import cookielib
import sys
import json

import util
from provider import ContentProvider, cached, ResolveException

sys.setrecursionlimit(10000)

MOVIES_BASE_URL = "http://movies.prehraj.me"
TV_SHOW_FLAG = "#tvshow#"
ISO_639_1_CZECH = "cs"

#JSONs
URL = "http://tv.sosac.to"
J_MOVIES_A_TO_Z_TYPE = "/vystupy5981/souboryaz.json"
J_MOVIES_GENRE = "/vystupy5981/souboryzanry.json"
J_MOVIES_MOST_POPULAR = "/vystupy5981/moviesmostpopular.json"
J_MOVIES_RECENTLY_ADDED = "/vystupy5981/moviesrecentlyadded.json"
#hack missing json with a-z series 
J_TV_SHOWS_A_TO_Z_TYPE = "/vystupy5981/tvpismenaaz/"
J_TV_SHOWS = "/vystupy5981/tvpismena/"
J_SERIES = "/vystupy5981/serialy/"
J_TV_SHOWS_MOST_POPULAR = "/vystupy5981/tvshowsmostpopular.json"
J_TV_SHOWS_RECENTLY_ADDED = "/vystupy5981/tvshowsrecentlyadded.json"
J_SEARCH = "/jsonsearchapi.php?q="
STREAMUJ_URL = "http://www.streamuj.tv/video/"
IMAGE_URL = "http://movies.sosac.tv/images/"
IMAGE_MOVIE = IMAGE_URL + "75x109/movie-"
IMAGE_SERIES = IMAGE_URL + "558x313/serial-"
IMAGE_EPISODE = URL

RATING = 'r'
LANG = 'd'
QUALITY = 'q'

class SosacContentProvider(ContentProvider):
    ISO_639_1_CZECH = None
    par = None

    def __init__(self, username=None, password=None, filter=None, reverse_eps=False):
        ContentProvider.__init__(self, name='sosac.ph', base_url=MOVIES_BASE_URL, username=username,
                                 password=password, filter=filter)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)
        self.reverse_eps = reverse_eps

    def on_init(self):
        kodilang = self.lang or 'cs'
        if kodilang == ISO_639_1_CZECH or kodilang == 'sk':
            self.ISO_639_1_CZECH = ISO_639_1_CZECH + '/'
        else:
            self.ISO_639_1_CZECH = ''

    def capabilities(self):
        return ['resolve', 'categories', 'search']

    def categories(self):
        result = []
        for title, url in [
            ("Movies", URL + J_MOVIES_A_TO_Z_TYPE),
            ("TV Shows", URL + J_TV_SHOWS_A_TO_Z_TYPE),
            ("Movies - by Genres", URL + J_MOVIES_GENRE),
            ("Movies - Most popular", URL + J_MOVIES_MOST_POPULAR),
            ("TV Shows - Most popular", URL + J_TV_SHOWS_MOST_POPULAR),
            ("Movies - Recently added", URL + J_MOVIES_RECENTLY_ADDED),
            ("TV Shows - Recently added", URL + J_TV_SHOWS_RECENTLY_ADDED)]:
            item = self.dir_item(title=title, url=url)
#            if title == 'Movies' or title == 'TV Shows' or title == 'Movies - Recently added':
#                item['menu'] = {"[B][COLOR red]Add all to library[/COLOR][/B]": {
#                    'action': 'add-all-to-library', 'title': title}}
            result.append(item)
        return result

    def search(self, keyword):
        return self.list_search(URL + J_SEARCH + urllib.quote_plus(keyword))

    def a_to_z(self, url):
        result = []
        for letter in ['0-9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'e', 'h', 'i', 'j', 'k', 'l', 'm',
                       'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
            item = self.dir_item(title=letter.upper())
            item['url'] = URL + url + letter + ".json"
            result.append(item)
        return result

    @staticmethod
    def remove_flag_from_url(url, flag):
        return url.replace(flag, "", count=1)

    @staticmethod
    def particular_letter(url):
        return "a-z/" in url

    def has_tv_show_flag(self, url):
        return TV_SHOW_FLAG in url

    def remove_flags(self, url):
        return url.replace(TV_SHOW_FLAG, "", 1)

    def list(self, url):
        util.info("Examining url " + url)
        if J_MOVIES_A_TO_Z_TYPE in url:
            return self.load_json_list(url)
        if J_MOVIES_GENRE in url:
            return self.load_json_list(url)
        if J_MOVIES_MOST_POPULAR in url:
            return self.list_videos(url)
        if J_MOVIES_RECENTLY_ADDED in url:
            return self.list_videos(url)
        if J_TV_SHOWS_A_TO_Z_TYPE in url:
            return self.a_to_z(J_TV_SHOWS)
        if J_TV_SHOWS in url:
            return self.list_series_letter(url)
        if J_SERIES in url:
            return self.list_episodes(url)
        if J_TV_SHOWS_MOST_POPULAR  in url:
            return self.list_series_letter(url)
        if J_TV_SHOWS_RECENTLY_ADDED in url:
            return self.list_recentlyadded_episodes(url)
        return self.list_videos(url)
    
    def load_json_list(self, url):
        result = []
        data = util.request(url)
        json_list = json.loads(data)
        for key, value in json_list.iteritems():
            item = self.dir_item(title=key.upper())
            item['url'] = value
            result.append(item)
        return result
    
    def list_videos(self, url):
        result = []
        data = util.request(url)
        json_video_array = json.loads(data)
        for video in json_video_array:
            item = self.video_item()
            item['title'] = video['n'][ISO_639_1_CZECH] +" ("+ video['y']+")"
            item['img'] =  IMAGE_MOVIE + video['i']
            item['url'] = video['l']
            if RATING in video:
                item['rating'] = video[RATING]
            if LANG in video:
                item['lang'] = video[LANG]
            if QUALITY in video:
                item['quality'] = video[QUALITY]
            result.append(item)
        return result
    
    def list_series_letter(self, url):
        result = []
        data = util.request(url)
        json_list = json.loads(data)
        for serial in json_list:
            item = self.dir_item()
            item['title'] = serial['n'][ISO_639_1_CZECH]
            item['img'] = IMAGE_SERIES + serial['i']
            item['url'] = serial['l']
            result.append(item)
        return result
    
    def list_episodes(self, url):
        result = []
        data = util.request(url)
        json_series = json.loads(data)
        for series in json_series:
            for series_key, episode in series.iteritems():
                for episode_key, video in episode.iteritems():
                    item = self.video_item()
                    item['title'] = series_key + "x" + episode_key + " - " + video['n']
                    item['img'] =  IMAGE_EPISODE + video['i']
                    item['url'] = video['l']
                    result.append(item)
        if not self.reverse_eps:
            result.reverse()
        return result
    
    def list_recentlyadded_episodes(self, url):
        result = []
        data = util.request(url)
        json_series = json.loads(data)
        for episode in json_series:
            item = self.video_item()
            item['title'] = episode['t'][ISO_639_1_CZECH] + ' ' + episode['s'] + "x" + episode['e'] + " - " + episode['n'][ISO_639_1_CZECH]
            item['img'] =  IMAGE_EPISODE + episode['i']
            item['url'] = episode['l']
            result.append(item)
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
    def get_data_cached(self, url):
        return util.request(url)

    def add_flag_to_url(self, item, flag):
        item['url'] = flag + item['url']
        return item

    def add_url_flag_to_items(self, items, flag):
        subs = self.get_subs()
        for item in items:
            if item['url'] in subs:
                item['title'] = '[B][COLOR yellow]*[/COLOR][/B] ' + item['title']
            self.add_flag_to_url(item, flag)
        return items

    def _url(self, url):
        # DirtyFix nefunkcniho downloadu: Neznam kod tak se toho zkusenejsi chopte
        # a prepiste to lepe :)
        if '&authorize=' in url:
            return url
        else:
            return self.base_url + "/" + url.lstrip('./')

    def list_tv_shows_by_letter(self, url):
        util.info("Getting shows by letter " + url)
        shows = self.list_by_letter(url)
        util.info("Resolved shows " + str(shows))
        shows = self.add_directory_flag(shows)
        return self.add_url_flag_to_items(shows, TV_SHOW_FLAG)

    def list_movies_by_letter(self, url):
        movies = self.list_by_letter(url)
        util.info("Resolved movies " + str(movies))
        return self.add_video_flag(movies)

    def resolve(self, item, captcha_cb=None, select_cb=None):
        data = item['url']
        if not data:
            raise ResolveException('Video is not available.')
        result = self.findstreams([STREAMUJ_URL + data])
        if len(result) == 1:
            return result[0]
        elif len(result) > 1 and select_cb:
            return select_cb(result)

    def get_subs(self):
        return self.parent.get_subs()

    def list_search(self, url):
        return self.list_videos(url)
