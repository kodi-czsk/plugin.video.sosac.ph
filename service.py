# -*- coding: UTF-8 -*-
#/*
# *      Copyright (C) 2015 BBaronSVK
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

import xbmcaddon
from sosac import SosacContentProvider
from sutils import XBMCSosac

__scriptid__   = 'plugin.video.sosac.ph'
__scriptname__ = 'sosac.ph'
__addon__      = xbmcaddon.Addon(id=__scriptid__)
__language__   = __addon__.getLocalizedString
__set__        = __addon__.getSetting

settings = {'downloads':__set__('downloads'),'quality':__set__('quality'),'subs':__set__('subs') == 'true'}

reverse_eps = __set__('order-episodes') == '0'

XBMCSosac(SosacContentProvider(reverse_eps=reverse_eps),settings,__addon__).service()
