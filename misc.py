# -*- coding: utf-8 -*-

"""
Some utility functions that can be used in this project.

Currently, we only provide one function:
  - L{dice_coefficient}
"""

import re


def dice_coefficient(a, b, ignore_case=True):
    """
    Calculate dice coefficient

    Downloaded from
    U{http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Dice's_coefficient#Python}.
    And then extended to add ignore_case parameter.

    @param a: First string
    @param b: Second string
    @param ignore_case: Ignore case in calculation
    @return: Coefficient (0 < coef < 1). The higher the closer.
    """
    if not len(a) or not len(b):
        return 0.0

    if ignore_case:
        a = a.lower()
        b = b.lower()

    if len(a) == 1:
        a = a + u'.'
    if len(b) == 1:
        b = b + u'.'

    a_bigram_list = []
    for i in range(len(a) - 1):
        a_bigram_list.append(a[i:i + 2])
    b_bigram_list = []
    for i in range(len(b) - 1):
        b_bigram_list.append(b[i:i + 2])

    a_bigrams = set(a_bigram_list)
    b_bigrams = set(b_bigram_list)
    overlap = len(a_bigrams & b_bigrams)
    dice_coeff = overlap * 2.0 / (len(a_bigrams) + len(b_bigrams))

    return dice_coeff


def strings_contained(complete_name, reduced_name):
    """
    Look for strings in reduced_name in complete_name

    The idea is to search for all the substrings of reduced_name inside
    complete_name. Substrings of reduced_name are calculated by splitting
    for each non-word character.
    If all characters are found, it's quite a good sign that the name is close

    @param complete_name: Name of the string to look in (most likely bigger
    than the real string, with junk)
    @param reduced_name: Name to look for, is it in the string
    @return: Percentage of word found
    @rtype: float
    """
    substrings = re.split('\W+', reduced_name)

    return (len([1 for string in substrings if string in complete_name]) /
            len(substrings))
