import pytest

from test_base_tokenizer import TestBaseTokenizer

import json
import os
import re
import string
import sys

from cltk.semantics.latin.lookup import Lemmata
from cltk.stem.latin.j_v import JVReplacer

from tesserae.db import TessMongoConnection
from tesserae.db.entities import Text
from tesserae.tokenizers import LatinTokenizer
from tesserae.utils import TessFile


@pytest.fixture(scope='module')
def latin_tokens(latin_files):
    tokens = []
    for fname in latin_files:
        fname = os.path.splitext(fname)[0] + '.tokens.json'
        with open(fname, 'r') as f:
            ts = [t for t in json.load(f)]
            tokens.append(ts)
    return tokens


@pytest.fixture(scope='module')
def latin_word_frequencies(latin_files):
    freqs = []
    for fname in latin_files:
        freq = {}
        fname = os.path.splitext(fname)[0] + '.freq_score_word'
        with open(fname, 'r') as f:
            for line in f.readlines():
                if '#' not in line:
                    word, n = line.strip().split()
                    freq[word] = int(n)
        freqs.append(freq)
    return freqs


class TestLatinTokenizer(TestBaseTokenizer):
    __test_class__ = LatinTokenizer

    def test_init(self, connection):
        t = self.__test_class__(connection)
        assert t.connection is connection
        assert hasattr(t, 'jv_replacer')
        assert isinstance(t.jv_replacer, JVReplacer)
        assert hasattr(t, 'lemmatizer')
        assert isinstance(t.lemmatizer, Lemmata)

    def test_normalize(self, connection, latin_files, latin_tokens):
        tessconn = TessMongoConnection('127.0.0.1', 27017, None, None)
        tessconn.connection = connection
        la = self.__test_class__(tessconn)

        for i in range(len(latin_files)):
            fname = latin_files[i]
            ref_tokens = [t for t in latin_tokens[i] if 'FORM' in t]

            t = TessFile(fname)

            tokens = re.split(la.split_pattern, la.normalize(t.read()))
            tokens = [t for t in tokens if re.search(la.word_characters, t)]

            correct = map(lambda x: ('FORM' in x[1] and x[0] == x[1]['FORM']) or x[0] == '',
                          zip(tokens, ref_tokens))

            assert all(correct)

            # token_idx = 0
            #
            # for i, line in enumerate(t.readlines(include_tag=False)):
            #     tokens = [t for t in la.normalize(line)
            #         if re.search(r'[a-zA-Z]+', t, flags=re.UNICODE) is not None]
            #
            #     # print(tokens)
            #
            #     offset = token_idx + len(tokens)
            #
            #     correct = map(lambda x: ('FORM' in x[1] and x[0] == x[1]['FORM']) or x[0] == '',
            #                   zip(tokens, ref_tokens[token_idx:offset]))
            #
            #     if not all(correct):
            #         print(fname, i, line)
            #         print(ref_tokens[token_idx:offset])
            #         for j in range(len(tokens)):
            #             if tokens[j] != ref_tokens[token_idx + j]['FORM']:
            #                 print('{}->{}'.format(tokens[j], ref_tokens[token_idx + j]['FORM']))
            #
            #     assert all(correct)
            #
            #     token_idx = offset

    def test_tokenize(self, connection, latin_files, latin_tokens,
                      latin_word_frequencies):
        tessconn = TessMongoConnection('127.0.0.1', 27017, None, None)
        tessconn.connection = connection
        la = self.__test_class__(tessconn)

        for k in range(len(latin_files)):
            fname = latin_files[k]
            ref_tokens = [t for t in latin_tokens[k] if 'FORM' in t]
            ref_freqs = latin_word_frequencies[k]

            t = TessFile(fname, metadata=Text(language='latin'))

            tokens, frequencies = la.tokenize(t.read(), text=t.metadata)
            tokens = [t for t in tokens
                      if re.search(r'^[a-zA-Z]+$', t.display,
                      flags=re.UNICODE)]

            correct = map(lambda x: x[0].display == x[1]['DISPLAY'],
                          zip(tokens, ref_tokens))

            if not all(correct):
                print(fname)
                for j in range(len(tokens)):
                    if tokens[j].display != ref_tokens[j]['DISPLAY']:
                        print('{}->{}'.format(tokens[j].display, ref_tokens[j]['DISPLAY']))

            assert all(correct)

            correct = map(lambda x: ('FORM' in x[1] and x[0].form == x[1]['FORM']) or not x[0].form,
                          zip(tokens, ref_tokens))

            if not all(correct):
                print(fname)
                # for j in range(len(tokens)):
                #     if tokens[j].form != ref_tokens[j]['FORM']:
                #         print('{}->{}'.format(tokens[j].form, ref_tokens[j]['FORM']))

            assert all(correct)

            for key in ref_freqs:
                assert key in la.frequencies
                assert la.frequencies[key] == ref_freqs[key]

            diff = []
            for word in frequencies:
                if word.form not in ref_freqs and re.search(r'[a-zA-Z]', word.form, flags=re.UNICODE):
                    diff.append(word.form)
            print(diff)
            assert len(diff) == 0

            keys = sorted(list(ref_freqs.keys()))
            frequencies.sort(key=lambda x: x.form)
            correct = map(
                lambda x: x[0].form == x[1] and
                          x[0].frequency == ref_freqs[x[1]],
                zip(frequencies, keys))

            assert all(correct)

            la.clear()

            # token_idx = 0
            #
            # for i, line in enumerate(t.readlines(include_tag=False)):
            #     tokens, frequencies = la.tokenize(line)
            #     tokens = [t for t in tokens
            #               if re.search(r'^[a-zA-Z]+$', t.display,
            #                            flags=re.UNICODE)]
            #
            #     offset = token_idx + len(tokens)
            #     # print([(t.display, ref_tokens[i + token_idx]['DISPLAY']) for i, t in enumerate(tokens)])
            #
            #     correct = map(lambda x: x[0].display == x[1]['DISPLAY'],
            #                   zip(tokens, ref_tokens[token_idx:offset]))
            #
            #     if not all(correct):
            #         print(fname, i, line)
            #         for j in range(len(tokens)):
            #             if tokens[j].display != ref_tokens[token_idx + j]['DISPLAY']:
            #                 print('{}->{}'.format(tokens[j].display, ref_tokens[token_idx + j]['DISPLAY']))
            #
            #     assert all(correct)
            #
            #     correct = map(lambda x: ('FORM' in x[1] and x[0].form == x[1]['FORM']) or not x[0].form,
            #                   zip(tokens, ref_tokens[token_idx:offset]))
            #
            #     if not all(correct):
            #         print(fname, i, line)
            #         for j in range(len(tokens)):
            #             if tokens[j].form != ref_tokens[token_idx + j]['FORM']:
            #                 print('{}->{}'.format(tokens[j].form, ref_tokens[token_idx + j]['FORM']))
            #
            #     assert all(correct)
            #
            #     token_idx = offset
            #
            # la_tokens = [t for t in la.tokens
            #           if re.search(r'^[a-zA-Z]+$', t.display, flags=re.UNICODE)]
            #
            # correct = map(lambda x: x[0].display == x[1]['DISPLAY'],
            #               zip(la_tokens, ref_tokens))
            #
            # print(len(la_tokens), len(ref_tokens))
            #
            # if not all(correct):
            #     for j in range(len(la_tokens)):
            #         if tokens[j].display != ref_tokens[j]['DISPLAY']:
            #             print('{}->{}'.format(la_tokens[j].display, ref_tokens[token_idx + j]['DISPLAY']))
            #
            # assert all(correct)
            #
            # correct = map(lambda x: x[0].form == x[1]['FORM'],
            #               zip(la_tokens, ref_tokens))
            #
            # if not all(correct):
            #     for j in range(len(la_tokens)):
            #         if tokens[j].form != ref_tokens[j]['FORM']:
            #             print('{}->{}'.format(la_tokens[j].form, ref_tokens[token_idx + j]['FORM']))
            #
            # assert all(correct)
            #
            # for key in ref_freqs:
            #     assert key in la.frequencies
            #     assert la.frequencies[key] == ref_freqs[key]
            #
            # diff = []
            # for word in frequencies:
            #     if word.form not in ref_freqs and re.search(r'[a-zA-Z]', word.form, flags=re.UNICODE):
            #         diff.append(word.form)
            # print(diff)
            # assert len(diff) == 0
            #
            # keys = sorted(list(ref_freqs.keys()))
            # frequencies.sort(key=lambda x: x.form)
            # correct = map(
            #     lambda x: x[0].form == x[1] and
            #               x[0].frequency == ref_freqs[x[1]],
            #     zip(frequencies, keys))
            #
            # assert all(correct)
            #
            # la.clear()
