# -*- coding: utf-8 -*-

import re
import StringIO
import urllib
import urlparse
import zipfile

class TVSubtitles(object):
    def __init__(self):
        self.base_url = 'http://www.tvsubtitles.net'

    def search(self, serie):
        """
        Return the list of series found, with matching id
        """
        search_path = urlparse.urljoin(self.base_url, 'search.php')
        data = urllib.urlencode({'q': serie})

        result = urllib.urlopen(search_path, data).read()

        pattern = re.compile("""
        href=\"/tvshow-(?P<serieid>\d+)\.html\">
        (?P<name>[^<]+)[ ]
         \(\d{4}-\d{4}\)
        """, re.MULTILINE | re.VERBOSE)

        return pattern.findall(result)


    def search_episode(self, serieid, season, episode):
        serieid = int(serieid)
        season = int(season)
        episode = int(episode)

        search_path = urlparse.urljoin(
            self.base_url,
            'tvshow-%d-%d.html' % (serieid, season))

        result = urllib.urlopen(search_path).read()

        match = re.search("""
        %dx%02d.*?href=\"episode-(?P<episodeid>\d+)\.html\">
        """ % (season, episode), result, re.MULTILINE | re.VERBOSE | re.DOTALL)

        return match.group('episodeid')

    def search_subtitles(self, episodeid, language):
        """
        Return a list of ids
        """
        episodeid = int(episodeid)

        search_path = urlparse.urljoin(
            self.base_url,
            "episode-%d.html" % episodeid)

        result = urllib.urlopen(search_path).read()

        matches = re.findall("""
        subtitle-(?P<subid>\d+).html
        .*?
        flags/(?P<language>\w+).gif
        """, result, re.VERBOSE | re.MULTILINE | re.DOTALL)

        return [subid for subid, lang in matches if lang == language]

    def download_subid(self, subid):
        subid = int(subid)
        # search_path = urlparse.urljoin(
        #     self.base_url,
        #     "subtitle-%d.html" % subid)

        # result = urllib.urlopen(search_path).read()

        # match = re.search("href=\"download-(\d+).html\"", result)

        # return self.__download_file(match.group(1))
        return self.__download_file(subid)

    def __download_file(self, fileid):
        download_path = urlparse.urljoin(
            self.base_url,
            "download-%d.html" % fileid)

        result = urllib.urlopen(download_path).read()

        fzip = zipfile.ZipFile(StringIO.StringIO(result))
        fsub = fzip.read(fzip.infolist()[0])

        return fsub

    def download_subtitle(self, serie, season, episode, language):
        serieid = self.search(serie)
        episodeid = self.search_episode(serieid[0][0], season, episode)
        subid = self.search_subtitles(episodeid, language)

        return self.download_subid(subid[0])
