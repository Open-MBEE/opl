
'''
A dictionary of VQL pattern groups provided for basic query functionality
'''
patterns = {
    'basic': {
        # fetch the literal string value of an owned attribute
        'attributeStringValue': '''
            (owner, attrName, value) {
                Class.ownedAttribute(owner, property);
                Property.name(property, attrName);
                Property.defaultValue(property, defaultValue);
                LiteralString.value(defaultValue, value);
            }
        ''',

        # fetch all literal string values in the array of an owned attribute
        'attributeStringArray': '''
            (owner, attrName, value) {
                Class.ownedAttribute(owner, property);
                Property.name(property, attrName);
                Property.defaultValue(property, defaultValue);
                Expression.operand(defaultValue, expr);
                LiteralString.value(expr, value);
            }
        ''',

        # returns all artifacts relationships
        'predicateTarget': '''
            (element : Class, target : Class, predicate : Property, predicateName : String, elementName : String, targetName : String) {
                Class.name(element, elementName);
                Class.ownedAttribute(element, predicate);
                Property.name(predicate, predicateName);
                Property.type(predicate, target);              
                Class.name(target, targetName);
            }
        ''',

        # get all literal string property values of an artifact
        'propertyValue': '''
            (artifact: Class, artifactName: String, property : Property, propertyName: String, value: String) {
                Class.name(artifact, artifactName);             
                Class.ownedAttribute(artifact, property);
                Property.name(property, propertyName);
                Property.defaultValue(property, propValue);    
                LiteralString.value(propValue, value);
            }
        '''
    }
}
