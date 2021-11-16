from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.expressions import F, Case, Value, When
from django.db.models.functions import Concat

from django_orm_hybrid.models import OrmManager, orm_property, OrmExpression, OrmExpressionResult


class Person(models.Model):
    first_note = models.IntegerField()
    second_note = models.IntegerField()
    first_name = models.CharField(max_length=63)
    last_name = models.CharField(max_length=63)
    datetime = models.DateTimeField()

    objects = OrmManager()

    @orm_property
    def approved(self, n):
        return (self.first_note + self.second_note) > n

    @approved.expression
    def approved(self, n, through=''):
        return Case(
            When(F(f'{through}first_note') + F(f'{through}second_note') > n, then=Value(True)),
            default=Value(False),
        )

    @orm_property
    def total_notes(self):
        return self.first_note + self.second_note
    
    @total_notes.expression
    def total_notes(cls, through=''):
        return models.F(f'{through}first_note') + models.F(f'{through}second_note')

    @orm_property
    def notes_concat(self):
        return f'{self.first_note} - {self.second_note}'

    @notes_concat.expression
    def notes_concat(cls, through=''):
        return Concat(
            f'{through}first_note',
            Value(' - '),
            f'{through}second_note',
            output_field=models.CharField(),
        )

    @orm_property
    def notes_multiplication(self, n):
        return self.first_note * self.second_note * n

    @notes_multiplication.expression
    def notes_multiplication(cls, n, through=''):
        return models.F(f'{through}first_note') * models.F(f'{through}second_note') * n

    @orm_property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    @full_name.expression
    def full_name(cls, through=''):
        return Concat(
            f'{through}first_name',
            Value(' '),
            f'{through}last_name',
        )

    @orm_property
    def birth_datetime(self):
        return self.datetime

    @birth_datetime.expression
    def birth_datetime(cls, through=''):
        return models.F(f'{through}datetime')


class Profile(models.Model):
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name='profile')
    age = models.IntegerField(validators=[MaxValueValidator(100)])

    objects = OrmManager()
