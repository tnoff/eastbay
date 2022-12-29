from copy import deepcopy
from re import fullmatch

from django.shortcuts import render
from django.http import HttpResponse
from twilio.twiml.voice_response import Play, VoiceResponse

from eastbay_massage.settings import CONTACT_EMAIL, CONTACT_NUMBER
from eastbay_massage.forms import EmailForm

CONTACT_INFO = {
  'contact_email': CONTACT_EMAIL,
  'contact_number': CONTACT_NUMBER,
  'contact_number_no_space': CONTACT_NUMBER.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
}

EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
MAX_MESSAGE_LENGTH = 1024 * 30

def home(request):
  return render(request, 'home.html', CONTACT_INFO)

def about(request):
  return render(request, 'about.html', CONTACT_INFO)

# https://docs.djangoproject.com/en/4.1/topics/email/
def send_message(request):
  form = EmailForm()
  if request.method=='POST':
    form = EmailForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        print('data', cd)
  return_data = deepcopy(CONTACT_INFO)
  return_data['errors'] = form.errors
  return render(request, 'home.html', return_data)