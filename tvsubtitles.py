#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module can be used as an interface to TVSubtitles.net.

Currently it uses some regex rather than html/xml parsing to find
the values we need when downloading the pages.

The main function to be called is L{download_subtitle}.
"""

import argparse
import re
import StringIO
import urllib
import urlparse
import zipfile

__author__ = "Antoine Pelisse"
__copyright__ = "Copyright 2012, Antoine Pelisse"
__license__ = "BSD"
__version__ = "0.9"
__contact__ = "apelisse@gmail.com"

BASE_URL = 'http://www.tvsubtitles.net'


def search_tvshow(tvshow):
    """
    Search for a sire according to tvshow name.

    This returns the same list as it would have been returned by
    U{tvsubtitles.net}. It means that there is B{no processing} on the data.
    It also means that you should not only rely on this and you will probably
    have many stupid results in there as their search engine is I{very}
    permissive.

    @param tvshow: Name of the tvshow
    @return: List of tuples: tvshow id, tvshow name
    """
    tvshow = str(tvshow)

    search_path = urlparse.urljoin(BASE_URL, 'search.php')
    data = urllib.urlencode({'q': tvshow})

    result = urllib.urlopen(search_path, data).read()

    pattern = re.compile("""
    href=\"/tvshow-(?P<tvshowid>\d+)\.html\">
    (?P<name>[^<]+)[ ]
    \(\d{4}-\d{4}\)
    """, re.MULTILINE | re.VERBOSE)

    return pattern.findall(result)


def search_episode(tvshowid, season, episode):
    """
    Searches for a specific episode

    @param tvshowid: Id of the tvshow in tvs database
    @param season: Season number you are interested in
    @param episode: Episode number you are looking for
    @return: Id of the episode
    """
    tvshowid = int(tvshowid)
    season = int(season)
    episode = int(episode)

    search_path = urlparse.urljoin(BASE_URL, 'tvshow-%d-%d.html' % (
        tvshowid, season))

    result = urllib.urlopen(search_path).read()

    match = re.search("""
    %dx%02d.*?href=\"episode-(?P<episodeid>\d+)\.html\">
    """ % (season, episode), result, re.MULTILINE | re.VERBOSE | re.DOTALL)

    return match.group('episodeid')


def search_subtitles(episodeid, language):
    """
    Returns all subtitles available for a specific episode and language.

    @todo: Add more information about subtitles, so we can select one
    decently.

    @param episodeid: Episode of interest
    @param language: Language of the subtitles
    @return: List of all Subtitles Id
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
    """
    Download the given subtitle

    @param subid: Id of the subtitle to download
    @return: Subtitle as text
    """
    subid = int(subid)

    return _download_file(subid)


def _download_subid(subid):
    """
    Download the given subtitle

    @deprecated: It looks like tvs uses the subtitle id as file id, so
    we don't need to get it, we already have that value !

    @param subid: Id of the subtitle to download
    @return: Subtitle as text
    """
    subid = int(subid)
    search_path = urlparse.urljoin(
        self.base_url,
        "subtitle-%d.html" % subid)

    result = urllib.urlopen(search_path).read()

    match = re.search("href=\"download-(\d+).html\"", result)

    return _download_file(match.group(1))


def _download_file(fileid):
    """
    Download Zip archive, look for subtitle file in it, open it and read it.

    @param fileid: Id of the file to download
    @return: Subtitle as text
    """
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


def download_subtitle(tvshow, season, episode, language):
    """
    This is a shortcut function to download a subtitle.

    It actually runs most of the function of the file in the correct
    order to make downloading of a subtitle easy.
    Searches for the tvshow id, then searches for the episode id,
    and then searches for the subtitle id, and then downloads the file and
    reads it !

    @param tvshow: Tvshow name
    @param season: Season number
    @param episode: Episode number
    @param language: Language of the subtitle required
    """
    tvshowid = search_tvshow(tvshow)
    episodeid = search_episode(tvshowid[0][0], season, episode)
    subid = search_subtitles(episodeid, language)

    return download_subid(subid[0])


def main():
    """
    Main function

    This function is called when the script is called by python directly.

    It parses the arguments given on command line and call the
    L{download_subtitle} function to get the subtitle.
    You have to know every arguments of the function to use this script like
    this: tvshow name, season number and episode number. It won't do
    automatic calculation of what is the movie, etc.
    """
    parser = argparse.ArgumentParser(
        description="Download subtitle for TV Episode")
    parser.add_argument('tvshow')
    parser.add_argument('season')
    parser.add_argument('episode')
    parser.add_argument('-l', '--language', default='en')
    parser.add_argument('-o', '--outfile', default='dump.srt')

    args = parser.parse_args()

    sub = download_subtitle(args.tvshow,
                            args.season,
                            args.episode,
                            args.language)

    with open(args.outfile, 'w') as f:
        f.write(sub)


if __name__ == '__main__':
    main()
