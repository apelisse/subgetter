# -*- coding: utf-8 -*-

import logging
import os
import re
import struct
import sys

import opensubtitles


class Movie(object):
    def __init__(self, name, kind="movie", imdbid=0, season=0, episode=0):
        self.name = str(name)
        try:
            self.imdbid = int(imdbid)
        except ValueError:
            self.imdbid = 0
        self.kind = str(kind)
        try:
            self.season = int(season)
        except ValueError:
            self.season = 0
        try:
            self.episode = int(episode)
        except ValueError:
            self.episode = 0

    def __str__(self):
        if self.kind == "episode":
            tvshow = "\nSeason {0.season} Episode {0.episode}".format(self)
        else:
            tvshow = ""

        return "Name: {0.name}\nKind: {0.kind}\nIMDb Id: {0.imdbid}{1}".format(
            self, tvshow)

    def update_info(self, movie):
        self.name = movie.name
        self.imdbid = movie.imdbid
        self.kind = movie.kind
        self.season = movie.season
        self.episode = movie.episode

class MovieFile(Movie):
    def __init__(self, path):
        super(MovieFile, self).__init__("", "")

        # File info
        self.path = str(path)
        self.hash = self.__hash(path)
        self.size = os.path.getsize(path)
        self.extension = path.split('.')[-1]

        # Any subfiles ?
        self.subfile = None

    def __str__(self):
        return "Movie {0.path} ({0.hash} size {0.size}):\n{1}".format(
            self, super(MovieFile, self).__str__())

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

    def osdb_criteria(self):
        return {
            'hash': self.hash,
            'size': self.size,
            'name': self.filename(),
            }

    def guess(self):
        """
        Let's try to guess what movie it can be.

        @return: Movie with the info we guessed
        """
        # XXX: Potentially, we could remove some garbage here
        name = self.filename()

        epsea = self.__guess_episode_season()
        if not epsea:
            return Movie(name=name)
        else:
            return Movie(name=name,
                         kind="episode",
                         season=epsea[0],
                         episode=epsea[1])

    def __guess_episode_season(self):
        base = os.path.basename(self.path)

        match = re.search(
            "[sS]?(?P<season>\d{1,2})[-xXeE](?P<episode>\d{1,2})",
            base)
        if match:
            return (int(match.groupdict()['season']),
                    int(match.groupdict()['episode']))
        else:
            return None


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
