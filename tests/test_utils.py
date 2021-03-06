import unittest2 as unittest

from fabricio.utils import Options, OrderedDict


class OptionsTestCase(unittest.TestCase):

    def test_str_version(self):
        cases = dict(
            # TODO all values must be quoted
            empty_options_list=dict(
                options=OrderedDict(),
                expected_str_version='',
            ),
            with_underscore=dict(
                options=OrderedDict(foo_baz='bar'),
                expected_str_version='--foo_baz bar',
            ),
            multiword=dict(
                options=OrderedDict(foo='bar baz'),
                expected_str_version='--foo "bar baz"',
            ),
            empty=dict(
                options=OrderedDict(foo=''),
                expected_str_version='--foo ""',
            ),
            with_single_quotes=dict(
                options=OrderedDict(foo="'bar'"),
                expected_str_version='--foo "\'bar\'"',
            ),
            with_double_quotes=dict(
                options=OrderedDict(foo='"bar"'),
                expected_str_version='--foo "\\"bar\\""',
            ),
            with_quotes_and_spaces=dict(
                options=OrderedDict(foo='"bar" \'baz\''),
                expected_str_version='--foo "\\"bar\\" \'baz\'"',
            ),
            single_length=dict(
                options=OrderedDict(foo='bar'),
                expected_str_version='--foo bar',
            ),
            integer=dict(
                options=OrderedDict(foo=42),
                expected_str_version='--foo 42',
            ),
            triple_length=dict(
                options=OrderedDict([
                    ('foo', 'foo'),
                    ('bar', 'bar'),
                    ('baz', 'baz'),
                ]),
                expected_str_version='--foo foo --bar bar --baz baz',
            ),
            multi_value=dict(
                options=OrderedDict(foo=['bar', 'baz']),
                expected_str_version='--foo bar --foo baz',
            ),
            boolean_values=dict(
                options=OrderedDict(foo=True, bar=False),
                expected_str_version='--foo',
            ),
            mix=dict(
                options=OrderedDict([
                    ('foo', 'foo'),
                    ('bar', True),
                    ('baz', ['1', 'a']),
                ]),
                expected_str_version='--foo foo --bar --baz 1 --baz a',
            ),
            # TODO empty value
            # TODO escaped value
        )
        for case, params in cases.items():
            with self.subTest(case=case):
                options = Options(params['options'])
                expected_str_version = params['expected_str_version']
                self.assertEqual(expected_str_version, str(options))
