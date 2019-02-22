import pytest

from collections import Counter
import random

from tesserae.tokenizers import BaseTokenizer


class TestBaseTokenizer(object):
    __test_class__ = BaseTokenizer

    def test_init(self, connection):
        t = self.__test_class__(connection)
        assert t.tokens == []
        assert t.frequencies == Counter()

    def test_normalize(self, connection):
        test_words = ['foo', 'Bar', 'BAZ', 'FoO bAr BaZ']
        punct = '.?:;"!'
        whitespace = ' \t\n\r'

        t = self.__test_class__(connection)

        # Ensure that an empty string is returned as an empty string
        assert t.normalize('') == ''

        # Ensure that an empty list is returned as an empty string
        assert t.normalize(['']) == ''

        # Ensure that standard words are converted to lowercase and split if
        # spaces exist in the string.
        for word in test_words[:-1]:
            assert t.normalize(word) == word.lower()

        assert t.normalize(test_words[-1]) == 'foo bar baz'

        # Ensure that normalization is applied to every string in a list
        for i in range(len(test_words) - 1):
            assert t.normalize(test_words[:i + 1]) == \
                   ' '.join([w.lower()for w in test_words[:i + 1]])

        # Ensure that strings containing only whitespace, punctuation, or
        # digits are returned as empty lists
        for i in range(len(punct)):
            assert t.normalize(punct[i]) == punct[i]
            assert t.normalize(punct[:i + 1]) == \
                   ''.join([p for p in punct[:i + 1]])

        for i in range(len(whitespace)):
            assert t.normalize(whitespace[i]) == whitespace[i]
            assert t.normalize(whitespace[:i + 1]) == \
                   ''.join([w for w in whitespace[:i + 1]])

        # Ensure that tokens with punctuation and whitespace are returned
        # lowercase with punct and whitespace removed
        for word in test_words[:-1]:
            for _ in range(100):
                p = punct[random.randint(0, len(punct) - 1)]
                w = whitespace[random.randint(0, len(whitespace) - 1)]

                assert t.normalize(w + word) == ''.join([w, word.lower()])
                assert t.normalize(p + word) == ''.join([p, word.lower()])
                assert t.normalize(word + w) == ''.join([word.lower(), w])
                assert t.normalize(word + p) == ''.join([word.lower(), p])
                assert t.normalize(p + word + w) == \
                       ''.join([p, word.lower(), w])
                assert t.normalize(w + word + p) == \
                       ''.join([w, word.lower(), p])
                assert t.normalize(p + w + word) == \
                       ''.join([p, w, word.lower()])
                assert t.normalize(w + p + word) == \
                       ''.join([w, p, word.lower()])
                assert t.normalize(word + p + w) == \
                       ''.join([word.lower(), p, w])
                assert t.normalize(word + w + p) == \
                       ''.join([word.lower(), w, p])
                assert t.normalize(p + w + word + p + w) == \
                       ''.join([p, w, word.lower(), p, w])
                assert t.normalize(w + p + word + w + p) == \
                       ''.join([w, p, word.lower(), w, p])
                assert t.normalize(w + p + word + p + w) == \
                       ''.join([w, p, word.lower(), p, w])
                assert t.normalize(p + w + word + w + p) == \
                       ''.join([p, w, word.lower(), w, p])

    def test_featurize(self, connection):
        t = self.__test_class__(connection)

        if self.__test_class__ is BaseTokenizer:
            with pytest.raises(NotImplementedError):
                t.featurize('foo')
