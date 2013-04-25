# Copyright 2013 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import unittest2

import urltree


class TestPathSplit(unittest2.TestCase):
    def test_path_split_notrail(self):
        url = "///root//elem1/elem2////"

        result = list(urltree._path_split(url))

        self.assertEqual(result, ['root', 'elem1', 'elem2'])

    def test_path_split_withtrail(self):
        url = "///root//elem1/elem2"

        result = list(urltree._path_split(url))

        self.assertEqual(result, ['root', 'elem1', 'elem2'])

    def test_path_split_unrooted(self):
        url = "root/elem1/elem2"

        result = list(urltree._path_split(url))

        self.assertEqual(result, ['root', 'elem1', 'elem2'])


class TestMethodDict(unittest2.TestCase):
    def test_init(self):
        mdict = urltree.MethodDict()

        self.assertEqual(mdict.default, None)

    def test_with_key(self):
        mdict = urltree.MethodDict()
        mdict['GET'] = 'method'

        self.assertEqual(mdict['GET'], 'method')

    def test_no_default(self):
        mdict = urltree.MethodDict()
        mdict['GET'] = 'method'

        self.assertEqual(mdict['POST'], None)

    def test_with_default(self):
        mdict = urltree.MethodDict()
        mdict['GET'] = 'method'
        mdict.default = 'default'

        self.assertEqual(mdict['POST'], 'default')


