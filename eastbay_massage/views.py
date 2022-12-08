from django.shortcuts import render
from django.http import HttpResponse
from twilio.twiml.voice_response import Play, VoiceResponse

from eastbay_massage.settings import CONTACT_EMAIL, CONTACT_NUMBER

CONTACT_INFO = {
  'contact_email': CONTACT_EMAIL,
  'contact_number': CONTACT_NUMBER,
  'contact_number_no_space': CONTACT_NUMBER.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
}

def home(request):
  return render(request, 'home.html', CONTACT_INFO)