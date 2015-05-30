# -*- coding: UTF-8 -*-
#/*
# *      Copyright (C) 2013 Libor Zoubek + jondas
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

import os
sys.path.append( os.path.join ( os.path.dirname(__file__),'resources','lib') )

import re
import xbmcaddon
import util,xbmcprovider,xbmcutil,xbmcvfs
from sosac import SosacContentProvider

__scriptid__   = 'plugin.video.sosac.ph'
__scriptname__ = 'sosac.ph'
__addon__      = xbmcaddon.Addon(id=__scriptid__)
__language__   = __addon__.getLocalizedString
__set__        = __addon__.getSetting

settings = {'downloads':__set__('downloads'),'quality':__set__('quality'),'subs':__set__('subs') == 'true'}

reverse_eps = __set__('order-episodes') == '0'

print("URL: ", sys.argv[2])
params = util.params()
if params=={}:
	xbmcutil.init_usage_reporting( __scriptid__)

class XBMCSosac(xbmcprovider.XBMCMultiResolverContentProvider):


    @staticmethod
    def normalize_filename(name):
        return name.replace('/','-').replace('\\','-').replace(':', '-').replace('*', '-').replace('!', '').replace('?', '')


    def run_custom(self, params):
        if 'action' in params.keys():
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
            icon = os.path.join(__addon__.getAddonInfo('path'),'icon.png')
            if params['action'] == 'add-to-library':
                error = False
                arg = {"play": params['url'], 'cp': 'sosac.ph'}
                item_url = util._create_plugin_url(arg)
                if "movie" in params['url']:
                    xbmc.executebuiltin('XBMC.Notification(%s,%s,3000,%s)' % ('Linking',params['name'],icon))
                    item_dir = __set__('library-movies')
                    error = self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), self.normalize_filename(params['name'])) + '.strm', item_url)
                else:
                    xbmc.executebuiltin('XBMC.Notification(%s,%s,100,%s)' % ('Linking',params['name'],icon))
                    item_dir = __set__('library-tvshows')
                    list = self.provider.list_tv_show(params['url'])
                    for itm in list:
                        arg = {"play": itm['url'], 'cp': 'sosac.ph'}
                        item_url = util._create_plugin_url(arg)
                        error |= self.add_item_to_library(os.path.join(item_dir, self.normalize_filename(params['name']), self.normalize_filename(itm['title']) + '.strm'), item_url)
                if error:
                    xbmc.executebuiltin('XBMC.Notification(%s,%s,3000,%s)' % ('Failed, Please check kodi.log','Linking',icon))

                else:
                    xbmc.executebuiltin('XBMC.Notification(%s,%s,3000,%s)' % ('Done','Linking',icon))


    @staticmethod
    def add_item_to_library(item_path, content):
        error = False
        print("path: ", item_path)
        if item_path:
            item_path = os.path.normpath(xbmc.translatePath(item_path))
            if not xbmcvfs.exists(os.path.dirname(item_path)):
                try:
                    xbmcvfs.mkdirs(os.path.dirname(item_path))
                except Exception, e:
                    print('Failed to create directory', item_path)

            try:
                file_desc = xbmcvfs.File(item_path, 'w')
                file_desc.write(content)
                file_desc.close()
            except Exception, e:
                print('Failed to create .strm file: ', item_path, e)
                error = True
        else:
            error = True
            
        return error

print("Running sosac provider with params:", params)
XBMCSosac(SosacContentProvider(reverse_eps=reverse_eps),settings,__addon__).run(params)