class TestURLNode(unittest2.TestCase):
    def test_init(self):
        node = urltree.URLNode()

        self.assertEqual(node._children, {})
        self.assertEqual(node._variables, {})
        self.assertEqual(node._defaults, [])
        self.assertEqual(node._dest, {})
        self.assertTrue(isinstance(node._dest, urltree.MethodDict))

    @mock.patch.object(urltree, 'URLVarNode')
    def test_get_var_child_exists(self, mock_URLVarNode):
        node = urltree.URLNode()
        node._variables['spam'] = mock.Mock(_restrict='restrict')

        child = node._get_var_child('spam', 'restrict')

        self.assertEqual(child, node._variables['spam'])
        self.assertFalse(mock_URLVarNode.called)

    @mock.patch.object(urltree, 'URLVarNode')
    def test_get_var_child_exists_badrestrict(self, mock_URLVarNode):
        node = urltree.URLNode()
        node._variables['spam'] = mock.Mock(_restrict='restrict')

        self.assertRaises(NameError, node._get_var_child, 'spam', 'other')

        self.assertFalse(mock_URLVarNode.called)

    @mock.patch.object(urltree, 'URLVarNode')
    def test_get_var_child_noexist_sharedrestrict(self, mock_URLVarNode):
        node = urltree.URLNode()
        node._defaults = [
            mock.Mock(_restrict='other'),
            mock.Mock(_restrict='restrict'),
        ]

        self.assertRaises(NameError, node._get_var_child, 'spam', 'restrict')

        self.assertFalse(mock_URLVarNode.called)

    @mock.patch.object(urltree, 'URLVarNode', return_value='new_node')
    def test_get_var_child_noexist_norestrict(self, mock_URLVarNode):
        node = urltree.URLNode()
        defaults = [
            mock.Mock(_restrict='other'),
            mock.Mock(_restrict='restrict'),
        ]
        node._defaults = defaults[:]

        child = node._get_var_child('spam', None)

        self.assertEqual(child, 'new_node')
        self.assertEqual(node._variables, dict(spam='new_node'))
        self.assertEqual(node._defaults, [
            defaults[0],
            defaults[1],
            'new_node',
        ])
        mock_URLVarNode.assert_called_once_with('spam', None)

    @mock.patch.object(urltree, 'URLVarNode', return_value='new_node')
    def test_get_var_child_noexist_nodefaults(self, mock_URLVarNode):
        node = urltree.URLNode()

        child = node._get_var_child('spam', 'restrict')

        self.assertEqual(child, 'new_node')
        self.assertEqual(node._variables, dict(spam='new_node'))
        self.assertEqual(node._defaults, ['new_node'])
        mock_URLVarNode.assert_called_once_with('spam', 'restrict')

    @mock.patch.object(urltree, 'URLVarNode', return_value='new_node')
    def test_get_var_child_noexist_noemptyrestrict(self, mock_URLVarNode):
        node = urltree.URLNode()
        defaults = [
            mock.Mock(_restrict='other'),
        ]
        node._defaults = defaults[:]

        child = node._get_var_child('spam', 'restrict')

        self.assertEqual(child, 'new_node')
        self.assertEqual(node._variables, dict(spam='new_node'))
        self.assertEqual(node._defaults, [
            defaults[0],
            'new_node',
        ])
        mock_URLVarNode.assert_called_once_with('spam', 'restrict')

    @mock.patch.object(urltree, 'URLVarNode', return_value='new_node')
    def test_get_var_child_noexist_withemptyrestrict(self, mock_URLVarNode):
        node = urltree.URLNode()
        defaults = [
            mock.Mock(_restrict='other'),
            mock.Mock(_restrict=None),
        ]
        node._defaults = defaults[:]

        child = node._get_var_child('spam', 'restrict')

        self.assertEqual(child, 'new_node')
        self.assertEqual(node._variables, dict(spam='new_node'))
        self.assertEqual(node._defaults, [
            defaults[0],
            'new_node',
            defaults[1],
        ])
        mock_URLVarNode.assert_called_once_with('spam', 'restrict')

    def test_get_child_exists(self):
        node = urltree.URLNode()
        node._children = dict(spam='fakechild')

        with mock.patch.object(urltree, 'URLNode') as mock_URLNode:
            result = node._get_child('spam')

        self.assertEqual(result, 'fakechild')
        self.assertFalse(mock_URLNode.called)

    def test_get_child_noexist(self):
        node = urltree.URLNode()

        with mock.patch.object(urltree, 'URLNode',
                               return_value='fakechild') as mock_URLNode:
            result = node._get_child('spam')

        self.assertEqual(result, 'fakechild')
        mock_URLNode.assert_called_once_with()

    def test_resolve_child_exact_match(self):
        node = urltree.URLNode()
        child = mock.Mock(**{'_match.return_value': True})
        node._children['spam'] = child

        result = node._resolve_child('spam', 'params')

        self.assertEqual(result, child)
        child._match.assert_called_once_with('spam', 'params')

    def test_resolve_child_exact_mismatch(self):
        node = urltree.URLNode()
        child = mock.Mock(**{'_match.return_value': False})
        node._children['spam'] = child

        result = node._resolve_child('spam', 'params')

        self.assertEqual(result, None)
        child._match.assert_called_once_with('spam', 'params')

    def test_resolve_child_default_match(self):
        node = urltree.URLNode()
        node._defaults = [
            mock.Mock(**{'_match.return_value': False}),
            mock.Mock(**{'_match.return_value': True}),
            mock.Mock(**{'_match.return_value': True}),
        ]

        result = node._resolve_child('spam', 'params')

        self.assertEqual(result, node._defaults[1])
        node._defaults[0]._match.assert_called_once_with('spam', 'params')
        node._defaults[1]._match.assert_called_once_with('spam', 'params')
        self.assertFalse(node._defaults[2]._match.called)

    def test_resolve_child_default_mismatch(self):
        node = urltree.URLNode()
        node._defaults = [
            mock.Mock(**{'_match.return_value': False}),
            mock.Mock(**{'_match.return_value': False}),
            mock.Mock(**{'_match.return_value': False}),
        ]

        result = node._resolve_child('spam', 'params')

        self.assertEqual(result, None)
        node._defaults[0]._match.assert_called_once_with('spam', 'params')
        node._defaults[1]._match.assert_called_once_with('spam', 'params')
        node._defaults[2]._match.assert_called_once_with('spam', 'params')

    def test_resolve_child_full(self):
        node = urltree.URLNode()
        node._defaults = [
            mock.Mock(**{'_match.return_value': False}),
            mock.Mock(**{'_match.return_value': True}),
            mock.Mock(**{'_match.return_value': True}),
        ]
        node._children['spam'] = mock.Mock(**{'_match.return_value': False})

        result = node._resolve_child('spam', 'params')

        self.assertEqual(result, node._defaults[1])
        node._children['spam']._match.assert_called_once_with('spam', 'params')
        node._defaults[0]._match.assert_called_once_with('spam', 'params')
        node._defaults[1]._match.assert_called_once_with('spam', 'params')
        self.assertFalse(node._defaults[2]._match.called)

    def test_match(self):
        node = urltree.URLNode()

        result = node._match('elem', 'params')

        self.assertEqual(result, True)


