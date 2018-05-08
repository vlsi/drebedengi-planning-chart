#!/usr/bin/python
# -*- coding: utf-8 -*-

import Cookie
import cookielib
import datetime as dt
import json
import re
import urllib
import urllib2
import logging
from datetime import datetime
from decimal import Decimal

from lxml import html


class DdCategory:
    def __init__(self, id, name, parent_id=None):
        self.id = id
        self.name = name
        self.parent_id = parent_id

    def __unicode__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
        }

    def __repr__(self):
        return (u'DdCategory(' + unicode(self.id) + u', ' + unicode(self.name) + u', ' + unicode(self.parent_id) + u')').encode('utf-8')

class DdPlace:
    def __init__(self, id, name, is_hidden=False, is_debt=False):
        self.id = id
        self.name = name
        self.is_hidden = is_hidden
        self.is_debt = is_debt

    def __unicode__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_hidden': self.is_hidden,
            'is_debt': self.is_debt,
        }

    def __repr__(self):
        return (u'DdPlace(' + unicode(self.id) + u', ' + unicode(self.name) + u', hidden: ' + unicode(self.is_hidden) +\
                u', debt: ' + unicode(self.is_debt) + u')').encode('utf-8')


class DdTransaction:
    def __init__(self, category, amount, comment, from_account, to_account, date, is_planned):
        self.category = category
        self.amount = amount
        self.from_account = from_account
        self.to_account = to_account
        self.date = date
        self.comment = comment
        self.is_planned = is_planned

    def to_json(self):
        return {
            'date': int(self.date.strftime("%s")),
            'category': 0 if self.category is None else self.category.id,
            'amount': long(self.amount * 100),
            'from': self.from_account.id,
            'to': '0' if self.to_account is None else self.to_account.id,
            'comment': self.comment,
            'is_planned': self.is_planned,
        }

    def __repr__(self):
        return (u'DdTransaction(' + unicode(self.date.strftime('%Y-%m-%d %H:%M')) + u', ' + repr(self.category).decode('utf-8') + u', ' + unicode(self.amount) + u', ' + repr(self.from_account).decode('utf-') + u' => ' + repr(self.to_account).decode('utf-8') + '; ' + self.comment + u')').encode('utf-8')


