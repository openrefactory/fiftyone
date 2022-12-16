"""
Dataset sample fields.

| Copyright 2017-2022, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
from copy import deepcopy
from datetime import date, datetime
import numbers

from bson import ObjectId, SON
from bson.binary import Binary
import mongoengine.fields
import numpy as np
import pytz

import eta.core.utils as etau

import fiftyone.core.expressions as foe
import fiftyone.core.frame_utils as fofu
import fiftyone.core.odm as foo
import fiftyone.core.utils as fou


def validate_type_constraints(
    ftype=None, embedded_doc_type=None, virtual=None
):
    """Validates the given type constraints.

    Args:
        ftype (None): an optional field type or iterable of types to enforce.
            Must be subclass(es) of :class:`Field`
        embedded_doc_type (None): an optional embedded document type or
            iterable of types to enforce. Must be subclass(es) of
            :class:`fiftyone.core.odm.BaseEmbeddedDocument`
        virtual (None): an optional virtual type (True or False) to enforce

    Returns:
        True/False whether any constraints were provided

    Raises:
        ValueError: if the constraints are not valid
    """
    has_contraints = False

    if ftype is not None:
        has_contraints = True

        if etau.is_container(ftype):
            ftype = tuple(ftype)
        else:
            ftype = (ftype,)

        for _ftype in ftype:
            if not issubclass(_ftype, Field):
                raise ValueError(
                    "Field type %s is not a subclass of %s" % (_ftype, Field)
                )

            if embedded_doc_type is not None and not issubclass(
                _ftype, EmbeddedDocumentField
            ):
                raise ValueError(
                    "embedded_doc_type can only be specified if ftype is a "
                    "subclass of %s" % EmbeddedDocumentField
                )

    if embedded_doc_type is not None:
        has_contraints = True

        if etau.is_container(embedded_doc_type):
            embedded_doc_type = tuple(embedded_doc_type)
        else:
            embedded_doc_type = (embedded_doc_type,)

        for _embedded_doc_type in embedded_doc_type:
            if not issubclass(_embedded_doc_type, foo.BaseEmbeddedDocument):
                raise ValueError(
                    "Embedded doc type %s is not a subclass of %s"
                    % (_embedded_doc_type, foo.BaseEmbeddedDocument)
                )

    if virtual is not None:
        has_contraints = True

        if virtual not in (False, True):
            raise ValueError(
                "virtual must be True or False; found %s" % virtual
            )

    return has_contraints


def matches_type_constraints(
    field, ftype=None, embedded_doc_type=None, virtual=None
):
    """Determines whether the field matches the given type constraints.

    Args:
        field: a :class:`Field`
        ftype (None): an optional field type or iterable of types to enforce.
            Must be subclass(es) of :class:`Field`
        embedded_doc_type (None): an optional embedded document type or
            iterable of types to enforce. Must be subclass(es) of
            :class:`fiftyone.core.odm.BaseEmbeddedDocument`
        virtual (None): an optional virtual type (True or False) to enforce

    Returns:
        True/False
    """
    if ftype is not None:
        if etau.is_container(ftype):
            ftype = tuple(ftype)

        if not isinstance(field, ftype):
            return False

    if embedded_doc_type is not None:
        if etau.is_container(embedded_doc_type):
            embedded_doc_type = tuple(embedded_doc_type)

        if not isinstance(field, EmbeddedDocumentField) or not issubclass(
            field.document_type, embedded_doc_type
        ):
            return False

    if virtual is not None:
        return virtual == field.is_virtual

    return True


def validate_field(
    field, path=None, ftype=None, embedded_doc_type=None, virtual=None
):
    """Validates that the field matches the given type constraints.

    Args:
        field: a :class:`Field`
        path (None): the field or ``embedded.field.name``. Only used to
            generate more informative error messages
        ftype (None): an optional field type or iterable of types to enforce.
            Must be subclass(es) of :class:`Field`
        embedded_doc_type (None): an optional embedded document type or
            iterable of types to enforce. Must be subclass(es) of
            :class:`fiftyone.core.odm.BaseEmbeddedDocument`
        virtual (None): an optional virtual type (True or False) to enforce

    Raises:
        ValueError: if the constraints are not valid
    """
    if ftype is None and embedded_doc_type is None and virtual is None:
        return

    if field is None:
        raise ValueError("%s does not exist" % _make_prefix(path))

    if ftype is not None:
        if etau.is_container(ftype):
            ftype = tuple(ftype)

        if not isinstance(field, ftype):
            raise ValueError(
                "%s has type %s, not %s"
                % (_make_prefix(path), type(field), ftype)
            )

    if embedded_doc_type is not None:
        if etau.is_container(embedded_doc_type):
            embedded_doc_type = tuple(embedded_doc_type)

        if not isinstance(field, EmbeddedDocumentField):
            raise ValueError(
                "%s has type %s, not %s"
                % (_make_prefix(path), type(field), EmbeddedDocumentField)
            )

        if not issubclass(field.document_type, embedded_doc_type):
            raise ValueError(
                "%s has document type %s, not %s"
                % (_make_prefix(path), field.document_type, embedded_doc_type)
            )

    if virtual is not None and field.is_virtual != virtual:
        raise ValueError(
            "%s has virtual=%s, not virtual=%s"
            % (_make_prefix(path), field.is_virtual, virtual)
        )


def _make_prefix(path):
    if path is None:
        return "Field"

    return "Field '%s'" % path


_SUPPORTED_MODES = ("before", "after", "both")


def filter_schema(
    schema,
    ftype=None,
    embedded_doc_type=None,
    virtual=None,
    include_private=False,
    flat=False,
    mode=None,
):
    """Filters the schema according to the given constraints.

    Args:
        schema: a dict mapping field names to :class:`Field` instances
        ftype (None): an optional field type or iterable of types to which
            to restrict the returned schema. Must be subclass(es) of
            :class:`Field`
        embedded_doc_type (None): an optional embedded document type or
            iterable of types to which to restrict the returned schema.
            Must be subclass(es) of
            :class:`fiftyone.core.odm.BaseEmbeddedDocument`
        virtual (None): whether to only include virtual (True) or
            non-virtual (False) fields
        include_private (False): whether to include fields that start with
            ``_`` in the returned schema
        flat (False): whether to return a flattened schema where all
            embedded document fields are included as top-level keys
        mode (None): whether to apply the ``ftype``, ``embedded_doc_type``
            and ``virtual`` constraints before and/or after flattening the
            schema. Only applicable when ``flat`` is True. Supported values
            are ``("before", "after", "both")``. The default is ``"after"``

    Returns:
        a dict mapping field names to :class:`Field` instances
    """
    has_contraints = validate_type_constraints(
        ftype=ftype, embedded_doc_type=embedded_doc_type, virtual=virtual
    )

    if has_contraints:
        kwargs = dict(
            ftype=ftype, embedded_doc_type=embedded_doc_type, virtual=virtual
        )
    else:
        kwargs = {}

    if flat:
        if mode is None:
            mode = "after"
        elif mode not in _SUPPORTED_MODES:
            raise ValueError(
                "Invalid mode=%s. Supported modes are %s"
                % (mode, _SUPPORTED_MODES)
            )

        if mode in ("before", "both"):
            before_kwargs = kwargs
        else:
            before_kwargs = {}

        if mode in ("after", "both"):
            after_kwargs = kwargs
        else:
            after_kwargs = {}
    else:
        before_kwargs = kwargs

    if has_contraints or not include_private:
        for field_name in tuple(schema.keys()):
            if (not include_private and field_name.startswith("_")) or (
                has_contraints
                and not matches_type_constraints(
                    schema[field_name], **before_kwargs
                )
            ):
                del schema[field_name]

    if flat:
        schema = flatten_schema(
            schema, **after_kwargs, include_private=include_private
        )

    return schema


def flatten_schema(
    schema,
    ftype=None,
    embedded_doc_type=None,
    virtual=None,
    include_private=False,
):
    """Returns a flat version of the given schema where all embedded document
    fields are included as top-level keys.

    Args:
        schema: a dict mapping field names to :class:`Field` instances
        ftype (None): an optional field type or iterable of types to which to
            restrict the returned schema. Must be subclass(es) of
            :class:`Field`
        embedded_doc_type (None): an optional embedded document type or
            iterable of types to which to restrict the returned schema. Must be
            subclass(es) of :class:`fiftyone.core.odm.BaseEmbeddedDocument`
        virtual (None): whether to only include virtual (True) or non-virtual
            (False) fields
        include_private (False): whether to include fields that start with
            ``_`` in the returned schema

    Returns:
        a dict mapping flattened paths to :class:`Field` instances
    """
    validate_type_constraints(
        ftype=ftype, embedded_doc_type=embedded_doc_type, virtual=virtual
    )

    _schema = {}
    for name, field in schema.items():
        _flatten(
            _schema,
            "",
            name,
            field,
            ftype,
            embedded_doc_type,
            virtual,
            include_private,
        )

    return _schema


def _flatten(
    schema,
    prefix,
    name,
    field,
    ftype,
    embedded_doc_type,
    virtual,
    include_private,
):
    if not include_private and name.startswith("_"):
        return

    if prefix:
        prefix = prefix + "." + name
    else:
        prefix = name

    if matches_type_constraints(
        field,
        ftype=ftype,
        embedded_doc_type=embedded_doc_type,
        virtual=virtual,
    ):
        schema[prefix] = field

    if isinstance(field, (ListField, DictField)):
        field = field.field

    if isinstance(field, EmbeddedDocumentField):
        for name, _field in field.get_field_schema().items():
            _flatten(
                schema,
                prefix,
                name,
                _field,
                ftype,
                embedded_doc_type,
                virtual,
                include_private,
            )


class Field(mongoengine.fields.BaseField):
    """A generic field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

        self._dataset = None
        self._path = None
        self._set_expr = None

    def __str__(self):
        return etau.get_class_name(self)

    def _set_dataset(self, dataset, path, set_expr=None):
        self._dataset = dataset
        self._path = path
        self._set_expr = set_expr

    @property
    def path(self):
        """The fully-qualified path of this field in the dataset's schema, or
        ``None`` if the field is not associated with a dataset.
        """
        return self._path

    @property
    def description(self):
        """A user-editable description of the field.

        Examples::

            import fiftyone as fo
            import fiftyone.zoo as foz

            dataset = foz.load_zoo_dataset("quickstart")
            dataset.add_dynamic_sample_fields()

            field = dataset.get_field("ground_truth")
            field.description = "Ground truth annotations"
            field.save()

            field = dataset.get_field("ground_truth.detections.area")
            field.description = "Area of the box, in pixels^2"
            field.save()

            dataset.reload()

            field = dataset.get_field("ground_truth")
            print(field.description)  # Ground truth annotations

            field = dataset.get_field("ground_truth.detections.area")
            print(field.description)  # 'Area of the box, in pixels^2'
        """
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def info(self):
        """A user-editable dictionary of information about the field.

        Examples::

            import fiftyone as fo
            import fiftyone.zoo as foz

            dataset = foz.load_zoo_dataset("quickstart")
            dataset.add_dynamic_sample_fields()

            field = dataset.get_field("ground_truth")
            field.info = {"url": "https://fiftyone.ai"}
            field.save()

            field = dataset.get_field("ground_truth.detections.area")
            field.info = {"url": "https://fiftyone.ai"}
            field.save()

            dataset.reload()

            field = dataset.get_field("ground_truth")
            print(field.info)  # {'url': 'https://fiftyone.ai'}

            field = dataset.get_field("ground_truth.detections.area")
            print(field.info)  # {'url': 'https://fiftyone.ai'}
        """
        return self._info

    @info.setter
    def info(self, info):
        self._info = info

    @property
    def expr(self):
        """The expression defining a virtual field, or None if the field is not
        virtual.

        Examples::

            import fiftyone as fo
            import fiftyone.zoo as foz
            from fiftyone import ViewField as F

            dataset = foz.load_zoo_dataset("quickstart")
            dataset.compute_metadata()

            dataset.add_sample_field(
                "num_objects",
                fo.IntField,
                expr=F("ground_truth.detections").length(),
            )

            bbox_area = (
                F("$metadata.width") * F("bounding_box")[2] *
                F("$metadata.height") * F("bounding_box")[3]
            )

            dataset.add_sample_field(
                "ground_truth.detections.area_pixels",
                fo.FloatField,
                expr=bbox_area,
            )

            session = fo.launch_app(dataset)
        """
        _ = self._set_field_expr()
        return self._expr

    @expr.setter
    def expr(self, expr):
        if expr is not None and self._expr is None:
            raise ValueError(
                "Regular fields cannot be transformed into virtual fields"
            )

        self._expr = expr
        self._set_expr = None

    def _set_field_expr(self):
        if self.path is None or self._expr is None:
            return None

        if getattr(self, "_set_expr", None) is None:
            pipeline, expr_dict = self._dataset._make_set_field_pipeline(
                self.path, self._expr, embedded_root=True
            )
            self._set_expr = pipeline[0]
            self._expr = expr_dict

        return self._set_expr

    @property
    def is_virtual(self):
        """Whether the field is virtual."""
        return self._expr is not None

    def copy(self):
        """Returns a copy of the field.

        The returned copy is not associated with a dataset.

        Returns:
            a :class:`Field`
        """
        field = deepcopy(self)
        field._set_dataset(None, None)
        return field

    def save(self):
        """Saves any edits to this field's :attr:`description` and :attr:`info`
        attributes.

        Examples::

            import fiftyone as fo
            import fiftyone.zoo as foz

            dataset = foz.load_zoo_dataset("quickstart")
            dataset.add_dynamic_sample_fields()

            field = dataset.get_field("ground_truth")
            field.description = "Ground truth annotations"
            field.info = {"url": "https://fiftyone.ai"}
            field.save()

            field = dataset.get_field("ground_truth.detections.area")
            field.description = "Area of the box, in pixels^2"
            field.info = {"url": "https://fiftyone.ai"}
            field.save()

            dataset.reload()

            field = dataset.get_field("ground_truth")
            print(field.description)  # Ground truth annotations
            print(field.info)  # {'url': 'https://fiftyone.ai'}

            field = dataset.get_field("ground_truth.detections.area")
            print(field.description)  # 'Area of the box, in pixels^2'
            field.info = {"url": "https://fiftyone.ai"}
        """
        if self._dataset is None:
            return

        self._dataset._save_field(self)


