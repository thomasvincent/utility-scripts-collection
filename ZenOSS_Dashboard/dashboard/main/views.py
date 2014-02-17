from django.http import *
from django.db.models import *
from models import *
from django.template import Context, loader
# Create your views here.

def index(request):
    devices = zenoss_device.objects.all()
    t = loader.get_template('device_list.html')
    c = Context({'devices':devices})
    return HttpResponse(t.render(c))

def device_details(request, device_id):
    try:
        dev = zenoss_device.objects.get(id=device_id)
        device_uid = dev.uid
        dev_templates = dev.templates.all()
        t = loader.get_template('device_details.html')
        c = Context(
            {'device_uid' : device_uid, 'device_templates' : dev_templates, 'device_id' : dev.id}
        )
        return HttpResponse(t.render(c))
    except ObjectDoesNotExist:
        return HttpResponse('No such device! It means that something went wrong.')

def device_template_details(request, device_id, template_id):
    dev = zenoss_device.objects.get(id=device_id)
    tpl = dev.templates.get(id=template_id)
    ### Django template vars ###
    device_name = dev.name
    device_uid = dev.uid
    template_text = tpl.text
    template_uid = tpl.uid
    template_path = tpl.path
    datapoints = tpl.datapoints.all()
    performance_data = {}
    for dp in datapoints:
        rrdpf = zenoss_rrd_performance_point.objects.filter(device=dev, template=tpl, datasource_details=dp)
        performance_data[dp.name] = rrdpf
    ############################
    t = loader.get_template('device_template_details.html')
    c = Context(
        {'device_name' : device_name,
         'device_uid' : device_uid,
         'template_text' : template_text,
         'template_path' : template_path,
         'template_uid' : template_uid,
         'datapoints' : datapoints,
         'pf_data' : performance_data,
         'device_obj' : dev,
         'template_obj' : tpl,}
    )
    return HttpResponse(t.render(c))