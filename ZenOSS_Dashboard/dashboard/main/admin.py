from django.contrib import admin
from models import *


admin.site.register(zenoss_location)
admin.site.register(zenoss_device)
admin.site.register(zenoss_rrd_template)
admin.site.register(zenoss_rrd_datasource)
admin.site.register(zenoss_rrd_performance_point)