class IntField(mongoengine.fields.IntField, Field):
    """A 32 bit integer field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def to_mongo(self, value):
        if value is None:
            return None

        return int(value)


class ObjectIdField(mongoengine.fields.ObjectIdField, Field):
    """An Object ID field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def to_mongo(self, value):
        if value is None:
            return None

        return ObjectId(value)

    def to_python(self, value):
        if value is None:
            return None

        return str(value)


class UUIDField(mongoengine.fields.UUIDField, Field):
    """A UUID field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr


class BooleanField(mongoengine.fields.BooleanField, Field):
    """A boolean field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def validate(self, value):
        if not isinstance(value, (bool, np.bool_)):
            self.error("Boolean fields only accept boolean values")


class DateField(mongoengine.fields.DateField, Field):
    """A date field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def to_mongo(self, value):
        if value is None:
            return None

        return datetime(value.year, value.month, value.day, tzinfo=pytz.utc)

    def to_python(self, value):
        if value is None:
            return None

        # Explicitly converting to UTC is important here because PyMongo loads
        # everything as `datetime`, which will respect `fo.config.timezone`,
        # but we always need UTC here for the conversion back to `date`
        return value.astimezone(pytz.utc).date()

    def validate(self, value):
        if not isinstance(value, date):
            self.error("Date fields must have `date` values")


class DateTimeField(mongoengine.fields.DateTimeField, Field):
    """A datetime field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def validate(self, value):
        if not isinstance(value, datetime):
            self.error("Datetime fields must have `datetime` values")


