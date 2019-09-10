from peewee import (
        CharField, FloatField, IntegerField, ForeignKeyField, TextField
        )

from cropdb import BaseModel


class Chemical(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    _searchable = ['code','name']

    @classmethod
    def modeltitle(cls):
        return 'Chemical Active Group'


class ProdStatus(BaseModel):
    name = CharField(unique=True)

    @classmethod
    def modeltitle(cls):
        return 'Product Status'


class SalesStatus(BaseModel):
    name = CharField(unique=True)

    @classmethod
    def modeltitle(cls):
        return 'Sales Status'


class Product(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    chemical = ForeignKeyField(Chemical, related_name='products')
    rate = CharField(null=True)
    launch_year = IntegerField(null=True)
    comment = TextField()
    product_status = ForeignKeyField(ProdStatus, null=True, related_name='products')
    sales_status = ForeignKeyField(SalesStatus, null=True, related_name='products')
    _searchable = ['name', 'code']
    _filter = ['launch_year', 'product_status', 'sales_status']


class Sales(BaseModel):
    product = ForeignKeyField(Product, related_name='sales')
    year = IntegerField(index=True)
    cost = FloatField(default=0)
    weight = FloatField(default=0)
    currency = CharField(default='USD')
    weight_units = CharField(default='tonne')


class Method(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    _searchable = ['code','name']

    @classmethod
    def modeltitle(cls):
        return 'Application Method'


class Crop(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    _searchable = ['code','name']


class PestType(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    _searchable = ['code','name']

    @classmethod
    def modeltitle(cls):
        return 'Pest Type'


class Pest(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    type = ForeignKeyField(PestType, related_name='pests')
    _searchable = ['code','name']
    _filter = ['type']


class CropPest(BaseModel):
    crop = ForeignKeyField(Crop, related_name='pests')
    pest = ForeignKeyField(Pest, related_name='crops')


class Application(BaseModel):
    product = ForeignKeyField(Product, related_name='applications')
    crop = ForeignKeyField(Crop, related_name='applications')
    pest = ForeignKeyField(Pest, related_name='applications')
    method = ForeignKeyField(Method, related_name='applications')

    class Meta:
        indexes = ((('product', 'crop', 'pest', 'method'), True),)


class Company(BaseModel):
    code = CharField(unique=True)
    name = CharField(unique=True)
    _searchable = ['name']


class Brand(BaseModel):
    company = ForeignKeyField(Company, related_name='brands')
    product = ForeignKeyField(Product, related_name='brands')
    name = CharField(null=True)
    porder = IntegerField(null=True)
    _searchable = ['name']
