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

"""
Provides a tree-based URL route resolver called ``URLTree``.  A URL
route is broken down into its path elements and a tree of nodes is
constructed from those elements to represent the route.  This provides
ultra high URL resolution efficiency in the face of large numbers of
routes, since, unlike other systems like Routes, ``URLTree`` does not
match on a list of regular expressions.

The URL syntax is similar to that used in Routes; constant parts of
the URL are represented by plain text, and variable parts are
delimited by braces ("{}"); the text inside the braces specifies the
name of the variable that will be computed from the replacement.  Each
such variable part corresponds to a single slash-delimited part of the
path; unlike Routes, it is not possible for one variable block to
cover only a portion of the URL path element, or to cover multiple URL
path elements.

When constructing the route, it is possible to apply restrictions to
what a variable element can match; these restrictions are passed as
keyword arguments to the ``URLTree.route()`` method.  The value of the
keyword argument may be a string--which will be interpreted as a
regular expression--or a function--which may raise a ``ValueError`` to
indicate a failure to match.  In the first case, the parameter value
will be the regular expression match object--allowing access to
parenthesized groups, for instance--and in the second case, the
parameter value will be the return value of the function.  If no
restrictions are specified, the matched element text will be used as
the value of the parameter.

Note that, because individual routes are not independent, all
variables with the same name at the same level MUST have the same
restriction, and that all variables with the same restriction at the
same level MUST have the same name.  If multiple variables exist at a
given level, the ones with restrictions will be processed first, in
the order in which they were added; the variable with no restrictions
specified, if any, will be checked last.
"""

import re


__all__ = ['URLTree']


def _path_split(path):
    """
    Split up a URL path into its component elements.  Repeated slashes
    are skipped, and no indication is given if there is a trailing
    slash.  Also, the root element ('/') is not included.

    :param path: The URL path to split.

    :returns: An iterator which iterates over all the elements of the
              path.
    """

    # Initialize the state
    start = None
    slash = True

    # Walk through the path
    for idx, char in enumerate(path):
        if char == '/':
            if not slash:
                # We hit the next slash, so yield the path element and
                # reset
                yield path[start:idx]
                start = None

                # Ignore repeated slashes
                slash = True
        elif start is None:
            # Found the start of a path element
            start = idx
            slash = False

    if start is not None:
        # Make sure to yield the last element
        yield path[start:]


class MethodDict(dict):
    """
    A ``dict`` subclass with dynamic default for unset elements.
    Instances of this class are used for storing the
    destination-per-method for a given URL route.
    """

    def __init__(self):
        """
        Initialize a ``MethodDict``.  Sets up the default value which
        will be returned when no element has been defined.
        """

        super(MethodDict, self).__init__()

        self.default = None

    def __missing__(self, key):
        """
        Fill in missing keys.

        :param key: The key that couldn't be found.

        :returns: The defined default.
        """

        return self.default


class URLNode(object):
    """
    Base class for URL nodes.  Represents a single element of the URL
    to be resolved.
    """

    def __init__(self):
        """
        Initialize a ``URLNode``.
        """

        self._children = {}
        self._variables = {}
        self._defaults = []
        self._dest = MethodDict()

    def _get_var_child(self, name, restrict):
        """
        Get the variable node that's a child of this node, creating it
        with the given name if necessary.

        :param name: The name that will be used to represent the value
                     in the parameters.
        :param restrict: Restrictions on whether this parameter will
                         match.

        :returns: The desired variable node.
        """

        if name in self._variables:
            node = self._variables[name]
            if node._restrict != restrict:
                # Complain about the mismatch
                raise NameError("variable node %r restriction mismatch")
        else:
            # Check for matching restrictions
            for chk_node in self._defaults:
                if chk_node._restrict == restrict:
                    # Complain about the mismatch
                    raise NameError("variable node name mismatch: %s != %s" %
                                    (name, chk_node._name))

            # Create new variable node
            node = URLVarNode(name, restrict)
            self._variables[name] = node

            # Insert it into the appropriate place.  We want variable
            # nodes with no set restrict to always be at the end,
            # which is the reason for the complicated append
            # vs. insert logic here...
            if (restrict is None or not self._defaults or
                    self._defaults[-1]._restrict is not None):
                self._defaults.append(node)
            else:
                self._defaults.insert(-1, node)

        return node

    def _get_child(self, elem):
        """
        Get the element node that's a child of this node and has the
        given name, creating it if necessary.

        :param elem: The path element the node will be stored under.

        :returns: The desired node.
        """

        # Create the element if necessary
        if elem not in self._children:
            self._children[elem] = URLNode()

        return self._children[elem]

    def _resolve_child(self, elem, params):
        """
        Look up the appropriate child element for the given next URL
        element.

        :param elem: The path element.
        :param params: A dictionary of parameters that is developed
                       from the URL.

        :returns: The appropriate child element, or ``None`` if the
                  child cannot be found.
        """

        # Handle the case of an exact match first
        if (elem in self._children and
                self._children[elem]._match(elem, params)):
            return self._children[elem]

        # OK, check on the default elements
        for node in self._defaults:
            if node._match(elem, params):
                return node

        # No matching child, then
        return None

    def _match(self, elem, params):
        """
        Check if the element actually matches this node.

        :params elem: The path element.
        :param params: A dictionary of parameters that is developed
                       from the URL.

        :returns: ``True`` if the element matches, ``False``
                  otherwise.
        """

        return True


