from __future__ import division, print_function, absolute_import, \
    unicode_literals

from django.contrib import admin
from django.conf.urls import url, include, patterns

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'toys.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),

                       url(r'^admin/', include(admin.site.urls)),
                       )