class FloatField(mongoengine.fields.FloatField, Field):
    """A floating point number field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def to_mongo(self, value):
        if value is None:
            return None

        return float(value)

    def validate(self, value):
        try:
            value = float(value)
        except OverflowError:
            self.error("The value is too large to be converted to float")
        except (TypeError, ValueError):
            self.error("%s could not be converted to float" % value)

        if self.min_value is not None and value < self.min_value:
            self.error("Float value is too small")

        if self.max_value is not None and value > self.max_value:
            self.error("Float value is too large")


class StringField(mongoengine.fields.StringField, Field):
    """A unicode string field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr


class ListField(mongoengine.fields.ListField, Field):
    """A list field that wraps a standard :class:`Field`, allowing multiple
    instances of the field to be stored as a list in the database.

    If this field is not set, its default value is ``[]``.

    Args:
        field (None): an optional :class:`Field` instance describing the
            type of the list elements
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(
        self, field=None, description=None, info=None, expr=None, **kwargs
    ):
        if field is not None:
            if not isinstance(field, Field):
                raise ValueError(
                    "Invalid field type '%s'; must be a subclass of %s"
                    % (type(field), Field)
                )

        super().__init__(field=field, **kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def __str__(self):
        if self.field is not None:
            return "%s(%s)" % (
                etau.get_class_name(self),
                etau.get_class_name(self.field),
            )

        return etau.get_class_name(self)

    def _set_dataset(self, dataset, path, set_expr=None):
        super()._set_dataset(dataset, path, set_expr=set_expr)

        if self.field is not None:
            self.field._set_dataset(dataset, path)


class HeatmapRangeField(ListField):
    """A ``[min, max]`` range of the values in a
    :class:`fiftyone.core.labels.Heatmap`.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, **kwargs):
        if "null" not in kwargs:
            kwargs["null"] = True

        if "field" not in kwargs:
            kwargs["field"] = FloatField()

        super().__init__(**kwargs)

    def __str__(self):
        return etau.get_class_name(self)

    def validate(self, value):
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 2
            or not value[0] <= value[1]
        ):
            self.error("Heatmap range fields must contain `[min, max]` ranges")


