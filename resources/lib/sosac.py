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

import re
import urllib
import urllib2
import cookielib
import xml.etree.ElementTree as ET
import sys

import util
from provider import ContentProvider, cached, ResolveException

sys.setrecursionlimit(10000)

MOVIES_BASE_URL = "http://movies.prehraj.me"
TV_SHOWS_BASE_URL = "http://tv.prehraj.me"
MOVIES_A_TO_Z_TYPE = "movies-a-z"
MOVIES_GENRE = "filmyxmlzanr.php"
GENRE_PARAM = "zanr"
TV_SHOWS_A_TO_Z_TYPE = "tv-shows-a-z"
XML_LETTER = "xmlpismeno"
TV_SHOW_FLAG = "#tvshow#"
ISO_639_1_CZECH = "cs"
MOST_POPULAR_TYPE = "most-popular"
RECENTLY_ADDED_TYPE = "recently-added"
SEARCH_TYPE = "search"


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
            ("Movies", MOVIES_BASE_URL),
            ("TV Shows", TV_SHOWS_BASE_URL),
            ("Movies - by Genres", MOVIES_BASE_URL + "/" + MOVIES_GENRE),
            ("Movies - Most popular",
             MOVIES_BASE_URL + "/" + self.ISO_639_1_CZECH + MOST_POPULAR_TYPE),
            ("TV Shows - Most popular",
             TV_SHOWS_BASE_URL + "/" + self.ISO_639_1_CZECH + MOST_POPULAR_TYPE),
            ("Movies - Recently added",
             MOVIES_BASE_URL + "/" + self.ISO_639_1_CZECH + RECENTLY_ADDED_TYPE),
            ("TV Shows - Recently added",
             TV_SHOWS_BASE_URL + "/" + self.ISO_639_1_CZECH + RECENTLY_ADDED_TYPE)]:
            item = self.dir_item(title=title, url=url)
            if title == 'Movies' or title == 'TV Shows' or title == 'Movies - Recently added':
                item['menu'] = {"[B][COLOR red]Add all to library[/COLOR][/B]": {
                    'action': 'add-all-to-library', 'title': title}}
            result.append(item)
        return result

    def search(self, keyword):
        return self.list_search('%s/%ssearch?%s' % (MOVIES_BASE_URL, self.ISO_639_1_CZECH,
                                                    urllib.urlencode({'q': keyword})))

    def a_to_z(self, url_type):
        result = []
        for letter in ['0-9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'e', 'h', 'i', 'j', 'k', 'l', 'm',
                       'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
            item = self.dir_item(title=letter.upper())
            if url_type == MOVIES_A_TO_Z_TYPE:
                item['url'] = self.base_url + "/filmyxmlpismeno.php?pismeno=" + letter
            else:
                item['url'] = self.base_url + "/" + self.ISO_639_1_CZECH + url_type + "/" + letter
            result.append(item)
        return result

    @staticmethod
    def remove_flag_from_url(url, flag):
        return url.replace(flag, "", count=1)

    @staticmethod
    def is_xml_letter(url):
        if XML_LETTER in url:
            return True
        return False

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
    def is_search(url):
        return SEARCH_TYPE in url

    @staticmethod
    def particular_letter(url):
        return "a-z/" in url

    def has_tv_show_flag(self, url):
        return TV_SHOW_FLAG in url

    def remove_flags(self, url):
        return url.replace(TV_SHOW_FLAG, "", 1)

    def list(self, url):
        util.info("Examining url " + url)
        if MOVIES_GENRE in url:
            return self.list_by_genres(url)
        if self.is_most_popular(url):
            if "movie" in url:
                return self.list_movies_by_letter(url)
            if "tv" in url:
                return self.list_tv_shows_by_letter(url)
        if self.is_recently_added(url):
            util.debug("is recently added")
            if "movie" in url:
                return self.list_movie_recently_added(url)
            if "tv" in url:
                util.debug("is TV")
                return self.list_tv_recently_added(url)
        if self.is_search(url):
            return self.list_search(url)
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

        if self.is_xml_letter(url):
            util.debug("xml letter")
            if "movie" in url:
                return self.list_xml_letter(url)

        return [self.dir_item(title="I failed", url="fail")]

    def list_by_genres(self, url):
        if "?" + GENRE_PARAM in url:
            return self.list_xml_letter(url)
        else:
            result = []
            page = util.request(url)
            data = util.substr(page, '<select name=\"zanr\">', '</select')
            for s in re.finditer('<option value=\"([^\"]+)\">([^<]+)</option>', data,
                                 re.IGNORECASE | re.DOTALL):
                item = {'url': url + "?" + GENRE_PARAM + "=" +
                        s.group(1), 'title': s.group(2), 'type': 'dir'}
                self._filter(result, item)
            return result

    def list_xml_letter(self, url):
        result = []
        data = util.request(url)
        tree = ET.fromstring(data)
        for film in tree.findall('film'):
            item = self.video_item()
            try:
                if ISO_639_1_CZECH in self.ISO_639_1_CZECH:
                    title = film.findtext('nazevcs').encode('utf-8')
                else:
                    title = film.findtext('nazeven').encode('utf-8')
                basetitle = '%s (%s)' % (title, film.findtext('rokvydani'))
                item['title'] = '%s - %s' % (basetitle, film.findtext('kvalita').upper())
                item['name'] = item['title']
                item['img'] = film.findtext('obrazekmaly')
                item['url'] = self.base_url + '/player/' + self.parent.make_name(
                    film.findtext('nazeven').encode('utf-8') + '-' + film.findtext('rokvydani'))
                item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                    'url': item['url'], 'action': 'add-to-library', 'name': basetitle}}
                self._filter(result, item)
            except Exception, e:
                util.error("ERR TITLE: " + item['title'] + " | " + str(e))
                pass
        util.debug(result)
        return result

    def list_tv_show(self, url):
        result = []
        page = util.request(url)
        data = util.substr(page, '<div class=\"content\">', '<script')
        for s in re.finditer('<strong.+?</ul>', data, re.IGNORECASE | re.DOTALL):
            serie = s.group(0)
            serie_name = re.search('<strong>([^<]+)', serie).group(1)
            for e in re.finditer('<li.+?</li>', serie, re.IGNORECASE | re.DOTALL):
                episode = e.group(0)
                item = self.video_item()
                ep_name = re.search('<a href=\"#[^<]+<span>(?P<id>[^<]+)</span>(?P<name>[^<]+)',
                                    episode)
                if ep_name:
                    item['title'] = '%s %s %s' % (
                        serie_name, ep_name.group('id'), ep_name.group('name'))
                    item['epname'] = ep_name.group('name')
                    item['ep'] = ep_name
                i = re.search('<div class=\"inner-item[^<]+<img src=\"(?P<img>[^\"]+).+?<a href=\"'
                              '(?P<url>[^\"]+)', episode, re.IGNORECASE | re.DOTALL)
                if i:
                    item['img'] = self._url(i.group('img'))
                    item['url'] = i.group('url')
                if i and ep_name:
                    self._filter(result, item)
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
    def get_data_cached(self, url):
        return util.request(url)

    def list_by_letter(self, url):
        result = []
        page = self.get_data_cached(url)
        data = util.substr(page, '<ul class=\"content', '</ul>')
        subs = self.get_subs()
        for m in re.finditer('<a class=\"title\" href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)', data,
                             re.IGNORECASE | re.DOTALL):
            item = {'url': m.group('url'), 'title': m.group('name')}
            if item['url'] in subs:
                item['menu'] = {"[B][COLOR red]Remove from subscription[/COLOR][/B]": {
                    'url': m.group('url'), 'action': 'remove-subscription', 'name': m.group('name')}
                }
            else:
                item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                    'url': m.group('url'), 'action': 'add-to-library', 'name': m.group('name')}}
            self._filter(result, item)
        paging = util.substr(page, '<div class=\"pagination\"', '</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page=(?P<page>\d+)', paging,
                         re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page=(?P<page>\d)', url)
            current_page = 0
            if self.is_most_popular(url) and next_page > 10:
                return result
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$', '', url) + '?page=' + str(next_page)
                result += self.list_by_letter(url)
        return result

    def list_tv_recently_added(self, url):
        result = []
        page = self.get_data_cached(url)
        data = util.substr(page, '<div class=\"content\"', '</ul>')
        subs = self.get_subs()
        for m in re.finditer('<a href=\"(?P<url>[^\"]+)[^>]+((?!<strong).)*<strong>S(?P<serie>\d+) '
                             '/ E(?P<epizoda>\d+)</strong>((?!<a href).)*<a href=\"(?P<surl>[^\"]+)'
                             '[^>]+class=\"mini\">((?!<span>).)*<span>\((?P<name>[^)]+)\)<',
                             data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['url'] = m.group('url')
            item['title'] = "Rada " + m.group('serie') + " Epizoda " + m.group(
                'epizoda') + " - " + m.group('name')
            if item['url'] in subs:
                item['menu'] = {"[B][COLOR red]Remove from subscription[/COLOR][/B]": {
                    'url': m.group('url'), 'action': 'remove-subscription',
                    'name': m.group('name') + " S" + m.group('serie') + 'E' + m.group('epizoda')}}
            else:
                item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                    'url': m.group('url'), 'action': 'add-to-library',
                    'name': m.group('name') + " S" + m.group('serie') + 'E' + m.group('epizoda')}}
            self._filter(result, item)
        paging = util.substr(page, '<div class=\"pagination\"', '</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page_1=(?P<page>\d+)', paging,
                         re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page_1=(?P<page>\d)', url)
            current_page = 0
            if next_page > 30:
                return result
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$', '', url) + '?page_1=' + str(next_page)
                result += self.list_tv_recently_added(url)
        return result

    def library_movies_all_xml(self):
        page = util.request('http://tv.prehraj.me/filmyxml.php')
        pagedata = util.substr(page, '<select name=\"rok\">', '</select>')
        pageitems = re.finditer('<option value=\"(?P<url>[^\"]+)\">(?P<name>[^<]+)</option>',
                                pagedata, re.IGNORECASE | re.DOTALL)
        pagetotal = float(len(list(pageitems)))
        pageitems = re.finditer('<option value=\"(?P<url>[^\"]+)\">(?P<name>[^<]+)</option>',
                                pagedata, re.IGNORECASE | re.DOTALL)
        util.info("PocetRoku: %d" % pagetotal)
        pagenum = 0
        for m in pageitems:
            pagenum += 1
            if self.parent.dialog.iscanceled():
                return
            pageperc = float(pagenum / pagetotal) * 100
            util.info("Rokpercento: %d" % int(pageperc))
            data = util.request('http://tv.prehraj.me/filmyxml.php?rok=' +
                                m.group('url') + '&sirka=670&vyska=377&affid=0#')
            tree = ET.fromstring(data)
            total = float(len(list(tree.findall('film'))))
            util.info("TOTAL: %d" % total)
            num = 0
            for film in tree.findall('film'):
                num += 1
                perc = float(num / total) * 100
                util.info("percento: %d" % int(perc))
                if self.parent.dialog.iscanceled():
                    return
                item = self.video_item()
                try:
                    if ISO_639_1_CZECH in self.ISO_639_1_CZECH:
                        title = film.findtext('nazevcs').encode('utf-8')
                    else:
                        title = film.findtext('nazeven').encode('utf-8')
                    self.parent.dialog.update(int(perc), str(pagenum) + '/' + str(int(pagetotal)) +
                                              ' [' + m.group('url') + '] ->  ' + title)
                    item['title'] = '%s (%s)' % (title, film.findtext('rokvydani'))
                    item['name'] = item['title']
                    item['url'] = 'http://movies.prehraj.me/' + self.ISO_639_1_CZECH + \
                        'player/' + self.parent.make_name(title + '-' + film.findtext('rokvydani'))
                    item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                        'url': item['url'], 'action': 'add-to-library', 'name': item['title']}}
                    item['update'] = True
                    item['notify'] = False
                    self.parent.add_item(item)
                except Exception, e:
                    util.error("ERR TITLE: " + item['title'] + " | " + str(e))
                    pass
