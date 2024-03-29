#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import operator
import os
import re
import struct
import sys

import iso639
import misc
import opensubtitles
import tvsubtitles

class Movie(object):
    MOVIE = "movie"
    EPISODE = "episode"
    TVSHOW = "tv series"

    def __init__(self, name, kind=MOVIE, imdbid=0, season=0, episode=0):
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
        if self.kind == self.EPISODE:
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

    def subname(self):
        return '.'.join(self.path.split('.')[:-1]) + '.srt'

    def has_subtitle(self):
        try:
            os.stat(self.subname())
        except OSError:
            return False
        else:
            return True

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

class Asker(object):
    """
    This class gives opportunity to user to select the correct movie.

    Well, this is an abstract class because it doesn't implement a function
    to allow the user to do it. There should be a TextAsker for exemple
    to allow the user to type in the name, etc, or maybe if we have a graphic
    interface, we can implement some other kind of functions.

    Function to be implemented: select
    """
    def __init__(self, ask_threshold):
        """
        Create asker

        @param ask_threshold: Below this score, we ask for suggestions
        """
        self.ask_threshold = ask_threshold

    def pick(self, moviefile, choices):
        """
        Pick a movie amongst choices

        Here goes the algorithm:
           - If one is higher than ask_threshold, pick the highest and notify
           - Else, call select() for all choices

        @param moviefile: MovieFile we are trying to identify
        @param choices: List of tuples: [(Movie, Score), ...]
        @return: Selected movie
        """
        try:
            max_choice = choices[-1]
        except IndexError:
            max_choice = None

        if max_choice and max_choice[1] > self.ask_threshold:
            return max_choice[0]
        else:
            return self.select(moviefile, choices)

    def select(self, moviefile, choices):
        """
        Allow user to select a movie

        This is an abstract base class, and this function should probably
        be implemented by inheriting classes.

        @param moviefile: MovieFile we are trying to identify
        @param choices: List of (movies, score)
        @return: Selected movie
        """
        raise NotImplementedError


class TextAsker(Asker):
    """
    This gives the user the opportunity to fill in the movie name and other
    information manually from a terminal.
    Either select from a list of movies or type in the information.
    """
    def select(self, moviefile, choices):
        """
        Output choices, and read the input
        """
        print 'Identifying movie:', moviefile.path
        print self.__show_choices(choices)
        result = None
        while result is None:
            last_choice = len(choices) or 1
            result = raw_input("Choice [{0}]: ".format(last_choice - 1))
            if result == "":
                result = "0"
            try:
                result = int(result)
            except TypeError:
                print result, "is not a valid choice (not a number)"
                result = None

            if not 0 <= result <= len(choices):
                print result, "is not a valid choice (invalid number)"
                result = None

        # At this point, either result is a valid choice,
        # or we have the max value which is: manual type-in
        if result < len(choices):
            return choices[result][0]
        else:
            return self.__get_from_user()

    def __show_choices(self, choices):
        num = -1
        text = "Select one amongst those choices:\n"
        for num, choice in enumerate(choices):
            text += "[%d] Score: (%2d%%)\n%s\n" % (
                num, int(choice[1] * 100), choice[0])
        text += "[%d] I will give my inputs" % (num + 1)

        return text

    def __get_from_user(self):
        name = raw_input("Movie/Show name: ")
        show_info = None
        while show_info is None:
            show_info = raw_input("SXXEXX or empty if movie: ")
            if show_info == "":
                season = 0
                episode = 0
                kind = Movie.MOVIE
                break
            match = re.match("S(\d{1,2})E(\d{1,2})", show_info)
            if not match:
                show_info = None
                continue
            else:
                season = match.group(1)
                episode = match.group(2)
                kind = Movie.EPISODE

        return Movie(name=name, episode=episode, season=season, kind=kind)


class AutomaticAsker(Asker):
    """
    Picks the best matching movie, and that's it.

    It does not interact with anything or anybody.
    It just returns the best match.
    """
    def __init__(self, minimum=0):
        super(AutomaticAsker, self).__init__(minimum)

    def select(self, choices):
        """
        Choose no choice if we have to select

        If we have to select a movie, it means we are below our minimum score,
        it means that we should pick no choice at all
        """
        return None

