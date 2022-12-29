from copy import deepcopy
from datetime import datetime
from re import fullmatch

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.http import HttpResponse
from twilio.twiml.voice_response import Play, VoiceResponse

from eastbay_massage.settings import CONTACT_EMAIL, CONTACT_NUMBER
from eastbay_massage.settings import EMAIL_ENABLED, EMAIL_HOST_USER
from eastbay_massage.forms import EmailForm

CONTACT_INFO = {
  'contact_email': CONTACT_EMAIL,
  'contact_number': CONTACT_NUMBER,
  'contact_number_no_space': CONTACT_NUMBER.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
}

EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

def home(request):
  return render(request, 'home.html', CONTACT_INFO)

def about(request):
  return render(request, 'about.html', CONTACT_INFO)

def message_successful(request):
  return render(request, 'message.html', CONTACT_INFO)

def send_message(request):
  form = EmailForm()
  return_data = deepcopy(CONTACT_INFO)
  if request.method=='POST':
    form = EmailForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        if EMAIL_ENABLED:
          send_mail(
            f'Web Form Message {datetime.now()}',
            f'From: {data.get("email")}\nMessage: {data.get("message")}',
            EMAIL_HOST_USER,
            [CONTACT_EMAIL],
            fail_silently=False,
          )
        else:
          print('data', cd)
        return HttpResponseRedirect('/message_successful/')
    else:
      return_data['errors'] = form.errors
  return render(request, 'home.html', return_data)