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

import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import hashlib
import sys
import json
import datetime
import re

import util
from provider import ContentProvider, cached, ResolveException

sys.setrecursionlimit(10000)

MOVIES_BASE_URL = "http://movies.prehraj.me"
TV_SHOW_FLAG = "#tvshow#"
ISO_639_1_CZECH = "cs"
ALPHA_SORT = '1'
YEAR_SORT = '2'

# JSONs
URL = "http://tv.sosac.to"
J_MOVIES_A_TO_Z_TYPE = "/vystupy5981/souboryaz.json"
J_MOVIES_GENRE = "/vystupy5981/souboryzanry.json"
J_MOVIES_MOST_POPULAR = "/vystupy5981/moviesmostpopular.json"
J_MOVIES_RECENTLY_ADDED = "/vystupy5981/moviesrecentlyadded.json"
# hack missing json with a-z series
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
IMAGE_DUBBING = "http://movies.sosac.tv/web-icons/sounds/"

FILTER_URL_PARAM = "?filter"
DUBBING_URL_PARAM = "?dub="
DUBBING_REGEX = r"\?dub=(\w\w)"
DUBBING_SETTINGS = [
    ["cs", "CZECH"],
    ["en", "ENGLISH"],
    ["sk", "SLOVAK"],
    ["cn", "CHINES"],
    ["de", "GERMAN"],
    ["el", "GREEK"],
    ["es", "SPANISH"],
    ["fi", "FINNISH"],
    ["fr", "FRENCH"],
    ["hr", "CROATIAN"],
    ["id", "INDONESIAN"],
    ["it", "ITALIAN"],
    ["ja", "JAPANES"],
    ["ko", "KOREAN"],
    ["nl", "DUTCH"],
    ["no", "NORWEGIAN"],
    ["pl", "POLISH"],
    ["pt", "PORTUGUESE"],
    ["ru", "RUSSIAN"],
    ["tr", "TURKISH"],
    ["vi", "VIETNAMESE"]
]

LIBRARY_MENU_ITEM_ADD = "[B][COLOR red]Add to library[/COLOR][/B]"
LIBRARY_MENU_ITEM_ADD_ALL = "[B][COLOR red]Add all to library[/COLOR][/B]"
LIBRARY_MENU_ITEM_REMOVE = "[B][COLOR red]Remove from subscription[/COLOR][/B]"
LIBRARY_MENU_ITEM_REMOVE_ALL = "[B][COLOR red]Remove all subscriptions[/COLOR][/B]"
LIBRARY_TYPE_VIDEO = "video"
LIBRARY_TYPE_TVSHOW = "tvshow"
LIBRARY_TYPE_ALL_VIDEOS = "all-videos"
LIBRARY_TYPE_RECENT_VIDEOS = "recent-videos"
LIBRARY_TYPE_ALL_SHOWS = "all-shows"
LIBRARY_ACTION_ADD = "add-to-library"
LIBRARY_ACTION_ADD_ALL = "add-all-to-library"
LIBRARY_ACTION_REMOVE_ALL = "remove-all-from-library"
LIBRARY_ACTION_REMOVE_SUBSCRIPTION = "remove-subscription"
LIBRARY_FLAG_IS_PRESENT = "[B][COLOR yellow]*[/COLOR][/B] "

RATING = 'r'
LANG = 'd'
QUALITY = 'q'
IMDB = 'm'
CSFD = 'c'
DESCRIPTION = 'p'
GENRE = 'g'

RATING_STEP = 2


