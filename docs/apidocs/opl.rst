opl package
===========

Module contents
---------------

.. automodule:: opl
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: opl.confluence._Page
    :members:
    :undoc-members:

Example IncQueryProject usage
*****************************
.. code-block:: python

    import opl

    opl.IncQueryProject(
        server='https://incquery.org.xyz',
        username=os.environ.get('INCQUERY_USERNAME'),
        password=os.environ.get('INCQUERY_PASSWORD'),
        org='example',
        project='demo',
        patterns={
            # mixin from opl basic queries
            **opl.patterns.basic,

            # simple, 'auto-named' pattern
            'propertyValue': '''
                (property: Property, value: java String) {
                    Property.defaultValue(property, propValue);
                    LiteralString.value(propValue, value);
                }
            ''',

            # more advanced, full pattern
            'predicateTarget': '''
                private incremental pattern predicateTarget(element: Class, predicateName: java String, target: Class) {
                    Class.ownedAttribute(element, predicate);
                    Property.name(predicate, predicateName);
                    Property.type(predicate, target);
                }
            ''',
        },
    )