class TestURLVarNode(unittest2.TestCase):
    @mock.patch('re.compile', return_value='compiled_pattern')
    def test_init_restrict_none(self, mock_compile):
        node = urltree.URLVarNode('spam', None)

        self.assertEqual(node._name, 'spam')
        self.assertEqual(node._restrict, None)
        self.assertEqual(node._pattern, None)
        self.assertFalse(mock_compile.called)

    @mock.patch('re.compile', return_value='compiled_pattern')
    def test_init_restrict_callable(self, mock_compile):
        restrict = lambda x: x
        node = urltree.URLVarNode('spam', restrict)

        self.assertEqual(node._name, 'spam')
        self.assertEqual(node._restrict, restrict)
        self.assertEqual(node._pattern, None)
        self.assertFalse(mock_compile.called)

    @mock.patch('re.compile', return_value='compiled_pattern')
    def test_init_restrict_string_unanchored(self, mock_compile):
        node = urltree.URLVarNode('spam', 'pattern')

        self.assertEqual(node._name, 'spam')
        self.assertEqual(node._restrict, 'pattern')
        self.assertEqual(node._pattern, 'compiled_pattern')
        mock_compile.assert_called_once_with('pattern$')

    @mock.patch('re.compile', return_value='compiled_pattern')
    def test_init_restrict_string_anchored(self, mock_compile):
        node = urltree.URLVarNode('spam', 'pattern$')

        self.assertEqual(node._name, 'spam')
        self.assertEqual(node._restrict, 'pattern$')
        self.assertEqual(node._pattern, 'compiled_pattern')
        mock_compile.assert_called_once_with('pattern$')

    def test_match_restrict_none(self):
        node = urltree.URLVarNode('spam', None)
        params = {}

        result = node._match('element', params)

        self.assertEqual(result, True)
        self.assertEqual(params, dict(spam='element'))

    def test_match_restrict_pattern_mismatch(self):
        node = urltree.URLVarNode('spam', None)
        node._pattern = mock.Mock(**{'match.return_value': None})
        params = {}

        result = node._match('element', params)

        self.assertEqual(result, False)
        self.assertEqual(params, {})
        node._pattern.match.assert_called_once_with('element')

    def test_match_restrict_pattern_match(self):
        node = urltree.URLVarNode('spam', None)
        node._pattern = mock.Mock(**{'match.return_value': 'match obj'})
        params = {}

        result = node._match('element', params)

        self.assertEqual(result, True)
        self.assertEqual(params, dict(spam='match obj'))
        node._pattern.match.assert_called_once_with('element')

    def test_match_restrict_callable_mismatch(self):
        node = urltree.URLVarNode('spam', None)
        node._restrict = mock.Mock(side_effect=ValueError)
        params = {}

        result = node._match('element', params)

        self.assertEqual(result, False)
        self.assertEqual(params, {})
        node._restrict.assert_called_once_with('element')

    def test_match_restrict_callable_match(self):
        node = urltree.URLVarNode('spam', None)
        node._restrict = mock.Mock(return_value='result')
        params = {}

        result = node._match('element', params)

        self.assertEqual(result, True)
        self.assertEqual(params, dict(spam='result'))
        node._restrict.assert_called_once_with('element')


