from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError, NotFound
from google import genai
from google.genai import types

from chatpj.const import GEMINI_API_KEY
from chatpj.utils import extract_title, getChatSetting


class TestRun (APIView): 

    def get(self, req: HttpRequest):
        print("TEST")
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents="Explain how LLM works"
        )
        print(response.text)
        return Response({'status': 'SUCCESS','response': response.text})
    

class TestRunChat (APIView): 

    def post(self, request):
        client = genai.Client(api_key=GEMINI_API_KEY)
        # try:
        data = request.data

        history = data.get('history', [])
        user_message = data.get('user_message', '').strip()

        if not user_message:
            return Response({
                'status': 'ERROR',
                'message': 'No msg input'
            }, status=400)

        gemini_history = []
        

        for msg in history:
            role = msg['sender'] 
            content = msg['text']

            gemini_role = "user" if role == "user" else "model"

            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)]
                )
            )

        chat = client.chats.create(model="gemini-2.5-flash",
                                history=gemini_history)

        response_stream = chat.send_message_stream(user_message)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text

        return Response({
            'status': 'SUCCESS',
            'current_reply': full_response_text.strip(),
            'history': history
        })
    


class StoryChat(APIView):
    def post(self, request):
        client = genai.Client(api_key=GEMINI_API_KEY)
        # try:
        data = request.data

        history = data.get('history', [])
        user_message = data.get('user_message', '').strip()

        chat_tem = data.get('chat_tem', '')

        if not user_message:
            return Response({
                'status': 'ERROR',
                'message': 'No msg input'
            }, status=400)

        gemini_history = []

        addChatSetting = getChatSetting(chat_tem)
        
        for temItem in addChatSetting:
            gemini_history.append(
                types.Content(
                    role='user',
                    parts=[types.Part(text=temItem)]
                )
            )

        for msg in history:
            role = msg['sender'] 
            content = msg['text']

            gemini_role = "user" if role == "user" else "model"

            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)]
                )
            )

        chat = client.chats.create(model="gemini-2.5-flash",
                                history=gemini_history)

        response_stream = chat.send_message_stream(user_message)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text



        return Response({
            'status': 'SUCCESS',
            'current_reply': full_response_text.strip(),
            'current_title':extract_title(full_response_text.strip()),
            'history': history
        })



        # except Exception as e:
        #     print("Gemini API error:", e)
        #     return Response({
        #         'status': 'ERROR',
        #         'message': '',
        #         'current_reply': ''
        #     }, status=500)