class SosacContentProvider(ContentProvider):
    ISO_639_1_CZECH = None
    par = None

    def __init__(self, username=None, password=None, filter=None, reverse_eps=False,
                 force_czech=False, order_recently_by=0):
        ContentProvider.__init__(self, name='sosac.ph', base_url=MOVIES_BASE_URL, username=username,
                                 password=password, filter=filter)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.LWPCookieJar()))
        urllib.request.install_opener(opener)
        self.reverse_eps = reverse_eps
        self.force_czech = force_czech
        self.streamujtv_user = None
        self.streamujtv_pass = None
        self.streamujtv_location = None
        self.order_recently_by = order_recently_by

    def on_init(self):
        kodilang = self.lang or 'cs'
        if kodilang == ISO_639_1_CZECH or kodilang == 'sk' or self.force_czech:
            self.ISO_639_1_CZECH = ISO_639_1_CZECH
        else:
            self.ISO_639_1_CZECH = 'en'

    def capabilities(self):
        return ['resolve', 'categories', 'search']

    def categories(self):
        result = []
        item = self.dir_item(title="Movies", url=URL + J_MOVIES_A_TO_Z_TYPE)
        item['menu'] = {
            LIBRARY_MENU_ITEM_ADD_ALL: {
                'action': LIBRARY_ACTION_ADD_ALL,
                'type': LIBRARY_TYPE_ALL_VIDEOS
            }
        }
        result.append(item)

        item = self.dir_item(title="TV Shows", url=URL +
                             J_TV_SHOWS_A_TO_Z_TYPE)
        item['menu'] = {
            LIBRARY_MENU_ITEM_ADD_ALL: {
                'action': LIBRARY_ACTION_ADD_ALL,
                'type': LIBRARY_TYPE_ALL_SHOWS
            }
        }
        result.append(item)

        item = self.dir_item(title="Movies - by Genres", url=URL +
                             J_MOVIES_GENRE)
        result.append(item)

        item = self.dir_item(title="Movies - Most popular", url=URL +
                             J_MOVIES_MOST_POPULAR)
        result.append(item)

        item = self.dir_item(title="TV Shows - Most popular", url=URL +
                             J_TV_SHOWS_MOST_POPULAR)
        result.append(item)

        item = self.item_with_last_mod("Movies - Recently added", URL + J_MOVIES_RECENTLY_ADDED)
        item['menu'] = {
            LIBRARY_MENU_ITEM_ADD_ALL: {
                'action': LIBRARY_ACTION_ADD_ALL,
                'type': LIBRARY_TYPE_RECENT_VIDEOS
            }
        }
        result.append(item)

        for item in result:
            if 'menu' not in item:
                item['menu'] = {}
            item['menu'][LIBRARY_MENU_ITEM_REMOVE_ALL] = {
                'action': LIBRARY_ACTION_REMOVE_ALL
            }

        item = self.item_with_last_mod("TV Shows - Recently added", URL + J_TV_SHOWS_RECENTLY_ADDED)
        result.append(item)

        return result

    def search(self, keyword):
        if len(keyword) < 3 or len(keyword) > 100:
            return [self.dir_item(title="Search query must be between 3 and 100 characters long!",
                                  url="fail")]
        return self.list_videos(URL + J_SEARCH + urllib.parse.quote_plus(keyword))

    def a_to_z(self, url):
        result = []
        for letter in ['0-9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                       'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
            item = self.dir_item(title=letter.upper())
            item['url'] = URL + url + letter + ".json"
            result.append(item)
        return result

    @staticmethod
    def particular_letter(url):
        return "a-z/" in url

    def has_tv_show_flag(self, url):
        return TV_SHOW_FLAG in url

    def list(self, url, filter=None):
        util.info("Examining url " + url)

        list_result = None
        if FILTER_URL_PARAM in url:
            list_result = self.list_movies_by_dubbing(url)
        elif not filter and DUBBING_URL_PARAM in url:
            list_result = self.list_dubbing(url)
        elif J_MOVIES_A_TO_Z_TYPE in url or J_MOVIES_GENRE in url:
            list_result = self.load_json_list(url)
        elif J_SERIES in url:
            list_result = self.list_episodes(url)
        elif J_TV_SHOWS in url or J_TV_SHOWS_MOST_POPULAR in url:
            list_result = self.list_series_letter(url)
        elif J_TV_SHOWS_RECENTLY_ADDED in url:
            list_result = self.list_recentlyadded_episodes(url)
        elif J_TV_SHOWS_A_TO_Z_TYPE in url:
            list_result = self.a_to_z(J_TV_SHOWS)
        else:
            order_by = None
            if J_MOVIES_RECENTLY_ADDED in url:
                order_by = self.order_recently_by
            list_result = self.list_videos(url, filter, order_by)
        return list_result

    def list_dubbing(self, url):
        p = re.compile(DUBBING_REGEX)
        m = p.search(url)
        dub = m.group(1)
        url_without_dub = url[:m.start()]

        filter = self.has_video_dub(dub)
        return self.list(url_without_dub, filter)

    def load_json_list(self, url):
        result = []
        data = util.request(url)
        json_list = json.loads(data)
        for key, value in json_list.items():
            item = self.dir_item(title=key.title())
            item['url'] = value
            result.append(item)

        return sorted(result, key=lambda i: i['title'])

    def list_videos(self, url, filter=None, order_by=0, library=False):
        result = []
        data = util.request(url)
        json_video_array = json.loads(data)
        for video in json_video_array:
            if not filter or filter(video):
                item = self.video_item()
                item['title'] = self.get_video_name(video)
                item['img'] = IMAGE_MOVIE + video['i']
                item['url'] = video['l'] if video['l'] and video['l'] is not None else ""
                item['year'] = int(video['y'])
                if RATING in video:
                    item['rating'] = video[RATING] * RATING_STEP
                if LANG in video:
                    item['lang'] = video[LANG]
                if QUALITY in video and video[QUALITY] is not None:
                    item['quality'] = video[QUALITY]
                if GENRE in video:
                    item['plot'] = ' '.join(video[GENRE])
                item['menu'] = {
                    LIBRARY_MENU_ITEM_ADD: {
                        'url': item['url'],
                        'type': LIBRARY_TYPE_VIDEO,
                        'action': LIBRARY_ACTION_ADD,
                        'name': self.get_library_video_name(video)
                    }
                }
                if CSFD in video and video[CSFD] is not None:
                    item['menu'][LIBRARY_MENU_ITEM_ADD]['csfd'] = video[CSFD]
                if IMDB in video and video[IMDB] is not None:
                    item['menu'][LIBRARY_MENU_ITEM_ADD]['imdb'] = video[IMDB]
                result.append(item)
        util.debug("ORDER BY" + str(order_by))
        if order_by == ALPHA_SORT:
            result = sorted(result, key=lambda i: i['title'])
        elif order_by == YEAR_SORT:
            result = sorted(result, key=lambda i: i['year'], reverse=True)
        if not filter and not library:
            result.insert(0, self.dir_item(title="Filter", url=url + FILTER_URL_PARAM))
        return result

    def list_series_letter(self, url, load_subs=True):
        result = []
        data = util.request(url)
        json_list = json.loads(data)
        subs = self.get_subscriptions() if load_subs else {}
        for serial in json_list:
            item = self.dir_item()
            item['title'] = self.get_localized_name(serial['n'])
            item['img'] = IMAGE_SERIES + serial['i']
            item['url'] = serial['l']
            item['year'] = int(serial['y'])
            if DESCRIPTION in serial:
                item['plot'] = serial[DESCRIPTION].encode('utf-8')
            if RATING in serial:
                item['rating'] = serial[RATING] * RATING_STEP
            if item['url'] in subs:
                item['title'] = LIBRARY_FLAG_IS_PRESENT + item['title']
                item['menu'] = {
                    LIBRARY_MENU_ITEM_REMOVE: {
                        'url': item['url'],
                        'action': LIBRARY_ACTION_REMOVE_SUBSCRIPTION,
                        'name': self.get_library_video_name(serial)
                    }
                }
            else:
                item['menu'] = {
                    LIBRARY_MENU_ITEM_ADD: {
                        'url': item['url'],
                        'type': LIBRARY_TYPE_TVSHOW,
                        'action': LIBRARY_ACTION_ADD,
                        'name': self.get_library_video_name(serial)
                    }
                }
                if CSFD in serial and serial[CSFD] is not None:
                    item['menu'][LIBRARY_MENU_ITEM_ADD]['csfd'] = serial[CSFD]
                if IMDB in serial and serial[IMDB] is not None:
                    item['menu'][LIBRARY_MENU_ITEM_ADD]['imdb'] = serial[IMDB]
            result.append(item)
        return result

    def list_movies_by_dubbing(self, url):
        url_without_filter = url[:-len(FILTER_URL_PARAM)]

        result = []
        for i in DUBBING_SETTINGS:
            item = self.dir_item(title=i[1], url=url_without_filter + DUBBING_URL_PARAM + i[0])
            item['img'] = IMAGE_DUBBING + i[0] + ".png"
            result.append(item)
        return result

    def list_episodes(self, url):
        result = []
        data = util.request(url)
        json_series = json.loads(data)
        for series in json_series:
            for series_key, episode in series.items():
                for episode_key, video in episode.items():
                    item = self.video_item()
                    item['title'] = (series_key.zfill(2) + "x" + episode_key.zfill(2) +
                                     " - " + video['n'])
                    item['season'] = int(series_key)
                    item['episode'] = int(episode_key)
                    if video['i'] is not None:
                        item['img'] = IMAGE_EPISODE + video['i']
                    item['url'] = video['l'] if video['l'] else ""
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
            item['title'] = self.get_episode_recently_name(episode)
            item['season'] = int(episode['s'])
            item['episode'] = int(episode['e'])
            item['img'] = IMAGE_EPISODE + episode['i']
            item['url'] = episode['l']
            result.append(item)
        return result

    def library_list_all_videos(self, filter=None):
        letters = self.load_json_list(URL + J_MOVIES_A_TO_Z_TYPE)
        total = len(letters)

        step = int(100 / total)
        for idx, letter in enumerate(letters):
            for video in self.list_videos(letter['url'], filter=filter, library=True):
                yield video
            yield {'progress': step * (idx + 1)}

    def library_list_recent_videos(self, filter=None):
        videos = self.list_videos(URL + J_MOVIES_RECENTLY_ADDED, filter, library=True)
        total = len(videos)

        step = int(100 / total)
        for idx, video in enumerate(videos):
            yield video
            yield {'progress': step * (idx + 1)}

    def library_list_all_tvshows(self):
        letters = self.a_to_z(J_TV_SHOWS)
        total = len(letters)

        step = int(100 / total)
        for idx, letter in enumerate(letters):
            for video in self.list_series_letter(letter['url'], False):
                yield video
            yield {'progress': step * (idx + 1)}

    def get_video_name(self, video):
        name = self.get_localized_name(video['n'])
        year = (" (" + video['y'] + ")") if video['y'] else " "
        quality = (" - " + video[QUALITY].upper()) if video[QUALITY] else ""
        return name + year + quality

    def get_library_video_name(self, video):
        name = self.get_localized_name(video['n'])
        year = (" (" + video['y'] + ")") if video['y'] else " "
        return (name + year).encode('utf-8')

    def get_episode_recently_name(self, episode):
        serial = self.get_localized_name(episode['t']) + ': '
        series = episode['s'].zfill(2) + "x"
        number = episode['e'].zfill(2) + " - "
        name = self.get_localized_name(episode['n'])
        return serial + series + number + name

    def get_localized_name(self, names):
        if self.ISO_639_1_CZECH in names:
            return names[self.ISO_639_1_CZECH]
        return names[ISO_639_1_CZECH]

    def resolve(self, item, captcha_cb=None, select_cb=None):
        data = item['url']
        if not data:
            raise ResolveException('Video is not available.')
        result = self.findstreams([STREAMUJ_URL + data])
        stream = None
        if len(result) == 1:
            stream = result[0]
        elif len(result) > 1 and select_cb:
            stream = select_cb(result)
            if not stream:
                return None
        return self.probe_html5(self.set_streamujtv_info(stream))

    def probe_html5(self, result):

        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):

            def http_error_302(self, req, fp, code, msg, headers):
                infourl = urllib.response.addinfourl(fp, headers, req.get_full_url())
                infourl.status = code
                infourl.code = code
                return infourl
            http_error_300 = http_error_302
            http_error_301 = http_error_302
            http_error_303 = http_error_302
            http_error_307 = http_error_302

        opener = urllib.request.build_opener(NoRedirectHandler())
        urllib.request.install_opener(opener)

        r = urllib.request.urlopen(urllib.request.Request(result['url'], headers=result['headers']))
        if r.code == 200:
            result['url'] = r.read()
        return result

    def set_streamujtv_info(self, stream):
        if stream:
            if len(self.streamujtv_user) > 0 and len(self.streamujtv_pass) > 0:
                # set streamujtv credentials
                m = hashlib.md5()
                m.update(self.streamujtv_pass)
                h = m.hexdigest()
                m = hashlib.md5()
                m.update(h)
                stream['url'] = stream['url'] + \
                    "&pass=%s:::%s" % (self.streamujtv_user, m.hexdigest())
            if self.streamujtv_location in ['1', '2']:
                stream['url'] = stream['url'] + "&location=%s" % self.streamujtv_location
        return stream

    def get_subscriptions(self):
        return self.parent.get_subs()

    def request_last_update(self, url):
        util.debug('request: %s' % url)
        lastmod = None
        req = urllib.request.Request(url)
        req.add_header('User-Agent', util.UA)
        try:
            response = urllib.request.urlopen(req)
            lastmod = datetime.datetime(*response.info().getdate('Last-Modified')[:6]).strftime(
                '%d.%m.%Y')
            response.close()
        except urllib.error.HTTPError as error:
            util.debug(error.read())
            error.close()
        return lastmod

    def item_with_last_mod(self, title, url):
        lastmod = self.request_last_update(url)
        if lastmod:
            title += " (" + lastmod + ")"
        item = self.dir_item(title=title, url=url)
        return item

    def has_video_dub(self, dubbing):
        return lambda v: LANG in v and dubbing in v[LANG]