class MovieScore(object):
    def __score_kind(self, given, guessed):
        """
        Calculate score based on movie kind, season and episode

        This modify the movie given if we fill we can do better

        @param given: Movie info given
        @param guessed: Movie info we tried to guess
        @return: score calculated. Range is 0 to 1
        @rtype: float
        """
        score = 0

        # Handle score for kind, season and episode
        if given.kind == Movie.TVSHOW and guessed.kind == Movie.EPISODE:
            given.kind = Movie.EPISODE
            given.season = guessed.season
            given.episode = guessed.episode
            score = 0.75
        elif (given.kind == Movie.EPISODE and
              guessed.kind == Movie.EPISODE):
            score += 0.5
            if given.season == guessed.season:
                score += 0.25
            if given.episode == guessed.episode:
                score += 0.25
            # We need to get show name from episode name, if possible
            m = re.search("\"(.*)\"", given.name)
            if m:
                given.name = m.group(1)
        elif given.kind == Movie.MOVIE and guessed.kind == Movie.MOVIE:
            score = 1

        assert 0 <= score <= 1

        return score

    def __score_name(self, given, guessed):
        """
        Calculate score based on name

        @param given: Given movie name
        @param guessed: Guessed movie name
        @return: score calculated. Range from 0 to 1.
        @rtype: float
        """
        score = misc.strings_contained(guessed, given)
        score += misc.dice_coefficient(guessed, given)

        assert 0 <= score <= 2

        return score / 2

    def score(self, movie_given, movie_guessed):
        """
        Give a score for matching two movies

        Kind score is 40%
        Name score is 60%

        @warning: This method can modify the movie_given

        @param movie_guessed: This is what we guessed from the filename
        @param movie_given: This is the movie given by osdb
        @return: (movie_given, score), score is what we calculated
        score range is from 0 to 1
        @rtype: float
        """
        kind_score = self.__score_kind(movie_given, movie_guessed)
        name_score = self.__score_name(movie_given.name, movie_guessed.name)

        score = kind_score * 0.4 + name_score * 0.6

        return (movie_given, score)

def identify_one_movie(moviefile, movies, asker):
    """
    Identify one movie

    @param moviefile: Movie to identify
    @param movies: Movies we found from osdb
    @param asker: Asker instance to get opinion from user
    """
    movie_guess = moviefile.guess()

    # Give a note to each movies, against what we have
    scores = [MovieScore().score(movie, movie_guess) for movie in movies]

    # sort scores
    scores.sort(key=operator.itemgetter(1))

    # Finally, let's decide amongst all movies
    movie = asker.pick(moviefile, scores)

    if movie:
        moviefile.update_info(movie)


def identify_movies(moviefiles, osdb, asker = None):
    """
    Identify movie information from moviesfiles

    Most of the logic to identify movies is obviously here.
    It would be here to add an exhaustive description of how we
    try to identify the movie

    @param moviefiles: Movies we want to identify
    @param osdb: OSDb Handler
    @param asker: Asker instance to get input from user
    """
    if not asker:
        asker = AutomaticAsker()

    movies_info = osdb.check_hashes(moviefiles.keys())

    for moviehash, moviefile in moviefiles.items():
        try:
            identify_one_movie(
                moviefile,
                [Movie(info['MovieName'],
                       kind=info['MovieKind'],
                       imdbid=info['MovieImdbID'],
                       season=info['SeriesSeason'],
                       episode=info['SeriesEpisode'])
                 for info in movies_info[moviehash]],
                asker)
        except KeyError:
            pass


def select_language(code):
    """
    Get 2 letters and 3 letters code for language given as code

    If one of the version doesn't exist, use the other version also

    @param code: Language code we want to evaluate
    @return: Tuple (two_letters_code, three_letters_code)
    """
    language = iso639.find_language(code)
    if not language:
        # Use default value
        return ('en', 'eng')
    else:
        if not language['2L']:
            language['2L'] = language['3L']
        if not language['3L']:
            language['3L'] = language['2L']
        return (language['2L'], language['3L'])

def main():
    parser = argparse.ArgumentParser(
        description="Get information about a movie")

    parser.add_argument('movie', help='Movie to investigate', nargs='+')
    parser.add_argument('-l', '--language', default='eng')
    parser.add_argument('-f', '--force', action='store_true')
    args = parser.parse_args()

    osdb = opensubtitles.OpenSubtitles()
    asker = TextAsker(0.7)

    moviefiles = [MovieFile(movie) for movie in args.movie]

    if not args.force:
        for moviefile in list(moviefiles):
            if moviefile.has_subtitle():
                print moviefile.path, \
                    'already has a subtitle (use -f to force)'
                moviefiles.remove(moviefile)

    identify_movies({mfile.hash: mfile for mfile in moviefiles},
                   osdb, asker)

    print
    print 'Identification summary'
    print
    for moviefile in moviefiles:
        if not moviefile.name:
            print 'Unable to identify:'
        print moviefile

    lang_2l, lang_3l = select_language(args.language)

    subs = osdb.download_subtitles(
        [moviefile.osdb_criteria() for moviefile in moviefiles],
        language=lang_3l)

    for moviefile in moviefiles:
        sub = None
        if moviefile.hash in subs:
            sub = subs[moviefile.hash]
        elif moviefile.kind == Movie.EPISODE:
            sub = tvsubtitles.download_subtitle(moviefile.name,
                                                moviefile.season,
                                                moviefile.episode,
                                                lang_2l)

        if not sub:
            print "No subtitle found for this movie"
            continue

        with open(moviefile.subname(), 'w') as f:
            f.write(sub)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
