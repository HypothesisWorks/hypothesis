# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django.urls import include, re_path

patterns, namespace, name = admin.site.urls

urlpatterns = [
    # Examples:
    # url(r'^$', 'toys.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    re_path(r"^admin/", include((patterns, name), namespace=namespace))
]
