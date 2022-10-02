from django.shortcuts import render
from django.http import HttpResponse

from eastbay_massage.settings import CONTACT_EMAIL, CONTACT_NUMBER

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
