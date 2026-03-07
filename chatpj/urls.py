"""
URL configuration for itp_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from chatpj.views import StoryChat, TestRun, TestRunChat, LoginFunction, GetStoryTemp, GetSingleStory, SetUpNewStoryOrGetOldStory,RetraceStoryChat

urlpatterns = [
    path('', TestRun.as_view()),
    path('test', TestRunChat.as_view()),
    path('StoryChat', StoryChat.as_view()),
    path('GetSingleStory', GetSingleStory.as_view()),
    path('GetStoryTemp', GetStoryTemp.as_view()),
    path('RetraceStoryChat', RetraceStoryChat.as_view()),
    path('SetUpNewStoryOrGetOldStory', SetUpNewStoryOrGetOldStory.as_view()),
    path('Login', LoginFunction.as_view()),
]