class TestURLTree(unittest2.TestCase):
    def test_route_noargs(self):
        tree = urltree.URLTree()

        self.assertRaises(TypeError, tree.route)

    def test_route_onearg(self):
        tree = urltree.URLTree()

        self.assertRaises(TypeError, tree.route, '/')

    def test_route_slash(self):
        tree = urltree.URLTree()

        result = tree.route('/', 'dest')

        self.assertEqual(result, set())
        self.assertEqual(tree._dest, {})
        self.assertEqual(tree._dest.default, 'dest')

    def test_route_slash_methods(self):
        tree = urltree.URLTree()

        result = tree.route('/', 'dest', 'get', 'post')

        self.assertEqual(result, set())
        self.assertEqual(tree._dest, dict(GET='dest', POST='dest'))
        self.assertEqual(tree._dest.default, None)

    def test_route_nonvariable(self):
        tree = urltree.URLTree()

        result1 = tree.route('/elem1/elem2/elem3', 'dest', 'get')
        result2 = tree.route('/elem1/elem2/elem4', 'dest', 'get')

        self.assertEqual(result1, set())
        self.assertEqual(result2, set())

        self.assertEqual(tree._dest, {})
        self.assertEqual(tree._dest.default, None)
        self.assertTrue('elem1' in tree._children)
        self.assertEqual(tree._variables, {})

        elem1 = tree._children['elem1']
        self.assertEqual(elem1._dest, {})
        self.assertEqual(elem1._dest.default, None)
        self.assertTrue('elem2' in elem1._children)
        self.assertEqual(elem1._variables, {})

        elem2 = elem1._children['elem2']
        self.assertEqual(elem2._dest, {})
        self.assertEqual(elem2._dest.default, None)
        self.assertTrue('elem3' in elem2._children)
        self.assertTrue('elem4' in elem2._children)
        self.assertEqual(elem2._variables, {})

        elem3 = elem2._children['elem3']
        self.assertEqual(elem3._dest, dict(GET='dest'))
        self.assertEqual(elem3._dest.default, None)
        self.assertEqual(elem3._children, {})
        self.assertEqual(elem3._variables, {})

        elem4 = elem2._children['elem4']
        self.assertEqual(elem4._dest, dict(GET='dest'))
        self.assertEqual(elem4._dest.default, None)
        self.assertEqual(elem4._children, {})
        self.assertEqual(elem4._variables, {})

    def test_route_variable_duplicates(self):
        tree = urltree.URLTree()

        self.assertRaises(NameError, tree.route,
                          '/elem1/{var1}/elem2/{var1}', 'dest')

    def test_route_variable_noduplicates(self):
        tree = urltree.URLTree()

        result1 = tree.route('/elem1/{var1}/elem2/{var2}', 'dest', 'get')
        result2 = tree.route('/elem1/{var1}/elem3/{var3}', 'dest', 'get')

        self.assertEqual(result1, set(['var1', 'var2']))
        self.assertEqual(result2, set(['var1', 'var3']))

        self.assertEqual(tree._dest, {})
        self.assertEqual(tree._dest.default, None)
        self.assertTrue('elem1' in tree._children)
        self.assertEqual(tree._variables, {})

        elem1 = tree._children['elem1']
        self.assertEqual(elem1._dest, {})
        self.assertEqual(elem1._dest.default, None)
        self.assertEqual(elem1._children, {})
        self.assertTrue('var1' in elem1._variables)

        var1 = elem1._variables['var1']
        self.assertEqual(var1._dest, {})
        self.assertEqual(var1._dest.default, None)
        self.assertTrue('elem2' in var1._children)
        self.assertTrue('elem3' in var1._children)
        self.assertEqual(var1._variables, {})

        elem2 = var1._children['elem2']
        self.assertEqual(elem2._dest, {})
        self.assertEqual(elem2._dest.default, None)
        self.assertEqual(elem2._children, {})
        self.assertTrue('var2' in elem2._variables)

        var2 = elem2._variables['var2']
        self.assertEqual(var2._dest, dict(GET='dest'))
        self.assertEqual(var2._dest.default, None)
        self.assertEqual(var2._children, {})
        self.assertEqual(var2._variables, {})

        elem3 = var1._children['elem3']
        self.assertEqual(elem3._dest, {})
        self.assertEqual(elem3._dest.default, None)
        self.assertEqual(elem3._children, {})
        self.assertTrue('var3' in elem3._variables)

        var3 = elem3._variables['var3']
        self.assertEqual(var3._dest, dict(GET='dest'))
        self.assertEqual(var3._dest.default, None)
        self.assertEqual(var3._children, {})
        self.assertEqual(var3._variables, {})

    def test_resolve_exact_dest(self):
        tree = urltree.URLTree()
        tree.route('/elem1/elem2', 'dest', 'get')

        dest, params = tree.resolve('get', '/elem1/elem2')

        self.assertEqual(dest, 'dest')
        self.assertEqual(params, {})

    def test_resolve_exact_nodest(self):
        tree = urltree.URLTree()
        tree.route('/elem1/elem2', 'dest', 'get')

        dest, params = tree.resolve('post', '/elem1/elem2')

        self.assertEqual(dest, None)
        self.assertEqual(params, None)

    def test_resolve_tail_dest(self):
        tree = urltree.URLTree()
        tree.route('/elem1/elem2', 'dest', 'get')

        dest, params = tree.resolve('get', '/elem1/elem2/elem3/elem4')

        self.assertEqual(dest, 'dest')
        self.assertEqual(params, dict(path_info='elem3/elem4'))

    def test_resolve_tail_nodest(self):
        tree = urltree.URLTree()
        tree.route('/elem1/elem2', 'dest', 'get')

        dest, params = tree.resolve('post', '/elem1/elem2/elem3/elem4')

        self.assertEqual(dest, None)
        self.assertEqual(params, None)

    def test_resolve_root_noroute(self):
        tree = urltree.URLTree()

        dest, params = tree.resolve('get', '/')

        self.assertEqual(dest, None)
        self.assertEqual(params, None)

    def test_resolve_root_withroute(self):
        tree = urltree.URLTree()
        tree.route('/', 'dest')

        dest, params = tree.resolve('get', '/')

        self.assertEqual(dest, 'dest')
        self.assertEqual(params, {})

    def test_resolve_root_withroute_tail(self):
        tree = urltree.URLTree()
        tree.route('/', 'dest')

        dest, params = tree.resolve('get', '/elem1/elem2')

        self.assertEqual(dest, 'dest')
        self.assertEqual(params, dict(path_info='elem1/elem2'))
