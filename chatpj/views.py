from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError, NotFound

# Create your views here.
class TestRun (APIView): 

    def get(self, req: HttpRequest):
        print("TEST")
        return Response({'status': 'SUCCESS'})