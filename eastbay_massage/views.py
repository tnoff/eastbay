from copy import deepcopy
from datetime import datetime
import logging

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseForbidden

from eastbay_massage.settings import CONTACT_EMAIL, CONTACT_NUMBER
from eastbay_massage.settings import EMAIL_ENABLED, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from eastbay_massage.forms import EmailForm

CONTACT_INFO = {
  'contact_email': CONTACT_EMAIL,
  'contact_number': CONTACT_NUMBER,
  'contact_number_no_space': CONTACT_NUMBER.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
}

logger = logging.getLogger(__name__)

def home(request):
  data = deepcopy(CONTACT_INFO)
  data['show_contact'] = False
  data['form'] = EmailForm()
  return render(request, 'home.html', data)

def message_successful(request):
  return render(request, 'message.html')

def send_message(request):
  form = EmailForm()
  return_data = deepcopy(CONTACT_INFO)
  if request.method=='POST':
    form = EmailForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        # Clean phone number
        cd['phone_number'] = str(cd['phone_number'])
        if EMAIL_ENABLED:
          send_mail(
            subject = f'Web Form Message {datetime.now()}',
            message = f'From: {cd.get("email")}\nName: {cd.get("name")}\nPhone Number: {cd.get("phone_number")}\nMessage: {cd.get("message")}',
            from_email = EMAIL_HOST_USER,
            recipient_list = [CONTACT_EMAIL,],
            auth_user = EMAIL_HOST_USER,
            auth_password = EMAIL_HOST_PASSWORD,
            fail_silently = False,
          )
        else:
          print('data', cd)
        return HttpResponseRedirect('/message_successful/')
    else:
      return_data['form'] = form
  return_data['show_contact'] = True
  return render(request, 'home.html', return_data)

@csrf_exempt
def log_csrf_attempt(request):
    if request.method == "POST" and 'csrfmiddlewaretoken' not in request.POST:
        logger.warning("CSRF violation attempt detected.")
        logger.warning("IP: %s", request.META.get("REMOTE_ADDR"))
        logger.warning("Headers: %s", dict(request.headers))
        logger.warning("POST data: %s", request.POST.dict())
        return HttpResponseForbidden("CSRF token missing.")