#        self.parent.dialog.close()

    def library_movie_recently_added_xml(self):
        data = util.request(
            'http://tv.prehraj.me/filmyxml2.php?limit=200&sirka=670&vyska=377&affid=0#')
        tree = ET.fromstring(data)
        total = float(len(list(tree.findall('film'))))
        util.info("TOTAL: %d" % total)
        num = 0
        for film in tree.findall('film'):
            num += 1
            perc = float(num / total) * 100
            util.info("percento: %d" % int(perc))
            if self.parent.dialog.iscanceled():
                return
            self.parent.dialog.update(int(perc), film.findtext('nazevcs') + ' (' +
                                      film.findtext('rokvydani') + ')\n' +
                                      film.findtext('nazeven') + ' (' +
                                      film.findtext('rokvydani') + ')\n\n\n')
            item = self.video_item()
            try:
                if ISO_639_1_CZECH in self.ISO_639_1_CZECH:
                    title = film.findtext('nazevcs').encode('utf-8')
                else:
                    title = film.findtext('nazeven').encode('utf-8')
                item['title'] = '%s (%s)' % (title, film.findtext('rokvydani'))
                item['name'] = item['title']
                item['url'] = 'http://movies.prehraj.me/' + self.ISO_639_1_CZECH + \
                    'player/' + self.parent.make_name(title + '-' + film.findtext('rokvydani'))
                item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                    'url': item['url'], 'action': 'add-to-library', 'name': item['title']}}
                item['update'] = True
                item['notify'] = False
                self.parent.add_item(item)
                # print("TITLE: ", item['title'])
            except Exception, e:
                util.error("ERR TITLE: " + item['title'] + " | " + str(e))
                pass
