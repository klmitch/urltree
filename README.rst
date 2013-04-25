======================
``URLTree`` URL Router
======================

This package provides a tree-oriented URL router.  Most URL routers
operate by matching a URL against a list of regular expressions until
they find one that matches, but this has obvious performance penalties
if there are many routes.  ``URLTree`` is different; routes are stored
as a tree, and matching a URL against the set of routes is equivalent
to traversing the tree.

The ``URLTree`` router supports parameters, and even allows parameter
values to be matched against regular expressions or converted by
functions.  Moreover, as long as these "restrictions" and the variable
names are different, several of these parameters can be declared at
the same level of a URL tree; this allows a URL with, say, an integer
in one location to be mapped to one destination, while a second URL
with non-integer values in that same location may be mapped to another
destination.

To use ``URLTree``, allocate a ``URLTree`` object and use the
``URLTree.route()`` method to map a URL pattern to a destination, like
so::

    mapper = URLTree()
    mapper.route("/article", list_articles, "get")
    mapper.route("/article", create_article, "post")
    mapper.route("/article/{id}", get_article, "get", id=int)
    mapper.route("/article/{id}", update_article, "put", id=int)
    mapper.route("/article/{id}", delete_article, "delete", id=int)

Upon receiving a request, the destination and the parameters can be
retrieved using the ``URLTree.resolve()`` method, like so::

    # "req.method" is the HTTP method, and "req.url" is the requested
    # URL
    dest, params = mapper.resolve(req.method, req.url)

Note that ``URLTree`` does not interpret the destination; the examples
above use callables, but anything can be used here.
