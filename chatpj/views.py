from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError, NotFound
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from google import genai
from google.genai import types
from .models import UserTable, StoryTemp, UserStory, UserStoryEntry
from .serializers import StoryTempSerializer, UserStorySerializer, UserStoryEntrySerializer
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch
import json

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
    
class GetStoryTemp(APIView):

    def get(self, request):
        # Check for Authorization header
        if 'Authorization' not in request.headers:
            return Response(
                {'error': 'Authorization header missing'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer '):
            return Response(
                {'error': 'Invalid authorization header'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(' ')[1]

        # Validate token and extract user_id
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = UserTable.objects.get(user_id=user_id)
        except (ObjectDoesNotExist, KeyError):
            return Response(
                {'error': 'Invalid token or user not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Filter: story_status must be 'Y' (Active) or 'L' (Locked)
        temps = StoryTemp.objects.filter(
            story_status__in=[StoryTemp.StoryTempStatus.ACTIVE, StoryTemp.StoryTempStatus.LOCKED]
        ).order_by('-created_on')

        serializer = StoryTempSerializer(temps, many=True)
        return Response({
            'status': 'SUCCESS',
            'count': temps.count(),
            'data': serializer.data
        })

class GetSingleStory(APIView):

    def get(self, request):
        story_id = request.query_params.get('story_id')

        if 'Authorization' not in request.headers:
            return Response(
                {'error': 'Authorization header missing'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer '):
            return Response(
                {'error': 'Invalid authorization header'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        token = auth_header.split(' ')[1]
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = UserTable.objects.get(user_id=user_id)
        except (ObjectDoesNotExist, KeyError):
            return Response(
                {'error': 'Invalid token or user not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            temp = StoryTemp.objects.get(
                story_id=story_id,  
                story_status__in=[StoryTemp.StoryTempStatus.ACTIVE]
            )
        except StoryTemp.DoesNotExist:
            return Response({'error': 'Story not found or not active'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StoryTempSerializer(temp)

        return Response({
            'status': 'SUCCESS',
            'data': serializer.data
        })

class SetUpNewStoryOrGetOldStory(APIView):
    """Set up a new story or retrieve existing user story with entries."""

    def get(self, request):
        # Authorization check
        if 'Authorization' not in request.headers:
            return Response(
                {'error': 'Authorization header missing'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer '):
            return Response(
                {'error': 'Invalid authorization header'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(' ')[1]

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = UserTable.objects.get(user_id=user_id)
        except (ObjectDoesNotExist, KeyError):
            return Response(
                {'error': 'Invalid token or user not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get story_id from query params
        story_id = request.query_params.get('story_id')
        if not story_id:
            return Response(
                {'error': 'story_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            story_id = int(story_id)
        except ValueError:
            return Response(
                {'error': 'story_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user_story exists and is active
        user_story = UserStory.objects.filter(
            user_id=user_id,
            story_id=story_id,
            user_story_status=UserStory.Status.ACTIVE
        ).prefetch_related(
            Prefetch('entries', queryset=UserStoryEntry.objects.filter(entry_status=UserStoryEntry.Status.ACTIVE))
        ).first()

        if user_story:
            # Return existing user_story with entries
            serializer = UserStorySerializer(user_story)
            return Response({
                'status': 'SUCCESS',
                'data': serializer.data
            })

        # Create new user_story
        try:
            story_temp = StoryTemp.objects.get(story_id=story_id)
        except StoryTemp.DoesNotExist:
            return Response(
                {'error': 'Story not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            with transaction.atomic():
                # Create UserStory; ensure it is saved before creating entries
                user_story = UserStory.objects.create(
                    story=story_temp,
                    user=user,
                    user_story_status=UserStory.Status.ACTIVE
                )

                # Create first entry: Introduction
                UserStoryEntry.objects.create(
                    user_story=user_story,
                    entry_title=f"{story_temp.story_title} - Introduction",
                    entry_content=story_temp.story_start,
                    entry_role=UserStoryEntry.Role.AI,
                    entry_status=UserStoryEntry.Status.ACTIVE
                )

                # Create second entry: Story content
                UserStoryEntry.objects.create(
                    user_story=user_story,
                    entry_title=f"{story_temp.story_title} (1)",
                    entry_content=story_temp.story_content,
                    entry_role=UserStoryEntry.Role.AI,
                    entry_status=UserStoryEntry.Status.ACTIVE
                )
        except Exception as e:
            # atomic block will roll back automatically
            return Response({'error': f'Failed to create story entries: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Return the new user_story with entries
        serializer = UserStorySerializer(user_story)
        return Response({
            'status': 'SUCCESS',
            'data': serializer.data
        })

class RetraceStoryChat(APIView):
    def post(self, request):
        # authenticate user
        if 'Authorization' not in request.headers:
            return Response({'error': 'Authorization header missing'}, status=status.HTTP_401_UNAUTHORIZED)
        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Invalid authorization header'}, status=status.HTTP_401_UNAUTHORIZED)
        token = auth_header.split(' ')[1]
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            _user = UserTable.objects.get(user_id=user_id)
        except (ObjectDoesNotExist, KeyError):
            return Response({'error': 'Invalid token or user not found'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        # parse payload (allow both raw JSON and DRF request.data)
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.data

        user_story_id = data.get('user_story_id')
        user_story_entry_id = data.get('user_story_entry_id')

        if not user_story_id or not user_story_entry_id:
            return Response({'error': 'user_story_id and user_story_entry_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # ensure story belongs to this user and is active
        try:
            user_story = UserStory.objects.get(
                user_story_id=user_story_id,
                user_id=user_id,
                user_story_status=UserStory.Status.ACTIVE,
            )
        except UserStory.DoesNotExist:
            return Response({'error': 'User story not found or not active.'}, status=status.HTTP_404_NOT_FOUND)

        # retrieve selected entry
        try:
            selected = UserStoryEntry.objects.get(
                user_story=user_story,
                user_story_entry_id=user_story_entry_id,
                entry_status=UserStoryEntry.Status.ACTIVE,
            )
        except UserStoryEntry.DoesNotExist:
            return Response({'error': 'Story entry not found.'}, status=status.HTTP_404_NOT_FOUND)

        # entry must be from the user
        if selected.entry_role != UserStoryEntry.Role.USER:
            return Response({'error': 'Can only retrace to a user message.'}, status=status.HTTP_400_BAD_REQUEST)

        # deactivate all later active entries for this story
        UserStoryEntry.objects.filter(
            user_story=user_story,
            created_on__gte=selected.created_on,
            entry_status=UserStoryEntry.Status.ACTIVE,
        ).update(entry_status=UserStoryEntry.Status.INACTIVE)

        return Response({
            'status': 'SUCCESS',
            'message': 'Chat retraced to selected user entry.',
            'retraced_entry_id': selected.user_story_entry_id
        })

class StoryChat(APIView):
    def post(self, request):
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        if 'Authorization' not in request.headers:
            return Response({'error': 'Authorization header missing'}, status=status.HTTP_401_UNAUTHORIZED)

        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Invalid authorization header'}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(' ')[1]

        try:
            access_token = AccessToken(token)
            print("Decoded token:", access_token)
            user_id = access_token['user_id']
            print("User ID from token:", user_id)
            user = UserTable.objects.get(user_id=user_id)
        except (ObjectDoesNotExist, KeyError):
            return Response({'error': 'Invalid token or user not found'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)



        data = request.data

        user_story_id = data.get('user_story_id')
        user_message = data.get('user_message', '').strip()
        chat_tem = data.get('chat_tem', '')

        if not user_story_id:
            return Response({
                'status': 'ERROR',
                'message': 'user_story_id is required'
            }, status=400)

        if not user_message:
            return Response({
                'status': 'ERROR',
                'message': 'No msg input'
            }, status=400)

        # Get user_story and verify ownership
        try:
            user_story = UserStory.objects.get(
                user_story_id=user_story_id,
                user_id=user_id,
                user_story_status=UserStory.Status.ACTIVE
            )
        except UserStory.DoesNotExist:
            return Response({
                'status': 'ERROR',
                'message': 'User story not found or not active'
            }, status=404)

        # Get history from user_story_entry, ordered by creation time
        entries = UserStoryEntry.objects.filter(
            user_story=user_story,
            entry_status=UserStoryEntry.Status.ACTIVE
        ).order_by('created_on')

        gemini_history = []

        # Add chat settings first
        addChatSetting = getChatSetting(chat_tem)
        for temItem in addChatSetting:
            gemini_history.append(
                types.Content(
                    role='user',
                    parts=[types.Part(text=temItem)]
                )
            )

        # Add history from entries
        for entry in entries:
            gemini_role = "user" if entry.entry_role == UserStoryEntry.Role.USER else "model"
            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=entry.entry_content)]
                )
            )

        chat = client.chats.create(model="gemini-2.5-flash",
                                history=gemini_history)

        response_stream = chat.send_message_stream(user_message)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text

        # Save the user input as an entry
        UserStoryEntry.objects.create(
            user_story=user_story,
            entry_title="User Input",
            entry_content=user_message.strip(),
            entry_role=UserStoryEntry.Role.USER,
            entry_status=UserStoryEntry.Status.ACTIVE
        )

        # Save the AI response as a new entry
        UserStoryEntry.objects.create(
            user_story=user_story,
            entry_title=extract_title(full_response_text.strip()),
            entry_content=full_response_text.strip(),
            entry_role=UserStoryEntry.Role.AI,
            entry_status=UserStoryEntry.Status.ACTIVE
        )

        # Fetch updated active history
        updated_entries = UserStoryEntry.objects.filter(
            user_story=user_story,
            entry_status=UserStoryEntry.Status.ACTIVE
        ).order_by('created_on')
        history_serializer = UserStoryEntrySerializer(updated_entries, many=True)

        return Response({
            'status': 'SUCCESS',
            'current_reply': full_response_text.strip(),
            'current_title': extract_title(full_response_text.strip()),
            'history': history_serializer.data,
        })


class StoryChat_old(APIView):
    def post(self, request):
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        if 'Authorization' not in request.headers:
            return Response({'error': 'Authorization header missing'}, status=status.HTTP_401_UNAUTHORIZED)

        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Invalid authorization header'}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(' ')[1]

        try:
            access_token = AccessToken(token)
            print("Decoded token:", access_token)
            user_id = access_token['user_id']
            print("User ID from token:", user_id)
            user = UserTable.objects.get(user_id=user_id)
        except (ObjectDoesNotExist, KeyError):
            return Response({'error': 'Invalid token or user not found'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)



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

class LoginFunction(APIView):
    def post(self, request):

        try:
            # Explicitly parse JSON from request body
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON format.'}, status=status.HTTP_400_BAD_REQUEST)

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        usertype = data.get('usertype', '').strip()
        try:
            user = UserTable.objects.get(
                user_name=username,
                user_type=usertype
            )
        except ObjectDoesNotExist:
            return Response({'error': 'Invalid username.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.user_status != UserTable.UserStatus.ACTIVE:
            return Response({'error': 'Account is inactive or locked.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.user_password != password:

            return Response({'error': 'Invalid password.'}, status=status.HTTP_401_UNAUTHORIZED)


        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful.',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'username': user.user_name,
                'type': user.get_user_type_display(),
                'status': user.get_user_status_display()
            }
        }, status=status.HTTP_200_OK)