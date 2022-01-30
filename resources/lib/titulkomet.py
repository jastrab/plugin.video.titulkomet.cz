# -*- coding: UTF-8 -*-
# /*
# *      Copyright (C) 2017 BrozikCZ
# *                    2022 Jastrab      
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
# import urllib2
# import cookielib

# try:
#     from urllib2 import Request, urlopen, HTTPError
#     import cookielib
# except:
# from urllib.request import Request, urlopen
# from urllib.error import HTTPError
# import http.cookiejar as cookielib


#Python 2
try: 
    import cookielib
    import urllib2
    import sys
    reload(sys)  # Reload does the trick!
    sys.setdefaultencoding('UTF8')
#Python 3
except:
    import http.cookiejar
    cookielib = http.cookiejar
    urllib2 = urllib.request

# from xml.etree.ElementTree import fromstring
from demjson import demjson

import util
# import resolver
# from provider import ResolveException
# from provider import ContentProvider
from contentprovider.provider import ResolveException
from contentprovider.provider import ContentProvider
import YDStreamExtractor

class TitulkometContentProvider(ContentProvider):
    def __init__(self, username=None, password=None, filter=None,
                 tmp_dir='/tmp'):
        ContentProvider.__init__(self, 'titulkomet.cz',
                                 'http://www.titulkomet.cz',
                                 username, password, filter, tmp_dir)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)

    def capabilities(self):
        return ['categories', 'resolve', 'search']

    def list(self, url):
        if url.find("#related#") == 0:
            return self.list_related(util.request(url[9:]))
        else:
            return self.list_content(util.request(self._url(url)), self._url(url))

    def search(self, keyword):
        return self.list('/?submit=Search&s=' + urllib2.quote(keyword))

    def categories(self):
        result = []
        item = self.dir_item()
        item['type'] = 'new'
        item['url'] = "?orderby=post_date"
        result.append(item)

        data = util.request(self.base_url)
        data = util.substr(data, '<ul id=\"menu-menu-1\" class', '</div>')
        pattern = '<a title=\"(?P<name>[^<]+)\" href=\"(?P<url>[^\"]+)'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            if m.group('url') == '#':
                break
            item = self.dir_item()
            item['title'] = m.group('name')
            item['url'] = m.group('url')
            result.append(item)
        return result

    def list_content(self, page, url=None):
        result = []
        if not url:
            url = self.base_url
        data = util.substr(page, '<main id=\"main', '<div id=\"secondary')
        pattern = '<article id=.+?<a href=\"(?P<url>[^\"]+)\" *title=\"(?P<title>[^\"]+)\".+?<img width=.+? src=\"(?P<img>[^\"]+)\".+?hodnocení: <strong>(?P<rating>[^<]+?)</strong>.+?<p>(?P<plot>.+?)<\/p>.'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['title'] = self.format_title(m)
            item['img'] = m.group('img').strip()
            item['plot'] = self.decode_plot(m)
            item['url'] = m.group('url')
            item['menu'] = {'$30060': {'list': '#related#' + item['url'],
                                       'action-type': 'list'}}
            self._filter(result, item)

        data = util.substr(page, '<ul class=\"easy-wp-page-nav', '</div>')
        n = re.search('<li><a class=\"prev page-numbers\" href=\"(?P<url>[^\"]+)\"', data)
        k = re.search('<li><a class=\"next page-numbers\" href=\"(?P<url>[^\"]+)\"', data)
        if n is not None:
            item = self.dir_item()
            item['type'] = 'prev'
            item['url'] = n.group('url')
            result.append(item)
        if k is not None:
            item = self.dir_item()
            item['type'] = 'next'
            item['url'] = k.group('url')
            result.append(item)
        return result

    def list_related(self, page):
        result = []
        data = util.substr(page,
                           '<div class=\"wp_rp_content\"',
                           '<div class=\"apss-social-share\"')
        pattern = '<li data-position=.+?<a href=\"(?P<url>[^\"]+)\".+?<img src=\"(?P<img>[^\"]+)\".+?class=\"wp_rp_title\">(?P<title>[^\"]+)<\/a>.+?<small class=\"[^\"]+\">(?P<plot>[^<]+?)<\/small>'
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['title'] = m.group('title')
            item['img'] = m.group('img')
            item['url'] = m.group('url')
            item['plot'] = m.group('plot')
            self._filter(result, item)
        return result

    def format_title(self, m):
        return "{0} - {1}%".format(m.group('title'), int(float(m.group('rating').replace(",", ".")) / 5 * 100))

    def decode_plot(self, m):
        p = m.group('plot')
        p = re.sub('<br[^>]*>', '', p)
        p = re.sub('<div[^>]+>', '', p)
        p = re.sub('<table.*', '', p)
        p = re.sub('</span>|<br[^>]*>|<ul>|</ul>|<hr[^>]*>', '', p)
        p = re.sub('<span[^>]*>|<p[^>]*>|<li[^>]*>', '', p)
        p = re.sub('<strong>|<a[^>]*>|<h[\d]+>', '[B]', p)
        p = re.sub('</strong>|</a>|</h[\d]+>', '[/B]', p)
        p = re.sub('</p>|</li>', '[CR]', p)
        p = re.sub('<em>', '[I]', p)
        p = re.sub('</em>', '[/I]', p)
        p = re.sub('<img[^>]+>', '', p)
        p = re.sub('\[B\]Edituj popis\[\/B\]', '', p)
        p = re.sub('\[B\]\[B\]', '[B]', p)
        p = re.sub('\[/B\]\[/B\]', '[/B]', p)
        p = re.sub('\[B\][ ]*\[/B\]', '', p)
        return util.decode_html(''.join(p)).encode('utf-8').strip()

    def resolve(self, item, captcha_cb=None, select_cb=None):
        result = []
        resolved = []
        item = item.copy()
        url = self._url(item['url'])
        self.info('== resolve titulkomet ===>' + url)
        original_yt = False

        


        data = util.substr(util.request(url), 'jQuery( document ).ready(function()', '</script>')

        urls = re.findall('file:[ ]+\"(?P<url>[^\"].+?)\"', data, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        self.info(urls)
        if original_yt:
            url2 = urls[0]
            # e = 'watch?v='
            e = 'youtu.be/'
            edx = url2.find(e)
            video_id = url2[edx+len(e):]

       # video_url = resolver.findstreams([urls[0].replace('https://youtu.be/', 'https://www.youtube.com/watch?v=')])
        vid = YDStreamExtractor.getVideoInfo(url, quality=3) #quality is 0=SD, 1=720p, 2=1080p, 3=Highest Available
        video_url = [vid.streams()[0]]
        subs = urls[1]
        # self.info(video_url)
        
        self.info(subs)
        if video_url and subs:
            for i in video_url:
                i['subs'] = subs
        resolved += video_url[:]

        if not resolved:
            raise ResolveException('Video nenalezeno')

        for i in resolved:
            item = self.video_item()
            try:
                item['title'] = i['title']
            except KeyError:
                pass
            item['url'] = i['xbmc_url']# i['url']
            if original_yt:
                item['url'] = "plugin://plugin.video.youtube/?action=play_video&videoid=" + video_id
                
            #item['quality'] = i['quality']
            #item['surl'] = i['surl']
            item['quality'] = i['ytdl_format']['height']
            item['surl'] = i['ytdl_format']['webpage_url']
            item['subs'] = i['subs']
            item['headers'] = {}#i['headers']
            self.info(item)
            try:
                item['fmt'] = i['fmt']
            except KeyError:
                pass
            result.append(item)
            
        return result

