from django.db.models.expressions import Case, Value, When
from django.test import TestCase
from unittest import skip
from django.db import models
from django.utils.timezone import now, timedelta

from django_orm_hybrid.models import QQ, OrmManager, orm_property, OrmExpression, OrmExpressionResult

from .models import Person, Profile


class HighLevelTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.person1: Person = Person.objects.create(first_note=1, second_note=2, first_name='Lautaro', last_name='Redbear', datetime=now())
        Profile.objects.create(person=self.person1, age=20)
        self.person2: Person = Person.objects.create(first_note=3, second_note=4, first_name='Gabriel', last_name='Smith', datetime=now() + timedelta(days=5))
        Profile.objects.create(person=self.person2, age=30)

    def test_instance_orm_property(self):
        self.assertEqual(self.person1.full_name(), 'Lautaro Redbear')
        self.assertEqual(self.person2.full_name(), 'Gabriel Smith')
        self.assertEqual(self.person1.total_notes(), 3)
        self.assertEqual(self.person2.total_notes(), 7)
        self.assertEqual(self.person1.notes_concat(), '1 - 2')
        self.assertEqual(self.person2.notes_concat(), '3 - 4')
        self.assertEqual(self.person1.notes_multiplication(10), 1 * 2 * 10)
        self.assertEqual(self.person2.notes_multiplication(10), 3 * 4 * 10)
        self.assertEqual(self.person1.approved(n=3), False)
        self.assertEqual(self.person1.approved(n=2), True)
        self.assertEqual(self.person2.approved(n=7), False)
        self.assertEqual(self.person2.approved(n=6), True)

    def test_queryset_orm_property_annotation(self):
        queryset = Person.objects.annotate(Person.full_name()).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear', 'Gabriel Smith'])
        queryset = Person.objects.annotate(Person.total_notes()).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])
        queryset = Person.objects.annotate(Person.notes_concat()).values_list('notes_concat', flat=True)
        self.assertEqual(list(queryset), ['1 - 2', '3 - 4'])
        queryset = Person.objects.annotate(Person.notes_multiplication(10)).values_list('notes_multiplication', flat=True)
        self.assertEqual(list(queryset), [1 * 2 * 10, 3 * 4 * 10])
        
    def test_queryset_orm_property_filter_with_qq_objects(self):
        queryset = Person.objects.filter(QQ(Person.full_name() == 'Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(~QQ(Person.full_name() == 'Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.filter(QQ(Person.full_name() == 'Lautaro Redbear') | QQ(Person.full_name() == 'Gabriel Smith')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear', 'Gabriel Smith'])
        queryset = Person.objects.filter(QQ(Person.full_name() == 'Lautaro Redbear') & QQ(Person.full_name() == 'Gabriel Smith')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), [])
        queryset = Person.objects.filter(QQ(Person.full_name() == 'Lautaro Redbear') & QQ(Person.notes_concat() == '1 - 2')).values_list('full_name', 'notes_concat')
        self.assertEqual(list(queryset), [('Lautaro Redbear', '1 - 2')])

    def test_queryset_orm_property_exclude_with_qq_objects(self):
        queryset = Person.objects.exclude(QQ(Person.full_name() == 'Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(~QQ(Person.full_name() == 'Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.exclude(QQ(Person.full_name() == 'Lautaro Redbear') | QQ(Person.full_name() == 'Gabriel Smith')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), [])
        queryset = Person.objects.exclude(QQ(Person.full_name() == 'Lautaro Redbear') & QQ(Person.full_name() == 'Gabriel Smith')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear', 'Gabriel Smith'])
        queryset = Person.objects.exclude(QQ(Person.full_name() == 'Lautaro Redbear') & QQ(Person.notes_concat() == '1 - 2')).values_list('full_name', 'notes_concat')
        self.assertEqual(list(queryset), [('Gabriel Smith', '3 - 4')])
        queryset = Person.objects.exclude(QQ(Person.full_name() == 'Lautaro Redbear') & ~QQ(Person.notes_concat() == '3 - 4')).values_list('full_name', 'notes_concat')
        self.assertEqual(list(queryset), [('Gabriel Smith', '3 - 4')])

    def test_queryset_orm_property_annotation_with_through(self):
        queryset = Profile.objects.annotate(Person.full_name(through='person')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear', 'Gabriel Smith'])

    def test_queryset_orm_property_filter_exact(self):
        queryset = Person.objects.filter(Person.full_name() == 'Lautaro Redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.total_notes() == 3).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])
        queryset = Person.objects.filter(Person.full_name().exact('Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.total_notes().exact(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])
        queryset = Person.objects.filter(Person.notes_multiplication(10) == 1 * 2 * 10).values_list('notes_multiplication', flat=True)
        self.assertEqual(list(queryset), [1 * 2 * 10])
        queryset = Person.objects.filter(Person.notes_multiplication(10).exact(1 * 2 * 10)).values_list('notes_multiplication', flat=True)
        self.assertEqual(list(queryset), [1 * 2 * 10])

    def test_queryset_orm_property_filter_exact_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person') == 'Lautaro Redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.full_name(through='person').exact('Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.notes_multiplication(10, through='person') == 1 * 2 * 10).values_list('notes_multiplication', flat=True)
        self.assertEqual(list(queryset), [1 * 2 * 10])
        queryset = Profile.objects.filter(Person.notes_multiplication(10, through='person').exact(1 * 2 * 10)).values_list('notes_multiplication', flat=True)
        self.assertEqual(list(queryset), [1 * 2 * 10])

    def test_queryset_orm_property_exclude_exact(self):
        queryset = Person.objects.exclude(Person.full_name() == 'Lautaro Redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.total_notes() == 3).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])
        queryset = Person.objects.exclude(Person.full_name().exact('Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.total_notes().exact(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_exclude_exact_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person') == 'Lautaro Redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Profile.objects.exclude(Person.full_name(through='person').exact('Lautaro Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_iexact(self):
        queryset = Person.objects.filter(Person.full_name(ignore_case=True) == 'lautaro redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.full_name().iexact('lautaro redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_iexact_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person', ignore_case=True) == 'lautaro redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.full_name(through='person').iexact('lautaro redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_iexact(self):
        queryset = Person.objects.exclude(Person.full_name(ignore_case=True) == 'lautaro redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.full_name().iexact('lautaro redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_iexact_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person', ignore_case=True) == 'lautaro redbear').values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Profile.objects.exclude(Person.full_name(through='person').iexact('lautaro redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_contains(self):
        queryset = Person.objects.filter(Person.full_name().contains('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_contains_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person').contains('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_contains(self):
        queryset = Person.objects.exclude(Person.full_name().contains('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_contains_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person').contains('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_icontains(self):
        queryset = Person.objects.filter(Person.full_name(ignore_case=True).contains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.full_name().icontains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_icontains_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person', ignore_case=True).contains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.full_name(through='person').icontains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_icontains(self):
        queryset = Person.objects.exclude(Person.full_name(ignore_case=True).contains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.full_name().icontains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_icontains_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person', ignore_case=True).contains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Profile.objects.exclude(Person.full_name(through='person').icontains('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_greater_than(self):
        queryset = Person.objects.filter(Person.total_notes() > 3).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])
        queryset = Person.objects.filter(Person.total_notes().gt(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_filter_greater_than_with_through(self):
        queryset = Profile.objects.filter(Person.total_notes(through='person') > 3).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])
        queryset = Profile.objects.filter(Person.total_notes(through='person').gt(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_exclude_greater_than(self):
        queryset = Person.objects.exclude(Person.total_notes() > 3).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])
        queryset = Person.objects.exclude(Person.total_notes().gt(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])

    def test_queryset_orm_property_exclude_greater_than_with_through(self):
        queryset = Profile.objects.exclude(Person.total_notes(through='person') > 3).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])
        queryset = Profile.objects.exclude(Person.total_notes(through='person').gt(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])


    def test_queryset_orm_property_filter_greater_equal_than(self):
        queryset = Person.objects.filter(Person.total_notes().gte(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])

    def test_queryset_orm_property_filter_greater_equal_than_with_through(self):
        queryset = Profile.objects.filter(Person.total_notes(through='person').gte(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])

    def test_queryset_orm_property_exclude_greater_equal_than(self):
        queryset = Person.objects.exclude(Person.total_notes().gte(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_exclude_greater_equal_than_with_through(self):
        queryset = Profile.objects.exclude(Person.total_notes(through='person').gte(3)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_filter_less_than(self):
        queryset = Person.objects.filter(Person.total_notes().lt(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])

    def test_queryset_orm_property_filter_less_than_with_through(self):
        queryset = Profile.objects.filter(Person.total_notes(through='person').lt(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])

    def test_queryset_orm_property_exclude_less_than(self):
        queryset = Person.objects.exclude(Person.total_notes().lt(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_exclude_less_than_with_through(self):
        queryset = Profile.objects.exclude(Person.total_notes(through='person').lt(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_filter_less_equal_than(self):
        queryset = Person.objects.filter(Person.total_notes().lte(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])

    def test_queryset_orm_property_filter_less_equal_than_with_through(self):
        queryset = Profile.objects.filter(Person.total_notes(through='person').lte(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])

    def test_queryset_orm_property_exclude_less_equal_than(self):
        queryset = Person.objects.exclude(Person.total_notes().lte(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_exclude_less_equal_than_with_through(self):
        queryset = Profile.objects.exclude(Person.total_notes(through='person').lte(7)).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_filter_in(self):
        queryset = Person.objects.filter(Person.total_notes().in_([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])

    def test_queryset_orm_property_filter_in_with_through(self):
        queryset = Profile.objects.filter(Person.total_notes(through='person').in_([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])

    def test_queryset_orm_property_exclude_in(self):
        queryset = Person.objects.exclude(Person.total_notes().in_([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_exclude_in_with_through(self):
        queryset = Profile.objects.exclude(Person.total_notes(through='person').in_([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_filter_startswith(self):
        queryset = Person.objects.filter(Person.full_name().startswith('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_startswith_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person').startswith('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_startswith(self):
        queryset = Person.objects.exclude(Person.full_name().startswith('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_startswith_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person').startswith('Lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_istartswith(self):
        queryset = Person.objects.filter(Person.full_name(ignore_case=True).startswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.full_name().istartswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_istartswith_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person', ignore_case=True).startswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.full_name(through='person').istartswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_istartswith(self):
        queryset = Person.objects.exclude(Person.full_name(ignore_case=True).startswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.full_name().istartswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_istartswith_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person', ignore_case=True).startswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Profile.objects.exclude(Person.full_name(through='person').istartswith('lautaro')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_endswith(self):
        queryset = Person.objects.filter(Person.full_name().endswith('Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_endswith_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person').endswith('Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_endswith(self):
        queryset = Person.objects.exclude(Person.full_name().endswith('Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_endswith_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person').endswith('Redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_iendswith(self):
        queryset = Person.objects.filter(Person.full_name(ignore_case=True).endswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.full_name().iendswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_iendswith_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person', ignore_case=True).endswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.full_name(through='person').iendswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_iendswith(self):
        queryset = Person.objects.exclude(Person.full_name(ignore_case=True).endswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.full_name().iendswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
    
    def test_queryset_orm_property_exclude_iendswith_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person', ignore_case=True).endswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Profile.objects.exclude(Person.full_name(through='person').iendswith('redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_range(self):
        queryset = Person.objects.filter(Person.total_notes().range([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])
        queryset = Person.objects.filter(Person.total_notes().range([6, 8])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_filter_range_with_through(self):
        queryset = Profile.objects.filter(Person.total_notes(through='person').range([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3, 7])
        queryset = Profile.objects.filter(Person.total_notes(through='person').range([6, 8])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [7])

    def test_queryset_orm_property_exclude_range(self):
        queryset = Person.objects.exclude(Person.total_notes().range([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])
        queryset = Person.objects.exclude(Person.total_notes().range([6, 8])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])

    def test_queryset_orm_property_exclude_range_with_through(self):
        queryset = Profile.objects.exclude(Person.total_notes(through='person').range([3, 7])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [])
        queryset = Profile.objects.exclude(Person.total_notes(through='person').range([6, 8])).values_list('total_notes', flat=True)
        self.assertEqual(list(queryset), [3])

    def test_queryset_orm_property_filter_regex(self):
        queryset = Person.objects.filter(Person.full_name().regex(f'^Lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_regex_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person').regex(f'^Lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_regex(self):
        queryset = Person.objects.exclude(Person.full_name().regex(f'^Lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_regex_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person').regex(f'^Lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_iregex(self):
        queryset = Person.objects.filter(Person.full_name(ignore_case=True).regex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Person.objects.filter(Person.full_name().iregex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_filter_iregex_with_through(self):
        queryset = Profile.objects.filter(Person.full_name(through='person', ignore_case=True).regex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])
        queryset = Profile.objects.filter(Person.full_name(through='person').iregex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    def test_queryset_orm_property_exclude_iregex(self):
        queryset = Person.objects.exclude(Person.full_name(ignore_case=True).regex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Person.objects.exclude(Person.full_name().iregex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_exclude_iregex_with_through(self):
        queryset = Profile.objects.exclude(Person.full_name(through='person', ignore_case=True).regex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])
        queryset = Profile.objects.exclude(Person.full_name(through='person').iregex(f'^lau*')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Gabriel Smith'])

    def test_queryset_orm_property_filter_date_range(self):
        queryset = Person.objects.filter(Person.birth_datetime().range([
            self.person1.datetime.date().__str__(),
            (self.person2.datetime.date() + timedelta(days=1)).__str__(),
        ])).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [
            self.person1.datetime,
            self.person2.datetime,
        ])

    def test_queryset_orm_property_filter_date_range_with_through(self):
        queryset = Profile.objects.filter(Person.birth_datetime(through='person').range([
            self.person1.datetime.date().__str__(),
            (self.person2.datetime.date() + timedelta(days=1)).__str__(),
        ])).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [
            self.person1.datetime,
            self.person2.datetime,
        ])

    def test_queryset_orm_property_exclude_date_range(self):
        queryset = Person.objects.exclude(Person.birth_datetime().range([
            self.person1.datetime.date().__str__(),
            self.person2.datetime.date().__str__(),
        ])).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person2.datetime])

    def test_queryset_orm_property_exclude_date_range_with_through(self):
        queryset = Profile.objects.exclude(Person.birth_datetime(through='person').range([
            self.person1.datetime.date().__str__(),
            self.person2.datetime.date().__str__(),
        ])).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person2.datetime])

    def test_queryset_orm_property_filter_date(self):
        queryset = Person.objects.filter(Person.birth_datetime().date(
            self.person1.datetime.date().__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person1.datetime])

    def test_queryset_orm_property_filter_date_with_through(self):
        queryset = Profile.objects.filter(Person.birth_datetime(through='person').date(
            self.person1.datetime.date().__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person1.datetime])

    def test_queryset_orm_property_exclude_date(self):
        queryset = Person.objects.exclude(Person.birth_datetime().date(
            self.person1.datetime.date().__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person2.datetime])

    def test_queryset_orm_property_exclude_date_with_through(self):
        queryset = Profile.objects.exclude(Person.birth_datetime(through='person').date(
            self.person1.datetime.date().__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person2.datetime])

    def test_queryset_orm_property_filter_year(self):
        queryset = Person.objects.filter(Person.birth_datetime().year(
            self.person1.datetime.year.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [
            self.person1.datetime,
            self.person2.datetime,
        ])

    def test_queryset_orm_property_filter_year_with_through(self):
        queryset = Profile.objects.filter(Person.birth_datetime(through='person').year(
            self.person1.datetime.year.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [
            self.person1.datetime,
            self.person2.datetime,
        ])

    def test_queryset_orm_property_exclude_year(self):
        queryset = Person.objects.exclude(Person.birth_datetime().year(
            self.person1.datetime.year.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_exclude_year_with_through(self):
        queryset = Profile.objects.exclude(Person.birth_datetime(through='person').year(
            self.person1.datetime.year.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [])

    def test_queryset_orm_property_filter_day(self):
        queryset = Person.objects.filter(Person.birth_datetime().day(
            self.person1.datetime.day.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person1.datetime])

    def test_queryset_orm_property_filter_day_with_through(self):
        queryset = Profile.objects.filter(Person.birth_datetime(through='person').day(
            self.person1.datetime.day.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person1.datetime])

    def test_queryset_orm_property_exclude_day(self):
        queryset = Person.objects.exclude(Person.birth_datetime().day(
            self.person1.datetime.day.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person2.datetime])

    def test_queryset_orm_property_exclude_day_with_through(self):
        queryset = Profile.objects.exclude(Person.birth_datetime(through='person').day(
            self.person1.datetime.day.__str__()),
        ).values_list('birth_datetime', flat=True)
        self.assertEqual(list(queryset), [self.person2.datetime])

    @skip('Implement check for database usage, this should only work on postgres')
    def test_queryset_orm_property_filter_search(self):
        # FIXME
        queryset = Person.objects.filter(Person.full_name().search(f'redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    @skip('Implement check for database usage, this should only work on postgres')
    def test_queryset_orm_property_filter_search_with_through(self):
        # FIXME
        queryset = Profile.objects.filter(Person.full_name(through='person').search(f'redbear')).values_list('full_name', flat=True)
        self.assertEqual(list(queryset), ['Lautaro Redbear'])

    # @skip('FIXME, this should annotate the clause before and then apply a filter')
    def test_queryset_orm_property_annotate_case_when(self):
        queryset = Person.objects.annotate(Person.full_name()).annotate(
            case_when=Case(
                When(full_name__icontains='redbear', then=Value(True)),
                default=Value(False),
            ),
        ).filter(case_when=True)
        self.assertEqual(list(queryset), [self.person1])
        queryset = Person.objects.annotate(
            Person.full_name(),
            case_when=Case(
                When(full_name__icontains='redbear', then=Value(True)),
                default=Value(False),
            ),
        ).filter(case_when=True)
        self.assertEqual(list(queryset), [self.person1])
        # FIXME
        # queryset = Person.objects.annotate(
        #     case_when=Case(
        #         When(Person.full_name().contains('redbear'), then=Value(True)),
        #         default=Value(False),
        #     ),
        # ).filter(case_when=True)
        # self.assertEqual(list(queryset), [self.person1])