#!usr/bin/Python
# -*- coding:utf-8 -*-
"""为了应付时不时出现的Too many redirects异常，使用此类打开链接。
此类会自动处理redirect和cookie，同时增加了失败自动重试功能"""
import urllib, urllib2, Cookie, urlparse
from google.appengine.api import urlfetch
from config import CONNECTION_TIMEOUT

class URLOpener:
    def __init__(self, host=None, maxfetchcount=2, maxredirect=3, 
                timeout=CONNECTION_TIMEOUT, addreferer=False):
        self.cookie = Cookie.SimpleCookie()
        self.maxFetchCount = maxfetchcount
        self.maxRedirect = maxredirect
        self.host = host
        self.addReferer = addreferer
        self.timeout = timeout
    
    def open(self, url, data=None):
        method = urlfetch.GET if data is None else urlfetch.POST
        
        maxRedirect = self.maxRedirect
        class resp: #出现异常时response不是合法的对象，使用一个模拟的
            status_code=555
            content=None
            headers={}
        
        response = resp()
        while url and (maxRedirect > 0):
            for cnt in range(self.maxFetchCount):
                try:
                    response = urlfetch.fetch(url=url, payload=data, method=method,
                        headers=self._getHeaders(self.cookie,url),
                        allow_truncated=False, follow_redirects=False, deadline=self.timeout)
                except urlfetch.DeadlineExceededError:
                    if response.status_code == 555:
                        response.status_code = 504
                    continue
                except urlfetch.ResponseTooLargeError:
                    if response.status_code == 555:
                        response.status_code = 509
                    break
                except urlfetch.DownloadError:
                    if response.status_code == 555:
                        response.status_code = 450
                    continue
                except urlfetch.Error:
                    if response.status_code == 555:
                        response.status_code = 451
                    break
                else:
                    break
            
            #只处理重定向信息
            if response.status_code not in [300,301,302,303,307]:
                break
            
            data = None
            method = urlfetch.GET
            self.cookie.load(response.headers.get('set-cookie', ''))
            urlnew = response.headers.get('Location')
            if urlnew and not urlnew.startswith("http"):
                url = urlparse.urljoin(url, urlnew)
            else:
                url = urlnew
            maxRedirect -= 1
            
        return response
        
    def _getHeaders(self, cookie, url):
        headers = {
             'User-Agent':'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36',
             'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
             'Cookie':self._makeCookieHeader(cookie)
                }
        if self.addReferer:
            headers['Referer'] = self.host if self.host else url
        return headers
        
    def _makeCookieHeader(self, cookie):
        cookieHeader = ""
        for value in cookie.values():
            cookieHeader += "%s=%s; " % (value.key, value.value)
        return cookieHeader

