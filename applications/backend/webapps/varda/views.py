from django.http import HttpResponse
from django.shortcuts import render


"""
General
"""


def index(request):
    return render(request, "varda/base.html")


def varda_index(request):
    return HttpResponse("Varda index.")


def varda_release_notes(request):
    return render(request, "varda/release_notes.html")


def ping(request):
    return HttpResponse("Pong!")