class DictField(mongoengine.fields.DictField, Field):
    """A dictionary field that wraps a standard Python dictionary.

    If this field is not set, its default value is ``{}``.

    Args:
        field (None): an optional :class:`Field` instance describing the type
            of the values in the dict
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(
        self, field=None, description=None, info=None, expr=None, **kwargs
    ):
        if field is not None:
            if not isinstance(field, Field):
                raise ValueError(
                    "Invalid field type '%s'; must be a subclass of %s"
                    % (type(field), Field)
                )

        super().__init__(field=field, **kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def __str__(self):
        if self.field is not None:
            return "%s(%s)" % (
                etau.get_class_name(self),
                etau.get_class_name(self.field),
            )

        return etau.get_class_name(self)

    def _set_dataset(self, dataset, path, set_expr=None):
        super()._set_dataset(dataset, path, set_expr=set_expr)

        if self.field is not None:
            self.field._set_dataset(dataset, path)

    def validate(self, value):
        if not all(map(lambda k: etau.is_str(k), value)):
            self.error("Dict fields must have string keys")

        if self.field is not None:
            for _value in value.values():
                self.field.validate(_value)

        if value is not None and not isinstance(value, dict):
            self.error("Value must be a dict")


class IntDictField(DictField):
    """A :class:`DictField` whose keys are integers.

    If this field is not set, its default value is ``{}``.

    Args:
        field (None): an optional :class:`Field` instance describing the type
            of the values in the dict
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def to_mongo(self, value):
        if value is None:
            return None

        value = {str(k): v for k, v in value.items()}
        return super().to_mongo(value)

    def to_python(self, value):
        if value is None:
            return None

        return {int(k): v for k, v in value.items()}

    def validate(self, value):
        if not isinstance(value, dict):
            self.error("Value must be a dict")

        if not all(map(lambda k: isinstance(k, numbers.Integral), value)):
            self.error("Int dict fields must have integer keys")

        if self.field is not None:
            for _value in value.values():
                self.field.validate(_value)


