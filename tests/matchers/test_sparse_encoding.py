import copy
import csv
import os
import re
import time

import pytest

from tesserae.db import Feature, Match, MatchSet, Text, Token, Unit, \
                        TessMongoConnection
from tesserae.matchers.sparse_encoding import SparseMatrixSearch
from tesserae.tokenizers import LatinTokenizer
from tesserae.unitizer import Unitizer
from tesserae.utils import TessFile


@pytest.fixture(scope='module')
def search_connection(request):
    """Create a new TessMongoConnection for this task.

    Fixtures
    --------
    request
        The configuration to connect to the MongoDB test server.
    """
    conf = request.config
    conn = TessMongoConnection(conf.getoption('db_host'),
                               conf.getoption('db_port'),
                               conf.getoption('db_user'),
                               password=conf.getoption('db_passwd',
                                                       default=None),
                               db=conf.getoption('db_name',
                                                 default=None))
    return conn


@pytest.fixture(scope='module')
def populate_database(search_connection, test_data):
    """Set up the database to conduct searches on the test texts.

    Fixtures
    --------
    search_connection
        TessMongoConnection for search unit tests.
    test_data
        Example data for unit testing.
    """
    for text in test_data['texts']:
        tessfile = TessFile(text['path'], metadata=Text(**text))
        search_connection.insert(tessfile.metadata)
        if text['language'] == 'latin':
            tok = LatinTokenizer(search_connection)
        unitizer = Unitizer()
        tokens, tags, features = tok.tokenize(tessfile.read(), text=tessfile.metadata)
        print(features[0].json_encode())
        search_connection.update(features)
        lines, phrases = unitizer.unitize(tokens, tags, tessfile.metadata)
        search_connection.insert(lines + phrases)
        search_connection.insert(tokens)

    yield

    search_connection.connection['texts'].delete_many({})
    search_connection.connection['tokens'].delete_many({})
    #search_connection.connection['features'].delete_many({})
    search_connection.connection['units'].delete_many({})
    search_connection.connection['matches'].delete_many({})
    search_connection.connection['match_sets'].delete_many({})


@pytest.fixture(scope='module')
def search_tessfiles(search_connection, populate_database):
    """Select the texts to use in the searches.

    Fixtures
    --------
    search_connection
        TessMongoConnection for search unit tests.
    populate_database
        Set up the database to conduct searches on the test texts.
    """
    return search_connection.find('texts')


@pytest.fixture(scope='module')
def correct_results(tessfiles):
    """Tesserae v3 search results for the test texts.

    Fixtures
    --------
    tessfiles
        Path to the test .tess files.
    """
    correct_matches = []
    for root, dirs, files in os.walk(tessfiles):
        for fname in files:
            if os.path.splitext(fname)[1] == '.csv':
                results = {
                    'source': None,
                    'target': None,
                    'unit': None,
                    'feature': None,
                    'dibasis': None,
                    'matches': []
                }
                match_template = {
                    'result': None,
                    'target_locus': None,
                    'target_text': None,
                    'source_locus': None,
                    'source_text': None,
                    'shared': None,
                    'score': None
                }
                with open(os.path.join(root, fname), 'r') as f:
                    print(fname)
                    for k, line in enumerate(f.readlines()):
                        print(line)
                        if line[0] == '#' and 'source' in line:
                            start = line.find('=') + 1
                            results['source'] = line[start:].strip()
                        elif line[0] == '#' and 'target' in line:
                            start = line.find('=') + 1
                            results['target'] = line[start:].strip()
                        elif line[0] == '#' and 'unit' in line:
                            start = line.find('=') + 1
                            results['unit'] = line[start:].strip()
                        elif line[0] == '#' and 'feature' in line:
                            start = line.find('=') + 1
                            ftype = line[start:].strip()
                            results['feature'] = 'form' if ftype == 'word' else 'lemmata'
                        elif line[0] == '#' and 'dibasis' in line:
                            start = line.find('=') + 1
                            results['dibasis'] = line[start:].strip()
                        elif re.search(r'^[\d]', line[0]):
                            parts = re.split(r',"(?!,")', line)  # [p.strip('"').replace('*', '') for p in line.split(',"')]
                            parts = [p for p in parts if p]
                            print(parts)
                            this_match = copy.deepcopy(match_template)
                            this_match['result'] = int(parts[0])
                            this_match['target_locus'] = parts[1].split()[-1]
                            this_match['target_text'] = parts[2]
                            this_match['source_locus'] = parts[3].split()[-1]
                            this_match['source_text'] = parts[4]
                            this_match['shared'] = parts[5].split(',')[0].replace('-', ' ').replace(';', '').split()
                            this_match['shared'] = [s.strip('"') for s in this_match['shared']]
                            this_match['score'] = int(parts[5].split(',')[1])
                            results['matches'].append(this_match)
                correct_matches.append(results)
    return correct_matches


def lookup_entities(search_connection, match):
    units = search_connection.find(Unit.collection, _id=match.units)
    # features = search_connection.find(Feature.collection, id=match.tokens)
    match.units = units
    # match.tokens = features
    return match

def test_init(search_connection):
    engine = SparseMatrixSearch(search_connection)
    assert engine.connection is search_connection


def test_get_stoplist(search_connection):
    engine = SparseMatrixSearch(search_connection)


def test_create_stoplist(search_connection):
    engine = SparseMatrixSearch(search_connection)


def test_get_frequencies(search_connection):
    engine = SparseMatrixSearch(search_connection)


def test_match(search_connection, search_tessfiles, correct_results):
    engine = SparseMatrixSearch(search_connection)

    for result in correct_results:
        source = [t for t in search_tessfiles
                  if os.path.splitext(os.path.basename(t.path))[0] == result['source']][0]
        target = [t for t in search_tessfiles
                  if os.path.splitext(os.path.basename(t.path))[0] == result['target']][0]

        start = time.time()
        matches, ms = engine.match([source, target], result['unit'], result['feature'], stopwords=10,
                     stopword_basis='corpus', score_basis='word', distance_metric=result['dibasis'],
                     max_distance=50, min_score=6)
        print(time.time() - start)

        matches = [lookup_entities(search_connection, m) for m in matches]
        matches.sort(key=lambda x: x.score, reverse=True)

        # print(matches, result)
        # top_matches = [m for m in result['matches'] if m['score'] == 10]
        for i in range(len(matches)):
            predicted = matches[i]
            src = predicted.units[0].tags[0]
            tar = predicted.units[1].tags[0]
            correct = None

            # print(matches[i].units[0].tags, result['matches'][i]['source_locus'])
            # print(matches[i].units[0].tokens, result['matches'][i]['source_text'])
            # print(matches[i].units[1].tags, result['matches'][i]['target_locus'])
            # print(matches[i].units[1].tokens, result['matches'][i]['target_text'])
            # print([t.token for t in matches[i].tokens], result['matches'][i]['shared'])
            # print(matches[i].score, result['matches'][i]['score'])

            for m in result['matches']:
                if m['source_locus'] == src and m['target_locus'] == tar:
                    correct = m
                    break
            # print([t.token for t in predicted.tokens], correct)
            assert correct is not None, "No matching v3 result found."
            assert src == correct['source_locus']

            assert all(map(lambda x: x.token in correct['shared'], predicted.tokens))
