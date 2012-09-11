# -*- coding: utf-8 -*-

import logging
import os
import re
import struct
import sys

import opensubtitles


class Movie(object):
    def __init__(self, path):
        # File info
        self.path = str(path)
        self.hash = self.__hash(path)
        self.size = os.path.getsize(path)
        self.extension = path.split('.')[-1]

        # Movie info
        self.name = None
        self.imdbid = int()
        self.kind = None

        # These are specific to tv shows
        self.episode = int()
        self.season = int()

        # Any subfiles ?
        self.subfile = None

    def __str__(self):
        return """
Movie %s (%s size %s):
Found name: %s
IMDb Id: %d
Video type: %s
Season %02d Episode %02d
""" % (self.path, self.hash, self.size,
       self.name, self.imdbid, self.kind,
       self.season, self.episode)

    @staticmethod
    def __hash(path):
        """
        Calculates the hash value of a movie.
        Source:
http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
        """
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)

        f = open(path, "rb")

        filesize = os.path.getsize(path)
        hash = filesize

        if filesize < 65536 * 2:
            return "SizeError"

        for x in range(65536 // bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

        f.seek(max(0, filesize - 65536), 0)
        for x in range(65536 // bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF

        f.close()
        returnedhash = "%016x" % hash
        return returnedhash

    def filename(self):
        return os.path.basename(self.path)

    def update(self, info):
        """
        Do not accept a list for the moment
        """
        if 'MovieName' in info:
            self.name = info['MovieName']
        if 'SeriesSeason' in info:
            self.season = int(info['SeriesSeason'])
        if 'SeriesEpisode' in info:
            self.episode = int(info['SeriesEpisode'])
        if 'MovieKind' in info:
            self.kind = info['MovieKind']
        if 'MovieImdbID' in info:
            self.imdbid = int(info['MovieImdbID'])

    def osdb_criteria(self):
        return {
            'hash': self.hash,
            'size': self.size,
            'name': self.filename(),
            }

    def add_subtitle(self, sub, language='eng'):
        base = self.path[-len(self.extension):]
        subfile = base + '.srt'  # We assume the file is srt ...

        self.subfile = subfile
        with open(subfile, 'w') as subf:
            subf.write(sub)

    def find_season_episode(self):
        assert 'serie' in self.kind
        assert not self.season
        assert not self.episode

        base = os.path.basename(self.path)

        match = re.search(
            "[sS]?(?P<season>\d{1,2})[-xXeE](?P<episode>\d{1,2})",
            base)
        if match:
            self.season = int(match.groupdict()['season'])
            self.episode = int(match.groupdict()['episode'])


def main():
    osdb = opensubtitles.OpenSubtitles()

    language = 'fra'

    movies = {}
    for f in sys.argv[1:]:
        movie = Movie(f)
        movies[movie.hash] = movie

    new_info = osdb.check_hashes(movies.keys())

    for hash, info in new_info.items():
        try:
            movies[hash].update(info[0])
        except IndexError:
            logging.debug('Hash not found for movie: %s', movies[hash])

    subs = osdb.download_subtitles(
        [movie.osdb_criteria() for movie in movies.values()], language)

    for hash, sub in subs.items():
        movies[hash].add_subtitle(sub, language)

    logging.info('%d movies with subtitle downloaded',
                 len([1 for movie in movies.values() if movie.subfile]))

    logging.info('%d movies with no subtitle downloaded',
                 len([1 for movie in movies.values() if not movie.subfile]))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