#        self.parent.dialog.close()

    def library_tvshows_all_xml(self):
        page = util.request('http://tv.prehraj.me/serialyxml.php')
        data = util.substr(page, '<select name=\"serialy\">', '</select>')
        items = re.finditer('<option value=\"(?P<url>[^\"]+)\">(?P<name>[^<]+)</option>', data,
                            re.IGNORECASE | re.DOTALL)
        total = float(len(list(items)))
        items = re.finditer('<option value=\"(?P<url>[^\"]+)\">(?P<name>[^<]+)</option>', data,
                            re.IGNORECASE | re.DOTALL)
        util.info("Pocet: %d" % total)
        num = 0
        for m in items:
            num += 1
            if self.parent.dialog.iscanceled():
                return
            perc = float(num / total) * 100
            util.info("percento: %d" % int(perc))
            self.parent.dialog.update(int(perc), m.group('name'))
            item = {'url': 'http://tv.prehraj.me/cs/detail/' + m.group('url'),
                    'action': 'add-to-library', 'name': m.group('name'), 'update': True,
                    'notify': True}
            self.parent.add_item(item)

        util.info("done....")

    def list_movie_recently_added(self, url):
        result = []
        page = self.get_data_cached(url)
        data = util.substr(page, '<div class=\"content\"', '</ul>')
        for m in re.finditer(
                '<a class=\"content-block\" href=\"(?P<url>[^\"]+)\" title=\"(?P<name>[^\"]+)',
                data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['url'] = m.group('url')
            item['title'] = m.group('name')
            item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                'url': m.group('url'), 'action': 'add-to-library', 'name': m.group('name')}}
            self._filter(result, item)
        paging = util.substr(page, '<div class=\"pagination\"', '</div')
        next = re.search('<li class=\"next[^<]+<a href=\"\?page=(?P<page>\d+)', paging,
                         re.IGNORECASE | re.DOTALL)
        if next:
            next_page = int(next.group('page'))
            current = re.search('\?page=(?P<page>\d)', url)
            current_page = 0
            if next_page > 5:
                return result
            if current:
                current_page = int(current.group('page'))
            if current_page < next_page:
                url = re.sub('\?.+?$', '', url) + '?page=' + str(next_page)
                result += self.list_movie_recently_added(url)
        return result

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
        page = util.request(item['url'])
        data = util.substr(page, '<div class=\"bottom-player\"', 'div>')
        if data.find('<iframe') < 0:
            raise ResolveException('Video is not available.')
        result = self.findstreams(data, ['<iframe src=\"(?P<url>[^\"]+)'])
        if len(result) == 1:
            return result[0]
        elif len(result) > 1 and select_cb:
            return select_cb(result)

    def get_subs(self):
        return self.parent.get_subs()

    def list_search(self, url):
        result = []
        html_tree = util.parse_html(url)
        for entry in html_tree.select('ul.content li'):
            item = self.video_item()
            entry.p.strong.extract()
            item['url'] = entry.h4.a.get('href')
            item['title'] = entry.h4.a.text
            item['img'] = MOVIES_BASE_URL + entry.img.get('src')
            item['plot'] = entry.p.text.strip()
            item['menu'] = {"[B][COLOR red]Add to library[/COLOR][/B]": {
                'url': item['url'], 'action': 'add-to-library', 'name': item['title']}}
            self._filter(result, item)
        # Process next 4 pages, so we'll get 20 items per page instead of 4
        for next_page in html_tree.select('.pagination ul li.next a'):
            next_url = '%s/%ssearch%s' % (MOVIES_BASE_URL, self.ISO_639_1_CZECH,
                                          next_page.get('href'))
            page_number = 1
            page = re.search(r'\bpage=(\d+)', url)
            if page:
                page_number = int(page.group(1))
            next_page_number = 1
            page = re.search(r'\bpage=(\d+)', next_url)
            if page:
                next_page_number = int(page.group(1))
            if page_number > next_page_number:
                break
            if page_number % 5 != 0:
                result += self.list_search(next_url)
            else:
                item = self.dir_item()
                item['type'] = 'next'
                item['url'] = next_url
                result.append(item)
            break
        return result
