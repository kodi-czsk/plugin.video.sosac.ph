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

import re,os,urllib,urllib2,cookielib
import util

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
class SosacContentProvider(ContentProvider):

    def __init__(self,username=None,password=None,filter=None,reverse_eps=False):
        ContentProvider.__init__(self,name='sosac.ph', username=username,password=password,filter=filter)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)
        self.reverse_eps = reverse_eps

    def capabilities(self):
        return ['resolve','categories']

    def categories(self):
        result = []
        for title, url in [("Movies", MOVIES_BASE_URL), ("TV Shows", TV_SHOWS_BASE_URL)]:
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
            item['url'] = self.base_url + "/" + ISO_639_1_CZECH +  "/" + url_type + "/" + letter
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
    def particular_letter(url):
        return "a-z" in url

    def has_tv_show_flag(self, url):
        return TV_SHOW_FLAG in url

    def remove_flags(self, url):
        return url.replace(TV_SHOW_FLAG, "", 1)

    def list(self,url):
        print("Examining url", url)
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
            self._filter(result,item)
        paging = util.substr(page,'<div class=\"pagination\"','</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page=(?P<page>\d+)',paging,re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page=(?P<page>\d)',url)
            current_page = 0
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$','',url) + '?page='+str(next_page)
                result += self.list_by_letter(url)
        return result

    def add_flag_to_url(self, item, flag):
        item['url'] = flag + item['url']
        return item

    def add_url_flag_to_items(self, items, flag):
        for item in items:
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
