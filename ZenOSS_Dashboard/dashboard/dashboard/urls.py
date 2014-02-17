from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dashboard.views.home', name='home'),
    # url(r'^dashboard/', include('dashboard.foo.urls')),
    url(r'^$', 'main.views.index', name='home'),
    url(r'^device/(?P<device_id>\d+)/$', 'main.views.device_details', name='device_home'),
    url(r'^device/(?P<device_id>\d+)/templates/(?P<template_id>\d+)/$', 'main.views.device_template_details', name='template_details'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
