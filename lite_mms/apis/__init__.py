# -*- coding: UTF-8 -*-
import types

_wrappers = {}


class ModelWrapper(object):
    def __init__(self, model):
        self.__model = model

    @property
    def model(self):
        return self.__model

    def __getattr__(self, name):
        attr = getattr(self.__model, name)
        if isinstance(attr, types.ListType) or isinstance(attr,
                                                          types.TupleType):
            return type(attr)(self.__wrap(i) for i in attr)
        return self.__wrap(attr)

    def __setattr__(self, key, value):
        if key != '_ModelWrapper__model':
            self.__model.__setattr__(key, value)
        else:
            self.__dict__[key] = value

    def __wrap(self, attr):
        from lite_mms.database import db

        if isinstance(attr, db.Model):
            return self.__do_wrap(attr)
        return attr

    def __do_wrap(self, attr):
        try:
            return _wrappers[attr.__class__.__name__ + "Wrapper"](attr)
        except KeyError:
            return attr

    def __unicode__(self):
        return unicode(self.model)

    def __dir__(self):
        return self.model.__dict__.keys()


def wraps(model):
    return _wrappers[model.__class__.__name__ + "Wrapper"](model)


import auth
import cargo
import customer
import order
import manufacture
import quality_inspection
import delivery
import product
import store
import harbor
import broker
import plate
import log

from path import path

for fname in path(__path__[0]).files("[!_]*.py"):
    fname = fname.basename()[:-len(".py")]
    package = __import__(str("lite_mms.apis." + fname), fromlist=[str(fname)])
    for k, v in package.__dict__.items():
        if isinstance(v, types.TypeType) and \
                issubclass(v, ModelWrapper) and \
                k.endswith("Wrapper"):
            _wrappers[k] = v
            globals()[k] = v # install all the wrappers in this module

