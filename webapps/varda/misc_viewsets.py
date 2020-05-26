"""
Validation functionality specifically for viewsets.
The functions here are built around an error dictionary.

All validation errors are added to the dictionary for field-specific key, as an array.
After all validations are done, there can be multiple fields and errors per field in
the error dictionary.

The error dictionary itself is a context manager, making it easy to use and not forget
to throw the potential validation errors:

>>> with ViewSetValidator() as validator:
>>>     if condition:
>>>         validator.error('some_field', 'Some message.')
"""
from rest_framework.exceptions import ValidationError


class ViewSetValidator:
    def __init__(self):
        self.messages = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if self.messages:
                raise ValidationError(self.messages, code='invalid')

    def error(self, key, message):
        """
        A helper function to add a validation error to the given dictionary.
        The values of the dictionary are expected to be arrays.
        If a key already exists, the error is appended to the list.

        :param msgs: Error dictionary
        :param key: Dictionary key
        :param message: Validation error text
        """

        arr = self.messages[key] = self.messages.get(key, [])
        arr.append(message)

    def errors(self, detail):
        """
        Like error, but the parameter can be a dict or a list.

        :param detail: errors as dict or list
        """

        if isinstance(detail, list):
            for msg in detail:
                # No key, just use something
                self.error('detail', msg)
        else:
            for key, msgs in detail.items():
                for msg in msgs:
                    self.error(key, msg)

    def wrap(self):
        """
        Returns a context handler that catches a ValidationError and
        adds its contents to the error dictionary.

        >>> with validator.wrap():
        >>>     raise ValidationError('foo')
        >>> with validator.wrap():
        >>>     raise ValidationError({'key': 'bar'})
        """

        return ValidationErrorWrapper(self)


class ValidationErrorWrapper:
    def __init__(self, validator):
        self.validator = validator

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ValidationError:
            self.validator.errors(exc_val.detail)
            return True
