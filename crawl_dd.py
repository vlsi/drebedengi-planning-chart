#!/usr/bin/python
# -*- coding: utf-8 -*-

import Cookie
import re
import urllib

from xml.sax.saxutils import escape
from lxml import html

import logging
import json

from datetime import datetime
import datetime as dt

import webapp2
from google.appengine.api import urlfetch
from google.appengine.ext import webapp

from crawl_dd_api import DdApi


def add_months(d, m):
    return d.replace(year=d.year+(d.month+m-1)/12, month=(d.month+m-1)%12+1)

class CrawlDd(webapp.RequestHandler):
    def __init__(self, request, response):
        super(CrawlDd, self).initialize(request, response)
        self.api = DdApi()

    def get(self):
        api = DdApi(email='demo@example.com', password='demo')
        api.login()
        api.get_collections()

        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        from_date = now.replace(day=27)
        if from_date > now:
            from_date = add_months(from_date, -1)
        from_date = add_months(from_date, -1)

        to_date = add_months(from_date, 12*1+6)
        # to_date = datetime(year=2018, month=9, day=30)

        trans = api.get_operations(from_date + dt.timedelta(days=1), to_date)
        trans_json = json.dumps([i.to_json() for i in reversed(trans)])

        places_json = json.dumps(dict([(k, v.to_json()) for k, v in api.places.iteritems()]))
        categories_json = json.dumps(dict([(k, v.to_json()) for k, v in api.categories.iteritems()]))

        balance_json = json.dumps(api.get_balance(from_date).get(api.currency_id))

        self.response.headers['Content-Type'] = 'application/javascript; charset=UTF-8'
        self.response.out.write(u'''
        var balanceDate = %s;
        var balance = %s;
        var places = %s;
        var categories = %s;
        var trans = %s;
        ''' % (now.strftime("%s"), balance_json, places_json, categories_json, trans_json))


app = webapp2.WSGIApplication([
    ('/chart/js/data.js', CrawlDd),
], debug=False)