class URLVarNode(URLNode):
    """
    Represent a variable node in the URL tree.  Variable nodes have a
    name; the URL element which matches a variable node will be
    assigned to that name in the parameters dictionary during the URL
    resolution process.
    """

    def __init__(self, name, restrict):
        """
        Initialize a ``URLVarNode``.

        :param name: The name of the variable.
        """

        super(URLVarNode, self).__init__()
        self._name = name
        self._restrict = restrict
        self._pattern = None

        # Compile the pattern
        if isinstance(restrict, basestring):
            # Anchor the end of the pattern
            if restrict[-1:] != '$':
                restrict += '$'

            self._pattern = re.compile(restrict)

    def _match(self, elem, params):
        """
        Check if the element actually matches this node.  Additionally
        adds the element to the parameters dictionary in the correct
        location.

        :params elem: The path element.
        :param params: A dictionary of parameters that is developed
                       from the URL.

        :returns: ``True`` if the element matches, ``False``
                  otherwise.
        """

        # If we have a pattern, try the match
        if self._pattern is not None:
            elem = self._pattern.match(elem)
            if elem is None:
                return False
        elif self._restrict is not None:
            try:
                # Call the restriction function
                elem = self._restrict(elem)
            except ValueError:
                # Failed to convert it...
                return False

        # Save the value
        params[self._name] = elem
        return True


class URLTree(URLNode):
    """
    The URL tree.  Routes are added with the ``route()`` method, and
    URLs are resolved using the ``resolve()`` method.
    """

    def route(self, *methods, **restrictions):
        """
        Add a route to the tree.  Takes two required positional
        arguments--the URL pattern for the route to match on, and the
        destination for the route.  Remaining positional arguments are
        interpreted as HTTP methods for the route to match on--if none
        are given, the route will match on all HTTP methods.  (Note
        that methods are treated case insensitively.)  Keyword
        arguments specify any restrictions on the parameters; if a
        restriction is a string, it is interpreted as a regular
        expression which the value must match, and the match object
        will be the value of the parameter (allowing access to, e.g.,
        parenthesized groups).  If, on the other hand, the restriction
        is a function, that function will be called, and its return
        value will become the value of the parameter; the function may
        raise ``ValueError`` to indicate a mismatch.

        Note that destinations may be any value; they are simply
        returned when the route matches in ``resolve()``.

        :returns: A set of the parameter names defined in the URL
                  pattern.
        """

        if len(methods) < 2:
            raise TypeError("route() takes at least 2 arguments (%d given)" %
                            len(methods))

        url, dest = methods[:2]

        node = self
        params = set()

        # Iterate over the URI path elements
        for elem in _path_split(url):
            if (elem[:1], elem[-1:]) == ('{', '}'):
                name = elem[1:-1]

                # Check for duplicates
                if name in params:
                    raise NameError("duplicate parameter name %r" % name)

                node = node._get_var_child(name, restrictions.get(name))
                params.add(name)
            else:
                node = node._get_child(elem)

        # Store the destination under the appropriate HTTP method(s)
        if len(methods) > 2:
            for method in methods[2:]:
                node._dest[method.upper()] = dest
        else:
            node._dest.default = dest

        return params

    def resolve(self, method, url):
        """
        Given an HTTP method and a URL, resolve the routes to
        determine the appropriate destination and the parameters.

        Note that if the path tree is resolved but there are
        remaining, unconsumed path elements, those elements will be
        placed into the special parameter ``path_info``.

        :param method: The HTTP method of the request.
        :param url: The URL of the request.

        :returns: A tuple of the destination and a dictionary of
                  parameters.  If the destination could not be
                  resolved (tests as ``False``), the tuple will be
                  ``(None, None)``.
        """

        params = {}
        node = self
        path_iter = _path_split(url)

        # Iterate over the URL finding the next nodes
        for elem in path_iter:
            next = node._resolve_child(elem, params)
            if next is None:
                break
            node = next
        else:
            path_iter = None

        # Build the path info
        if path_iter is not None:
            params['path_info'] = '/'.join([elem] + list(path_iter))

        dest = node._dest[method.upper()]
        if not dest:
            return None, None

        return dest, params
