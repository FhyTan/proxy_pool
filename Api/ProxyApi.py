# -*- coding: utf-8 -*-
# !/usr/bin/env python
"""
-------------------------------------------------
   File Name：     ProxyApi.py
   Description :   WebApi
   Author :       JHao
   date：          2016/12/4
-------------------------------------------------
   Change Activity:
                   2016/12/04: WebApi
                   2019/08/14: 集成Gunicorn启动方式
-------------------------------------------------
"""
__author__ = 'JHao'

import platform
import sys

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from werkzeug.wrappers import Response

sys.path.append('../')

from Config.ConfigGetter import config
from Manager.ProxyManager import ProxyManager
from Util.LogHandler import LogHandler
from Util.WebRequest import WebRequest

app = Flask(__name__)
logger = LogHandler('proxy_api')


class JsonResponse(Response):
    @classmethod
    def force_type(cls, response, environ=None):
        if isinstance(response, (dict, list)):
            response = jsonify(response)

        return super(JsonResponse, cls).force_type(response, environ)


app.response_class = JsonResponse

api_list = {
    'get': u'get an useful proxy',
    # 'refresh': u'refresh proxy pool',
    'get_all': u'get all proxy from proxy pool',
    'delete?proxy=127.0.0.1:8080': u'delete an unable proxy',
    'get_status': u'proxy number',
    'view?site=baidu.com': u'use proxy to view a page',
}


@app.route('/')
def index():
    return api_list


@app.route('/get/')
def get():
    proxy = ProxyManager().get()
    return proxy.info_json if proxy else {"code": 0, "src": "no proxy"}


@app.route('/refresh/')
def refresh():
    # TODO refresh会有守护程序定时执行，由api直接调用性能较差，暂不使用
    # ProxyManager().refresh()
    pass
    return 'success'


@app.route('/get_all/')
def getAll():
    proxies = ProxyManager().getAll()
    return jsonify([_.info_dict for _ in proxies])


@app.route('/delete/', methods=['GET'])
def delete():
    proxy = request.args.get('proxy')
    ProxyManager().delete(proxy)
    return {"code": 0, "src": "success"}


@app.route('/get_status/')
def getStatus():
    status = ProxyManager().getNumber()
    return status


@app.route('/view/')
def view():
    site = request.args.get('site', 'http://www.baidu.com')
    if not site.startswith('http://'):
        site = 'http://' + site

    proxy = ProxyManager().get()
    if proxy is None:
        return 'no avaliable proxy to use'

    proxy = proxy.proxy
    logger.info('using proxy {} to view site {}'.format(proxy, site))

    try:
        # use proxy to get target page
        proxies = {
            "http": "http://{proxy}".format(proxy=proxy),
            "https": "http://{proxy}".format(proxy=proxy),
        }
        headers = WebRequest().header
        res = requests.get(site, proxies=proxies, headers=headers, timeout=5)

        # add proxy info to the top of html
        html = BeautifulSoup(res.text, 'lxml')
        info = BeautifulSoup('''
            <div style='position:absolute;z-index:999999;background-color:white;font-size=20px'>
                <p>using proxy: {}  status code: {}</p>
            <div>'''.format(proxy, res.status_code), 'lxml')
        html.body.insert(0, info.div)
        return str(html.html), {'Content-Type': 'text/html'}
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return 'proxy {} timeout, please try again'.format(proxy)
    except requests.exceptions.ProxyError:
        return 'proxy {} error, please try again'.format(proxy)


if platform.system() != "Windows":
    import gunicorn.app.base
    from six import iteritems


    class StandaloneApplication(gunicorn.app.base.BaseApplication):

        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super(StandaloneApplication, self).__init__()

        def load_config(self):
            _config = dict([(key, value) for key, value in iteritems(self.options)
                            if key in self.cfg.settings and value is not None])
            for key, value in iteritems(_config):
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application


def runFlask():
    app.run(host=config.host_ip, port=config.host_port)


def runFlaskWithGunicorn():
    _options = {
        'bind': '%s:%s' % (config.host_ip, config.host_port),
        'workers': 4,
        'accesslog': '-',  # log to stdout
        'access_log_format': '%(h)s %(l)s %(t)s "%(r)s" %(s)s "%(a)s"'
    }
    StandaloneApplication(app, _options).run()


if __name__ == '__main__':
    if platform.system() == "Windows":
        runFlask()
    else:
        runFlaskWithGunicorn()