class KeypointsField(ListField):
    """A list of ``(x, y)`` coordinate pairs.

    If this field is not set, its default value is ``[]``.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __str__(self):
        return etau.get_class_name(self)

    def validate(self, value):
        # Only validate value[0], for efficiency
        if not isinstance(value, (list, tuple)) or (
            value
            and (not isinstance(value[0], (list, tuple)) or len(value[0]) != 2)
        ):
            self.error("Keypoints fields must contain a list of (x, y) pairs")


class PolylinePointsField(ListField):
    """A list of lists of ``(x, y)`` coordinate pairs.

    If this field is not set, its default value is ``[]``.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __str__(self):
        return etau.get_class_name(self)

    def validate(self, value):
        # Only validate value[0] and value[0][0], for efficiency
        if (
            not isinstance(value, (list, tuple))
            or (value and not isinstance(value[0], (list, tuple)))
            or (
                value
                and value[0]
                and (
                    not isinstance(value[0][0], (list, tuple))
                    or len(value[0][0]) != 2
                )
            )
        ):
            self.error(
                "Polyline points fields must contain a list of lists of "
                "(x, y) pairs"
            )


class _GeoField(Field):
    """Base class for GeoJSON fields.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    # The GeoJSON type of the field. Subclasses must implement this
    _TYPE = None

    def to_mongo(self, value):
        if isinstance(value, dict):
            return value

        return SON([("type", self._TYPE), ("coordinates", value)])

    def to_python(self, value):
        if isinstance(value, dict):
            return value["coordinates"]

        return value


class GeoPointField(_GeoField, mongoengine.fields.PointField):
    """A GeoJSON field storing a longitude and latitude coordinate point.

    The data is stored as ``[longitude, latitude]``.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    _TYPE = "Point"

    def validate(self, value):
        if isinstance(value, dict):
            self.error("Geo fields expect coordinate lists, but found dict")

        super().validate(value)


