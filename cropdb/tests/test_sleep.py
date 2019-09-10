'''
    tests
    —————

    :copyright: Anshul Sirur 2015
'''
from peewee import *

# Locals
from ..sleep import Sleep, SleepModel, Request, Response
from .test_base import TestBase


class Owner(SleepModel):
    code = CharField(primary_key=True)
    name = CharField()


class Pet(SleepModel):
    code = CharField(primary_key=True)
    name = CharField()
    age = IntegerField()
    owner = ForeignKeyField(Owner, related_name='pets')


class Scrip(SleepModel):
    pet = ForeignKeyField(Pet, related_name='scrips')

    class Views:
        @classmethod
        def makepdf(cls, item):
            return 'PDF:'+str(item.id)


class ScripItem(SleepModel):
    drug = CharField()
    dose = IntegerField()
    scrip = ForeignKeyField(Scrip, related_name='items')


mimes = ['application/pdf', 'text/html', 'application/json']

data = {'alan'   : dict(code='ALN', name='Alan'),
        'stan'   : dict(code='STN', name='Stan'),
        'brutus' : dict(code='BRT', owner='ALN', name='Brutus', age=6),
        'poopy'  : dict(code='POO', name='Poopy', owner='ALN', age=21)
        }


class TestSleep(TestBase):
    def setUp(self):
        super().setUp()

        self.alan = Owner.create(**data['alan'])
        self.brutus = Pet.create(**data['brutus'])
        self.poopy = Pet.create(**data['poopy'])
        self.scrip = Scrip.create(pet='BRT')

        drugs = [
                {'drug': 'Noflea', 'dose': 3, 'scrip':self.scrip},
                {'drug': 'Glowfur', 'dose': 5, 'scrip':self.scrip}
                ]

        with Sleep.db.atomic():
            ScripItem.insert_many(drugs).execute()

    def test_post_request(self):
        req = Request.post('owner', data['stan'])
        resp = Sleep.request(req)
        self.assertEqual(resp.code, 201, 'POST request failed.')
        item = resp.data
        self.assertEqual(item.name, data['stan']['name'], 'POST incorrect data.')

    def test_get_request(self):
        req = Request.get('pet', key='BRT')
        resp = Sleep.request(req)
        self.assertEqual(resp.code, 200, 'GET request failed.')
        item = resp.data
        self.assertEqual(item, self.brutus, 'GET wrong item.')

    def test_put_request(self):
        req = Request.put('pet', 'BRT', {'age':11})
        resp = Sleep.request(req)
        self.assertEqual(resp.code, 200, 'PUT request failed.')
        item = Pet.get(Pet.code == 'BRT')
        self.assertEqual(item.age, 11, 'PUT incorrect.')

    def test_delete_request(self):
        req = Request.delete('pet', 'POO')
        resp = Sleep.request(req)
        self.assertEqual(resp.code, 200, 'DELETE request failed.')

    def test_relationship(self):
        req = Request.get('pet', key='BRT')
        resp = Sleep.request(req)
        item = resp.data
        self.assertIsInstance(item.owner, Owner)
        for pet in item.owner.pets:
            self.assertIn(pet.name, ['Brutus', 'Poopy'])
