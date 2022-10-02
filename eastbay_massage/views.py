from django.shortcuts import render
from django.http import HttpResponse
from twilio.twiml.voice_response import Play, VoiceResponse

from eastbay_massage.settings import CONTACT_EMAIL, CONTACT_NUMBER, RENDER_EXTERNAL_HOSTNAME

CONTACT_INFO = {
  'contact_email': CONTACT_EMAIL,
  'contact_number': CONTACT_NUMBER,
}

def home(request):
  return render(request, 'home.html', CONTACT_INFO)

def services(request):
  return render(request, 'services.html', CONTACT_INFO) 

def about(request):
  return render(request, 'about.html', CONTACT_INFO) 

def contact(request):
  return render(request, 'contact.html', CONTACT_INFO) 

def voicemail(request):
  response = VoiceResponse()
  response.play(f'{RENDER_EXTERNAL_HOSTNAME}/static/audio/voicemail.mp3')

  return HttpResponse(response, content_type='text/xml')