from django.db import models


class TestModel(models.Model):

    big_integer_field = models.BigIntegerField()

    binary_field = models.BinaryField()

    boolean_field = models.BooleanField()

    char_field = models.CharField(
        max_length=200,
    )

    date_field = models.DateField()

    datetime_field = models.DateTimeField()

    decimal_field = models.DecimalField(
        decimal_places=2,
        max_digits=8,
    )

    email_field = models.EmailField()

    float_field = models.FloatField()

    integer_field = models.IntegerField()

    null_boolean_field = models.NullBooleanField()

    positive_integer_field = models.PositiveIntegerField()

    positive_small_integer_field = models.PositiveSmallIntegerField()

    slug_field = models.SlugField()

    small_integer_field = models.SmallIntegerField()

    text_field = models.TextField()

    time_field = models.TimeField()

    url_field = models.URLField()