class GeoLineStringField(_GeoField, mongoengine.fields.LineStringField):
    """A GeoJSON field storing a line of longitude and latitude coordinates.

    The data is stored as follows::

        [[lon1, lat1], [lon2, lat2], ...]

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    _TYPE = "LineString"

    def validate(self, value):
        if isinstance(value, dict):
            self.error("Geo fields expect coordinate lists, but found dict")

        super().validate(value)


class GeoPolygonField(_GeoField, mongoengine.fields.PolygonField):
    """A GeoJSON field storing a polygon of longitude and latitude coordinates.

    The data is stored as follows::

        [
            [[lon1, lat1], [lon2, lat2], ...],
            [[lon1, lat1], [lon2, lat2], ...],
            ...
        ]

    where the first element describes the boundary of the polygon and any
    remaining entries describe holes.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    _TYPE = "Polygon"

    def validate(self, value):
        if isinstance(value, dict):
            self.error("Geo fields expect coordinate lists, but found dict")

        super().validate(value)


class GeoMultiPointField(_GeoField, mongoengine.fields.MultiPointField):
    """A GeoJSON field storing a list of points.

    The data is stored as follows::

        [[lon1, lat1], [lon2, lat2], ...]

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    _TYPE = "MultiPoint"

    def validate(self, value):
        if isinstance(value, dict):
            self.error("Geo fields expect coordinate lists, but found dict")

        super().validate(value)


class GeoMultiLineStringField(
    _GeoField, mongoengine.fields.MultiLineStringField
):
    """A GeoJSON field storing a list of lines.

    The data is stored as follows::

        [
            [[lon1, lat1], [lon2, lat2], ...],
            [[lon1, lat1], [lon2, lat2], ...],
            ...
        ]

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    _TYPE = "MultiLineString"

    def validate(self, value):
        if isinstance(value, dict):
            self.error("Geo fields expect coordinate lists, but found dict")

        super().validate(value)


class GeoMultiPolygonField(_GeoField, mongoengine.fields.MultiPolygonField):
    """A GeoJSON field storing a list of polygons.

    The data is stored as follows::

        [
            [
                [[lon1, lat1], [lon2, lat2], ...],
                [[lon1, lat1], [lon2, lat2], ...],
                ...
            ],
            [
                [[lon1, lat1], [lon2, lat2], ...],
                [[lon1, lat1], [lon2, lat2], ...],
                ...
            ],
            ...
        ]

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    _TYPE = "MultiPolygon"

    def validate(self, value):
        if isinstance(value, dict):
            self.error("Geo fields expect coordinate lists, but found dict")

        super().validate(value)


class VectorField(mongoengine.fields.BinaryField, Field):
    """A one-dimensional array field.

    :class:`VectorField` instances accept numeric lists, tuples, and 1D numpy
    array values. The underlying data is serialized and stored in the database
    as zlib-compressed bytes generated by ``numpy.save`` and always retrieved
    as a numpy array.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def to_mongo(self, value):
        if value is None:
            return None

        bytes = fou.serialize_numpy_array(value)
        return super().to_mongo(bytes)

    def to_python(self, value):
        if value is None or isinstance(value, np.ndarray):
            return value

        if isinstance(value, (list, tuple)):
            return np.array(value)

        return fou.deserialize_numpy_array(value)

    def validate(self, value):
        if isinstance(value, np.ndarray):
            if value.ndim > 1:
                self.error("Only 1D arrays may be used in a vector field")
        elif not isinstance(value, (list, tuple, Binary)):
            self.error(
                "Only numpy arrays, lists, and tuples may be used in a "
                "vector field"
            )


class ArrayField(mongoengine.fields.BinaryField, Field):
    """An n-dimensional array field.

    :class:`ArrayField` instances accept numpy array values. The underlying
    data is serialized and stored in the database as zlib-compressed bytes
    generated by ``numpy.save`` and always retrieved as a numpy array.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, description=None, info=None, expr=None, **kwargs):
        super().__init__(**kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def to_mongo(self, value):
        if value is None:
            return None

        bytes = fou.serialize_numpy_array(value)
        return super().to_mongo(bytes)

    def to_python(self, value):
        if value is None or isinstance(value, np.ndarray):
            return value

        return fou.deserialize_numpy_array(value)

    def validate(self, value):
        if not isinstance(value, (np.ndarray, Binary)):
            self.error("Only numpy arrays may be used in an array field")


class FrameNumberField(IntField):
    """A video frame number field.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def validate(self, value):
        try:
            fofu.validate_frame_number(value)
        except fofu.FrameError as e:
            self.error(str(e))


