# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

"""Django settings for toys project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/

"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

from __future__ import division, print_function, absolute_import

import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = u'o0zlv@74u4e3s+o0^h$+tlalh&$r(7hbx01g4^h5-3gizj%hub'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    u'django.contrib.admin',
    u'django.contrib.auth',
    u'django.contrib.contenttypes',
    u'django.contrib.sessions',
    u'django.contrib.messages',
    u'django.contrib.staticfiles',
    u'tests.django.toystore',
)

MIDDLEWARE_CLASSES = (
    u'django.contrib.sessions.middleware.SessionMiddleware',
    u'django.middleware.common.CommonMiddleware',
    u'django.middleware.csrf.CsrfViewMiddleware',
    u'django.contrib.auth.middleware.AuthenticationMiddleware',
    u'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    u'django.contrib.messages.middleware.MessageMiddleware',
    u'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = u'toys.urls'

WSGI_APPLICATION = u'toys.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    u'default': {
        u'ENGINE': u'django.db.backends.sqlite3',
        u'NAME': os.path.join(BASE_DIR, u'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = u'en-us'

TIME_ZONE = u'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = u'/static/'
