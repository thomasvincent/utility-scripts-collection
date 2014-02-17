from django.db import models
from datetime import datetime
import time

# Create your models here.

class zenoss_rrd_datasource(models.Model):
    id = models.AutoField(primary_key=True)
    uid = models.CharField(max_length=16384, blank=False, unique=True)
    id_text = models.CharField(max_length=16384, blank=False)
    name = models.CharField(max_length=256, blank=True)
    newId = models.CharField(max_length=256, blank=True)
    RRD_VALUE_TYPES = (
        (u'C', u'COUNTER'),
        (u'G', u'GAUGE'),
        (u'D', u'DERIVE'),
        (u'A', u'ABSOLUTE'),
    )
    rrdType = models.CharField(max_length=2, choices=RRD_VALUE_TYPES)
    type = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=16384, blank=True)

    def __unicode__(self):
        return self.name

class zenoss_rrd_template(models.Model):
    id = models.AutoField(primary_key=True)
    path = models.CharField(max_length=512, blank=True, unique=True)
    text = models.CharField(max_length=512, blank=True)
    uid = models.CharField(max_length=16384, blank=False, unique=False)
    datapoints = models.ManyToManyField(zenoss_rrd_datasource)
    def __unicode__(self):
        return self.text

class zenoss_location(models.Model):
    id = models.AutoField(primary_key=True)
    uid = models.CharField(max_length=16384)
    name = models.CharField(max_length=16384, unique=True)

    def __unicode__(self):
        return self.name

class zenoss_device(models.Model):
    id = models.AutoField(primary_key=True)
    uid = models.CharField(max_length=16384, unique=True)
    collector = models.CharField(max_length=256)
    ipAddress = models.BigIntegerField()
    ipAddressString = models.CharField(max_length=30)
    location = models.ForeignKey(zenoss_location, blank=True)
    name = models.CharField(max_length=16384)
    templates = models.ManyToManyField(zenoss_rrd_template, blank=True)

    def __unicode__(self):
        return self.uid

class zenoss_rrd_performance_point(models.Model):
    id = models.AutoField(primary_key=True)
    template = models.ForeignKey(zenoss_rrd_template, blank=False)
    datasource_details = models.ForeignKey(zenoss_rrd_datasource, blank=False)
    device = models.ForeignKey(zenoss_device, blank=False)
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)
    value_int = models.BigIntegerField(blank=True, null=True)
    value_float = models.FloatField(blank=True, null=True)
    value_str = models.CharField(max_length=256, blank=True, null=True)

    def __unicode__(self):
        return self.device.uid + " :: " + str(self.timestamp) + " :: " + self.value_str

    def unixtm(self):
        return int(time.mktime(self.timestamp.timetuple())*1000)
