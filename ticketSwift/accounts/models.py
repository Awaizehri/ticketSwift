from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    CUSTOMER = 'customer'
    MANAGER = 'manager'
    ROLE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (MANAGER, 'Manager'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)