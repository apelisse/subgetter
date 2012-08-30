import base64
import datetime
import decimal
import logging
import xmlrpclib
import zlib

class OpenSubtitles(object):
    def __init__(self):
        self.conn = xmlrpclib.ServerProxy(
            'http://api.opensubtitles.org/xml-rpc')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.token = None
        self.osdb_time = decimal.Decimal()
        self.transfer_time = datetime.timedelta()
        self.__login()


    def __request(self, name, *args, **kw):
        func = getattr(self.conn, name)

        self.logger.debug('Request: %s %s %s %s', name, self.token, args, kw)

        btime = datetime.datetime.now()
        if name != 'LogIn':
            answer = func(self.token, *args, **kw)
        else:
            answer = func(*args, **kw)
        self.transfer_time += (datetime.datetime.now() - btime)

        self.logger.debug('Answer: %s', answer)

        if answer['status'] == '401 Unauthorized' and name != 'LogIn':
            self.__login()
        elif not answer['status'].startswith('2'):
            raise Exception('Request failed: %s' % answer['status'])

        self.osdb_time += decimal.Decimal(answer['seconds'])

        return answer


    def __login(self):
        self.logger.info('Logging in...')
        answer = self.__request('LogIn', '', '', 'en', 'OS Test User Agent')
        self.token = answer['token']


    def __logout(self):
        self.logger.info('Logging out.')
        self.__request('LogOut')


    def check_hashes(self, hashes):
        answer = self.__request('CheckMovieHash2', hashes)

        if not answer['data']:
            return {}

        return answer['data']


    def download_subtitles(self, movies, language='eng'):
        """
        Movies is a dictionary. It should contain:
        - hash
        - filesize
        - filename
        """
        array = [{'moviehash': movie['hash'],
                  'moviebytesize': movie['size'],
                  'tag': movie['name'],
                  'sublanguageid': language}
                 for movie in movies]

        answer = self.__request('SearchSubtitles', array)

        if answer['data'] == False:
            return {}

        # Take the first one
        subs = {data['IDSubtitleFile']: data['MovieHash']
                for data in answer['data']}

        answer = self.__request('DownloadSubtitles', subs.keys())

        return {
            subs[data['idsubtitlefile']]: self.__convert_subtitle(data['data'])
            for data in answer['data']}


    def subtitle_language(self, subs):
        """
        Subs is a dict of: {md5: sub}
        """
        zipsubs = [base64.b64encode(zlib.compress(sub))
                   for sub in subs.values()]
        answer = self.__request('DetectLanguage', zipsubs)

        return answer['data']

    def __convert_subtitle(self, bzdata):
        zdata = base64.b64decode(bzdata)

        return zlib.decompress(zdata, 15 + 32)

    def __del__(self):
        # Be kind, let's say we are leaving
        if self.token:
            self.__logout()
        self.logger.info('Total time used by osdb: %s secs',
                         self.osdb_time.quantize(decimal.Decimal('0.001')))
        time = decimal.Decimal(
            self.transfer_time.total_seconds()) - self.osdb_time
        self.logger.info('Total transfer time: %s secs',
                         time.quantize(decimal.Decimal('0.001')))