class FrameSupportField(ListField):
    """A ``[first, last]`` frame support in a video.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, **kwargs):
        if "field" not in kwargs:
            kwargs["field"] = IntField()

        super().__init__(**kwargs)

    def __str__(self):
        return etau.get_class_name(self)

    def validate(self, value):
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 2
            or not (1 <= value[0] <= value[1])
        ):
            self.error(
                "Frame support fields must contain `[first, last]` frame "
                "numbers"
            )


class ClassesField(ListField):
    """A :class:`ListField` that stores class label strings.

    If this field is not set, its default value is ``[]``.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, **kwargs):
        if "field" not in kwargs:
            kwargs["field"] = StringField()

        super().__init__(**kwargs)

    def __str__(self):
        return etau.get_class_name(self)


class TargetsField(IntDictField):
    """A :class:`DictField` that stores mapping between integer keys and string
    targets.

    If this field is not set, its default value is ``{}``.

    Args:
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(self, **kwargs):
        if "field" not in kwargs:
            kwargs["field"] = StringField()

        super().__init__(**kwargs)

    def __str__(self):
        return etau.get_class_name(self)


class EmbeddedDocumentField(mongoengine.fields.EmbeddedDocumentField, Field):
    """A field that stores instances of a given type of
    :class:`fiftyone.core.odm.BaseEmbeddedDocument` object.

    Args:
        document_type: the :class:`fiftyone.core.odm.BaseEmbeddedDocument` type
            stored in this field
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(
        self, document_type, description=None, info=None, expr=None, **kwargs
    ):
        super().__init__(document_type, **kwargs)
        self.fields = kwargs.get("fields", [])
        self._description = description
        self._info = info
        self._expr = expr
        self._selected_fields = None
        self._excluded_fields = None
        self._virtual_fields = None
        self.__fields = None

    def __str__(self):
        return "%s(%s)" % (
            etau.get_class_name(self),
            etau.get_class_name(self.document_type),
        )

    def _set_dataset(self, dataset, path, set_expr=None):
        super()._set_dataset(dataset, path, set_expr=set_expr)

        for field_name, field in self._fields.items():
            if not isinstance(field, Field):
                continue

            if path is not None:
                _path = path + "." + field_name
            else:
                _path = None

            field._set_dataset(dataset, _path)

    @property
    def _fields(self):
        if self.__fields is None:
            # Must initialize now because `document_type` could have been a
            # string at class instantiation
            self.__fields = deepcopy(self.document_type._fields)
            self.__fields.update({f.name: f for f in self.fields})

        return self.__fields

    def _use_view(
        self, selected_fields=None, excluded_fields=None, virtual_fields=None
    ):
        if selected_fields is not None and excluded_fields is not None:
            selected_fields = selected_fields.difference(excluded_fields)
            excluded_fields = None

        if virtual_fields is not None:
            self._fields.update(virtual_fields)

        self._selected_fields = selected_fields
        self._excluded_fields = excluded_fields
        self._virtual_fields = virtual_fields

    def _get_field_names(self, include_private=False, use_db_fields=False):
        field_names = tuple(self._fields.keys())

        if not include_private:
            field_names = tuple(
                fn for fn in field_names if not fn.startswith("_")
            )

        if self._selected_fields is not None:
            field_names = tuple(
                fn for fn in field_names if fn in self._selected_fields
            )

        if self._excluded_fields is not None:
            field_names = tuple(
                fn for fn in field_names if fn not in self._excluded_fields
            )

        if use_db_fields:
            return self._to_db_fields(field_names)

        return field_names

    def _get_default_fields(self, include_private=False, use_db_fields=False):
        field_names = tuple(self.document_type._fields.keys())

        if not include_private:
            field_names = tuple(
                f for f in field_names if not f.startswith("_")
            )

        if use_db_fields:
            field_names = self._to_db_fields(field_names)

        return field_names

    def _to_db_fields(self, field_names):
        return tuple(self._fields[f].db_field or f for f in field_names)

    def get_field_schema(
        self,
        ftype=None,
        embedded_doc_type=None,
        virtual=None,
        include_private=False,
        flat=False,
        mode=None,
    ):
        """Returns a schema dictionary describing the fields of the embedded
        document field.

        Args:
            ftype (None): an optional field type or iterable of types to which
                to restrict the returned schema. Must be subclass(es) of
                :class:`Field`
            embedded_doc_type (None): an optional embedded document type or
                iterable of types to which to restrict the returned schema.
                Must be subclass(es) of
                :class:`fiftyone.core.odm.BaseEmbeddedDocument`
            virtual (None): whether to only include virtual (True) or
                non-virtual (False) fields
            include_private (False): whether to include fields that start with
                ``_`` in the returned schema
            flat (False): whether to return a flattened schema where all
                embedded document fields are included as top-level keys
            mode (None): whether to apply the ``ftype``, ``embedded_doc_type``
                and ``virtual`` constraints before and/or after flattening the
                schema. Only applicable when ``flat`` is True. Supported values
                are ``("before", "after", "both")``. The default is ``"after"``

        Returns:
            a dict mapping field names to :class:`Field` instances
        """
        schema = {
            field_name: self._fields[field_name]
            for field_name in self._get_field_names(
                include_private=include_private
            )
        }

        return filter_schema(
            schema,
            ftype=ftype,
            embedded_doc_type=embedded_doc_type,
            virtual=virtual,
            include_private=include_private,
            flat=flat,
            mode=mode,
        )

    def validate(self, value, **kwargs):
        if not isinstance(value, self.document_type):
            self.error(
                "Expected %s; found %s" % (self.document_type, type(value))
            )

        for k, v in self._fields.items():
            try:
                val = value[k]
            except KeyError:
                val = None

            if val is not None:
                v.validate(val)

    def _merge_fields(self, path, field, validate=True, recursive=True):
        if validate:
            foo.validate_fields_match(path, field, self)
        elif not isinstance(field, EmbeddedDocumentField):
            return None

        new_schema = {}
        existing_fields = self._fields

        for name, _field in field._fields.items():
            _existing_field = existing_fields.get(name, None)
            if _existing_field is not None:
                if validate:
                    _path = path + "." + name
                    foo.validate_fields_match(_path, _field, _existing_field)

                if recursive:
                    if isinstance(_existing_field, ListField):
                        _existing_field = _existing_field.field
                        if isinstance(_field, ListField):
                            _field = _field.field
                        else:
                            _existing_field = None

                    if isinstance(_existing_field, EmbeddedDocumentField):
                        _path = path + "." + name
                        _new_schema = _existing_field._merge_fields(
                            _path,
                            _field,
                            validate=validate,
                            recursive=recursive,
                        )

                        if _new_schema:
                            new_schema.update(_new_schema)
            else:
                _path = path + "." + name
                new_schema[_path] = _field

        return new_schema

    def _declare_field(self, dataset, path, field_or_doc):
        if isinstance(field_or_doc, foo.SampleFieldDocument):
            field = field_or_doc.to_field()
        else:
            field = field_or_doc

        field_name = field.name

        self.fields = [f for f in self.fields if f.name != field_name]
        self.fields.append(field)

        prev = self._fields.pop(field_name, None)

        if prev is not None:
            prev._set_dataset(None, None)
            field.required = prev.required
            field.null = prev.null

        field._set_dataset(dataset, path)
        self._fields[field_name] = field

    def _update_field(self, dataset, field_name, new_path, field):
        new_field_name = field.name

        self.fields = [
            f if f.name != field_name else field for f in self.fields
        ]
        prev = self._fields.pop(field_name, None)

        if prev is not None:
            prev._set_dataset(None, None)

        field._set_dataset(dataset, new_path)
        self._fields[new_field_name] = field

    def _undeclare_field(self, field_name):
        self.fields = [f for f in self.fields if f.name != field_name]
        prev = self._fields.pop(field_name, None)

        if prev is not None:
            prev._set_dataset(None, None)


class EmbeddedDocumentListField(
    mongoengine.fields.EmbeddedDocumentListField, Field
):
    """A field that stores a list of a given type of
    :class:`fiftyone.core.odm.BaseEmbeddedDocument` objects.

    Args:
        document_type: the :class:`fiftyone.core.odm.BaseEmbeddedDocument` type
            stored in this field
        description (None): an optional description
        info (None): an optional info dict
        expr (None): a :class:`fiftyone.core.expressions.ViewExpression`
            defining the field's virtual expression
    """

    def __init__(
        self, document_type, description=None, info=None, expr=None, **kwargs
    ):
        super().__init__(document_type, **kwargs)
        self._description = description
        self._info = info
        self._expr = expr

    def __str__(self):
        # pylint: disable=no-member
        return "%s(%s)" % (
            etau.get_class_name(self),
            etau.get_class_name(self.document_type),
        )


_ARRAY_FIELDS = (VectorField, ArrayField)

# Fields whose values can be used without parsing when loaded from MongoDB
_PRIMITIVE_FIELDS = (
    BooleanField,
    DateTimeField,
    FloatField,
    IntField,
    ObjectIdField,
    StringField,
)