class NoRedirection(urllib2.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response


class DdApi:
    re_date = re.compile(ur'(?:(\d+) ([^ ]+)(?: (\d+))?|(Сегодня)|(Вчера))[^\d]+(\d+):(\d+)')
    re_move = re.compile(ur"Из '([^'].*)' в '([^'].*)'")
    re_planned = re.compile(ur'\s*([^.]+)\.\s*(.*)')

    months = {u'янв': 1, u'фев': 2,
              u'мар': 3, u'апр': 4,
              u'мая': 5, u'июн': 6,
              u'июл': 7, u'авг': 8,
              u'сен': 9, u'окт': 10,
              u'ноя': 11, u'дек': 12,
              }

    def __init__(self, email='demo@example.com', password='demo', currency_id='17'):
        self.base = 'https://www.drebedengi.ru/'
        self.cookie = Cookie.SimpleCookie()
        self.email = email
        self.password = password
        self.categories = {}
        self.cj = cookielib.CookieJar()
        self.currency_id = currency_id
        self.opener = urllib2.build_opener(NoRedirection, urllib2.HTTPCookieProcessor(self.cj))
        self.places = {}
        self.__places_by_name = {}

    @staticmethod
    def parse_date(str, now, yesterday):
        m = DdApi.re_date.match(str)
        day = m.group(1)
        if day is None:
            # logging.info(str)
            # logging.info(m.group(4))
            # logging.info(m.group(5))
            if m.group(4) is not None:
                day = now.day
                month = now.month
                year = now.year
            elif m.group(5) is not None:
                day = yesterday.day
                month = yesterday.month
                year = yesterday.year
        else:
            month = DdApi.months[m.group(2)]
            year = m.group(3)
            if year is None:
                year = now.year
        return datetime(year=int(year), month=int(month), day=int(day), hour=int(m.group(6)), minute=int(m.group(7)))

    def login(self):
        res = self.opener.open(self.base + '?module=v2_start&action=login',
                               data=urllib.urlencode({
                                   'email': self.email,
                                   'password': self.password,
                                   'ssl': 'on'
                               }))
        res.read()

    def _xhr_headers(self):
        return {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Prototype-Version': '1.7',
            'Origin': 'https://www.drebedengi.ru',
            'Referer': 'https://www.drebedengi.ru/?module=v2_homeBuhPrivate',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': self._makeCookieHeader(self.cookie), #self.cookie.output(header='')
        }

    def __parse_place(self, el, dst=None, is_hidden=False, is_debt=False):
        if dst is None:
            dst = {}
        for div in el.xpath('div'):
            links = div.xpath('a')
            if len(links) > 0:
                second_tag = links[0]
                if second_tag.tag == 'a':
                    # Просто счёт
                    id_ = second_tag.get('id')[9:]
                    dst[unicode(id_)] = DdPlace(id_, second_tag.text, is_hidden=is_hidden, is_debt=is_debt)
                    continue

            group_tag = div.xpath('div[@id]')[0]
            group_id = group_tag.get('id')
            debt = is_debt
            hidden = is_hidden
            if group_id == 'pl_list_w_from_-13':
                debt = True
            elif group_id == 'pl_list_w_from_-3':
                hidden = True

            self.__parse_place(group_tag, dst, hidden, debt)

        return dst

    def get_collections(self):
        # self.opener.addheaders = self._xhr_headers()
        response = self.opener.open(self.base + '?module=v2_homeBuhPrivate',
                                    data=urllib.urlencode({
                                        # 'action': 'reload',
                                        'currencyId': '17',  # TODO: use proper currency
                                        'restDate': '2017-02-01',
                                        'is_with_duty': 'false',
                                        'is_with_accum': 'false',
                                        'is_with_null': 'false',
                                        'is_with_planned': 'false'
                                    }))
        txt = response.read().decode('utf-8')
        # Получаем категории
        categories = re.search(ur'<select id="rz_category">(?:.(?!</div>))+', txt, re.DOTALL)

        for m in re.finditer(ur'(?:<option\s*value="([^"]+)"[^>]*>((?:&nbsp;)*)([^<]*))', categories.group(0)):
            id = m.group(1)
            self.categories[id] = DdCategory(id, m.group(3))

        places = re.search(u'<div id="w_from_all_div">(?:.(?!<div style="padding:5px 0px 0px 20px;margin:10px -5px 0px -12px;border-top:1px solid #ccc"))+', txt, re.DOTALL)

        self.places = self.__parse_place(html.fromstring(places.group(0)))
        for place in self.places.values():
            logging.info(place)
            self.__places_by_name[place.name] = place

    def get_place_by_id(self, id):
        key = unicode(id)
        if not self.places.has_key(key):
            self.places[key] = DdPlace(id, u'Unknown place ' + key, is_hidden=True, is_debt=True)
        return self.places[key]

    def get_place_by_name(self, name):
        key = unicode(name)
        if not self.__places_by_name.has_key(key):
            self.__places_by_name[key] = DdPlace(4242, u'Unknown place ' + key, is_hidden=True, is_debt=True)
        return self.__places_by_name[key]

    def get_balance(self, date = datetime.now()):
        # logging.error('Using date' + date)
        response = self.opener.open(self.base + '?module=v2_homeBuhPrivateRest',
                                    data=urllib.urlencode({
                                        'action': 'reload',
                                        'currencyId': '1469857',  # TODO: use proper currency, not RUB
                                        'restDate': date.strftime("%Y-%m-%d"),
                                        'is_with_duty': 'false',
                                        'is_with_accum': 'false',
                                        'is_with_null': 'false',
                                        'is_with_planned': 'false'
                                    }))
        txt = response.read().decode('utf-8')
        rest_text = re.search(ur'dutyRestList = ([^;]+)', txt)
        return json.loads(rest_text.group(1))


    def get_operations(self, date_from, date_to):
        now = datetime.now()
        yesterday = now - dt.timedelta(days=1)
        response = self.opener.open(self.base + '?module=v2_homeBuhPrivateReport',
                                    data=urllib.urlencode({
                                        'r_what': '6',
                                        'r_how': '1',
                                        'r_period': '0',
                                        'r_who': '0',
                                        'period_from': date_from.strftime("%Y-%m-%d"),
                                        'period_to': date_to.strftime("%Y-%m-%d"),
                                        'r_middle': '0',
                                        'r_is_place': '0',
                                        'r_is_category': '0',
                                        'r_currency': self.currency_id,
                                        'r_search_comment': '',
                                        'r_is_tag': '0',
                                        'is_cat_childs': 'true',
                                        'is_with_rest': 'false',
                                        'is_with_planned': 'true',
                                        'is_course_hist': 'false',
                                        'r_duty': '0',
                                        'r_sum': '0',
                                        'r_sum_from': '',
                                        'r_sum_to': '',
                                        'r_place[]': '0',
                                        'r_category[]': '0',
                                        'r_tag[]': '0',
                                        'action': 'show_report',
                                    }))
        # print response.headers
        txt = response.read().decode('utf-8')
        h = html.fromstring(txt)

        transactions = []
        for t in h.xpath('div[@id="m_last_block"]/div[@class="bBody"]/div[4]/div[@id]'):
            transaction_id = t.get('id')[6:]
            if transaction_id.startswith('grp'):
                for st in t.xpath('div[@id="a_'+ transaction_id+ '_dtlist"]/div[@id]'):
                    tr = self.__parse_transaction(st, now, yesterday)
                    transactions.append(tr)
                continue

            tr = self.__parse_transaction(t, now, yesterday)
            #print repr(tr).decode('utf-8')
            if tr is not None:
                transactions.append(tr)

        return transactions

    @staticmethod
    def __full_text(elem):
        if elem is None:
            return None
        return ''.join(elem.itertext()).strip()

    def __parse_transaction(self, t, now, yesterday):
        is_planned = t.get('title') != ''
        tr_type = t.get('type')
        # if tr_type == 'ch':
        #     return None
        transaction_id = t.get('id')[6:]
        descr_div = t.xpath('div[@class="limited wht"]')[0]
        description = descr_div[0].text
        category_div = descr_div.getnext()
        category_id = category_div.get('value').decode('utf-8')
        amount_div = category_div.getnext()
        amount = Decimal(amount_div.get('value'))
        comment = self.__full_text(t.xpath('div[@id="hdc_' + transaction_id + '"]')[0])
        if comment is None:
            comment = ''
        else:
            comment = comment.strip()
        # logging.info(comment)
        date_div = t.xpath('div[@id="rdt_' + transaction_id + '"]')[0]
        date_text = self.__full_text(date_div)
        oper_text = t[0].get('title')
        from_account = oper_text
        to_account = ''
        # logging.info(oper_text)
        # if oper_text.startswith(u"Из '") or tr_type == 'ch':
        if tr_type == 'm':
            m = self.re_move.match(oper_text)
            category = None
            if m:
                from_account =  self.get_place_by_name(m.group(1)) # m.group(1)
                to_account = self.get_place_by_id(category_id)
        elif tr_type == 'ch':
            category = None
            from_account = self.get_place_by_id(category_id)
            to_account = None
            dst_amount = amount_div.getnext().xpath('div[2]/div')[0]
            dst_amount = self.__full_text(dst_amount)
            dst_amount = Decimal(dst_amount.strip().replace(u"\xa0", ""))
            logging.info(str(amount) + " " + str(dst_amount))
            amount = amount + dst_amount
        else:
            category = self.categories[category_id]
            from_account = self.get_place_by_name(oper_text)
            to_account = None
        # if tr_type != 'ch':
        #     return None
        tr = DdTransaction(category=category, amount=amount, from_account=from_account, to_account=to_account,
                           date=self.parse_date(date_text, now, yesterday), comment=comment, is_planned=is_planned)
        # logging.info(tr)
        return tr

    def _makeCookieHeader(self, cookie):
        cookieHeader = ""
        for value in cookie.values():
            cookieHeader += "%s=%s; " % (value.key, value.value)
        return cookieHeader
