#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import re
import StringIO
import urllib
import urlparse
import zipfile


BASE_URL = 'http://www.tvsubtitles.net'


def search_serie(serie):
    """
    Return the list of series found, with matching id
    """
    search_path = urlparse.urljoin(BASE_URL, 'search.php')
    data = urllib.urlencode({'q': serie})

    result = urllib.urlopen(search_path, data).read()

    pattern = re.compile("""
    href=\"/tvshow-(?P<serieid>\d+)\.html\">
    (?P<name>[^<]+)[ ]
    \(\d{4}-\d{4}\)
    """, re.MULTILINE | re.VERBOSE)

    return pattern.findall(result)


def search_episode(serieid, season, episode):
    serieid = int(serieid)
    season = int(season)
    episode = int(episode)

    search_path = urlparse.urljoin(BASE_URL, 'tvshow-%d-%d.html' % (
        serieid, season))

    result = urllib.urlopen(search_path).read()

    match = re.search("""
    %dx%02d.*?href=\"episode-(?P<episodeid>\d+)\.html\">
    """ % (season, episode), result, re.MULTILINE | re.VERBOSE | re.DOTALL)

    return match.group('episodeid')


def search_subtitles(episodeid, language):
    """
    Return a list of ids
    """
    episodeid = int(episodeid)

    search_path = urlparse.urljoin(BASE_URL, "episode-%d.html" % episodeid)

    result = urllib.urlopen(search_path).read()

    matches = re.findall("""
    subtitle-(?P<subid>\d+).html
    .*?
    flags/(?P<language>\w+).gif
    """, result, re.VERBOSE | re.MULTILINE | re.DOTALL)

    return [subid for subid, lang in matches if lang == language]


def download_subid(subid):
    subid = int(subid)
    # search_path = urlparse.urljoin(
    #     self.base_url,
    #     "subtitle-%d.html" % subid)

    # result = urllib.urlopen(search_path).read()

    # match = re.search("href=\"download-(\d+).html\"", result)

    # return _download_file(match.group(1))
    return _download_file(subid)


def _download_file(fileid):
    download_path = urlparse.urljoin(BASE_URL, "download-%d.html" % fileid)

    result = urllib.urlopen(download_path).read()

    fzip = zipfile.ZipFile(StringIO.StringIO(result))

    subname = None
    for f in fzip.infolist():
        fname = f.filename
        if (fname.endswith('srt') or
            fname.endswith('sub')):
            subname = fname

    if not subname:
        raise Exception('No subtitle in zip file')

    fsub = fzip.read(subname)

    return fsub


def download_subtitle(serie, season, episode, language):
    serieid = search_serie(serie)
    episodeid = search_episode(serieid[0][0], season, episode)
    subid = search_subtitles(episodeid, language)

    return download_subid(subid[0])

def main():
    parser = argparse.ArgumentParser(
        description="Download subtitle for TV Episode")
    parser.add_argument('serie')
    parser.add_argument('season')
    parser.add_argument('episode')
    parser.add_argument('-l', '--language', default='en')
    parser.add_argument('-o', '--outfile', default='dump.srt')

    args = parser.parse_args()

    sub = download_subtitle(args.serie,
                            args.season,
                            args.episode,
                            args.language)

    with open(args.outfile, 'w') as f:
        f.write(sub)

if __name__ == '__main__':
    main()
