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

from chatpj.const import GEMINI_API_KEY,GEMINI_API_MODEL
from chatpj.utils import extract_title, getChatGenrateSetting, getChatSetting, getChatSetting_fallback, getDefaultReportPrompt, split_text_by_chars

test = ""

class TestRun (APIView): 

    def get(self, req: HttpRequest):
        print("TEST")
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_API_MODEL, contents="Explain how LLM works"
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

        chat = client.chats.create(model=GEMINI_API_MODEL,
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

        story_id = request.query_params.get('story_id')
        kid_id = request.query_params.get('kid_id')

        if kid_id:
            try:
                kid_id = int(kid_id)
            except ValueError:
                return Response(
                    {'error': 'kid_id must be an integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if user.user_type != UserTable.UserType.PARENT:
                return Response(
                    {'error': 'Only parents can access or create stories for kids'},
                    status=status.HTTP_403_FORBIDDEN
                )

            try:
                kid = UserTable.objects.get(
                    user_id=kid_id,
                    user_type=UserTable.UserType.KID,
                    parent_id=user.user_id
                )
            except UserTable.DoesNotExist:
                return Response(
                    {'error': 'Kid not found or not associated with this parent'},
                    status=status.HTTP_404_NOT_FOUND
                )

            user = kid
            user_id = kid_id
            print(f"Parent {user.user_name} accessing story for kid {kid.user_name}")

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

        user_story = UserStory.objects.filter(
            user_id=user_id,
            story_id=story_id,
            user_story_status=UserStory.Status.ACTIVE
        ).prefetch_related(
            Prefetch('entries', queryset=UserStoryEntry.objects.filter(entry_status=UserStoryEntry.Status.ACTIVE))
        ).first()

        if user_story:
            serializer = UserStorySerializer(user_story)
            return Response({
                'status': 'SUCCESS',
                'data': serializer.data
            })

        try:
            story_temp = StoryTemp.objects.get(story_id=story_id)
        except StoryTemp.DoesNotExist:
            return Response(
                {'error': 'Story not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            with transaction.atomic():
                user_story = UserStory.objects.create(
                    story=story_temp,
                    user=user,
                    user_story_status=UserStory.Status.ACTIVE
                )

                UserStoryEntry.objects.create(
                    user_story=user_story,
                    entry_title=f"{story_temp.story_title} - Introduction",
                    entry_content=story_temp.story_start,
                    entry_role=UserStoryEntry.Role.AI,
                    entry_status=UserStoryEntry.Status.ACTIVE
                )

                if story_temp.story_content:
                    UserStoryEntry.objects.create(
                        user_story=user_story,
                        entry_title=f"{story_temp.story_title} (1)",
                        entry_content=story_temp.story_content,
                        entry_role=UserStoryEntry.Role.AI,
                        entry_status=UserStoryEntry.Status.ACTIVE
                    )
        except Exception as e:
            return Response({'error': f'Failed to create story entries: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = UserStorySerializer(user_story)
        return Response({
            'status': 'SUCCESS',
            'data': serializer.data
        })

class RetraceStoryChat(APIView):
    def post(self, request):
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

        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = request.data

        user_story_id = data.get('user_story_id')
        user_story_entry_id = data.get('user_story_entry_id')

        if not user_story_id or not user_story_entry_id:
            return Response({'error': 'user_story_id and user_story_entry_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_story = UserStory.objects.get(
                user_story_id=user_story_id,
                user_id=user_id,
                user_story_status=UserStory.Status.ACTIVE,
            )
        except UserStory.DoesNotExist:
            return Response({'error': 'User story not found or not active.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            selected = UserStoryEntry.objects.get(
                user_story=user_story,
                user_story_entry_id=user_story_entry_id,
                entry_status=UserStoryEntry.Status.ACTIVE,
            )
        except UserStoryEntry.DoesNotExist:
            return Response({'error': 'Story entry not found.'}, status=status.HTTP_404_NOT_FOUND)


        if selected.entry_role != UserStoryEntry.Role.USER:
            return Response({'error': 'Can only retrace to a user message.'}, status=status.HTTP_400_BAD_REQUEST)


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


        entries = UserStoryEntry.objects.filter(
            user_story=user_story,
            entry_status=UserStoryEntry.Status.ACTIVE
        ).order_by('created_on')

        gemini_history = []


        addChatSetting = getChatSetting(chat_tem)
        for temItem in addChatSetting:
            gemini_history.append(
                types.Content(
                    role='user',
                    parts=[types.Part(text=temItem)]
                )
            )

      
        for entry in entries:
            gemini_role = "user" if entry.entry_role == UserStoryEntry.Role.USER else "model"
            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=entry.entry_content)]
                )
            )

        chat = client.chats.create(model=GEMINI_API_MODEL,
                                history=gemini_history)

        response_stream = chat.send_message_stream(user_message)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text

   
        UserStoryEntry.objects.create(
            user_story=user_story,
            entry_title="User Input",
            entry_content=user_message.strip(),
            entry_role=UserStoryEntry.Role.USER,
            entry_status=UserStoryEntry.Status.ACTIVE
        )

       
        UserStoryEntry.objects.create(
            user_story=user_story,
            entry_title=extract_title(full_response_text.strip()),
            entry_content=full_response_text.strip(),
            entry_role=UserStoryEntry.Role.AI,
            entry_status=UserStoryEntry.Status.ACTIVE
        )

        
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

        addChatSetting = getChatSetting_fallback(chat_tem)

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
            print("Adding to history - Role:", gemini_role, "Content:", content)
            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)]
                )
            )

        chat = client.chats.create(model=GEMINI_API_MODEL,
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
                'nickname': user.user_nickname,
                'type': user.get_user_type_display(),
                'status': user.get_user_status_display()
            }
        }, status=status.HTTP_200_OK)
    


class getChildrenListByParentId(APIView):
    def get(self, request):
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

        parent_id = user_id

        if not parent_id:
            return Response({'error': 'parent_id parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parent_id = int(parent_id)
        except ValueError:
            return Response({'error': 'parent_id must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            parent = UserTable.objects.get(user_id=parent_id, user_type=UserTable.UserType.PARENT)
        except UserTable.DoesNotExist:
            return Response({'error': 'Parent user not found.'}, status=status.HTTP_404_NOT_FOUND)

        
        try:
            children = UserTable.objects.filter(
                parent_id=parent_id,
                user_type=UserTable.UserType.KID,
                user_status=UserTable.UserStatus.ACTIVE
            ).order_by('user_name')
        except Exception as e:
            return Response({'error': f'Error retrieving children: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        children_data = [
            {
                'user_id': child.user_id,
                'user_name': child.user_name,
                'user_nickname': child.user_nickname,
                'user_type': child.get_user_type_display(),
                'user_status': child.get_user_status_display(),
                'created_on': child.created_on,
            }
            for child in children
        ]

        return Response({
            'status': 'SUCCESS',
            'parent_id': parent_id,
            'parent_name': parent.user_name,
            'children': children_data,
            'total': len(children_data)
        }) 
    

class GetKidStoryRecords(APIView):
    def get(self, request):
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

        kid_id = request.query_params.get('kid_id')

        if not kid_id:
            return Response({'error': 'kid_id parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            kid_id = int(kid_id)
        except ValueError:
            return Response({'error': 'kid_id must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            kid = UserTable.objects.get(user_id=kid_id, user_type=UserTable.UserType.KID)
        except UserTable.DoesNotExist:
            return Response({'error': 'Kid user not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        
        try:
            stories = UserStory.objects.filter(
                user_id=kid_id,
                user_story_status=UserStory.Status.ACTIVE
            ).order_by('-created_on')
        except Exception as e:
            return Response({'error': f'Error retrieving stories: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        stories_data = []
        for story in stories:
            stories_data.append({
                'user_story_id': story.user_story_id,
                'story_id': story.story.story_id,
                'story_title': story.story.story_title,
                'created_on': story.created_on,
            })

        return Response({
            'status': 'SUCCESS',
            'kid_id': kid_id,
            'stories': stories_data,
            'total': len(stories_data)
        }) 


class GenOrGetReportFromStory(APIView):
    def get(self, request):
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

        user_story_id = request.query_params.get('user_story_id')

        if not user_story_id:
            return Response({'error': 'user_story_id parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        getReportFromUserStory = UserStory.objects.filter(
            user_story_id=user_story_id,
            user_story_status=UserStory.Status.ACTIVE,
        ).first()

        if not getReportFromUserStory:
            return Response({'error': 'Report not found for the specified story.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'status': 'SUCCESS',
            'report': getReportFromUserStory.user_story_report
        })

    def post(self, request):
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
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON format.'}, status=status.HTTP_400_BAD_REQUEST)

        client = genai.Client(api_key=GEMINI_API_KEY)
        user_story_id = data.get('user_story_id')

        if not user_story_id:
            return Response({'error': 'user_story_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_story_entrys = UserStoryEntry.objects.filter(
            user_story_id=user_story_id,
            entry_status=UserStoryEntry.Status.ACTIVE
        ).order_by('created_on')

        report_request = getDefaultReportPrompt()
        gemini_history = []

        gemini_history.append(
                types.Content(
                    role='user',
                    parts=[types.Part(text=report_request)]
                )
            )

        
        for entry in user_story_entrys:
            gemini_role = "user" if entry.entry_role == UserStoryEntry.Role.USER else "model"
            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=entry.entry_content)]
                )
            )

        chat = client.chats.create(model=GEMINI_API_MODEL,
                                history=gemini_history)

        response_stream = chat.send_message_stream(report_request)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text

        UserStory.objects.filter(user_story_id=user_story_id).update(
            user_story_report=full_response_text.strip())

        return Response({
            'status': 'SUCCESS',
            'report': full_response_text.strip(),
        })



class GenerateStory(APIView):
    def post(self, request):
        client = genai.Client(api_key=GEMINI_API_KEY)
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
        data = request.data

        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        user_message = data.get('user_message', '').strip()

        if not title or not description:
            return Response({
                'status': 'ERROR',
                'message': 'Title and description are required'
            }, status=400)

        if not user_message:
            return Response({
                'status': 'ERROR',
                'message': 'No msg input'
            }, status=400)

        gemini_history = []

        addChatSetting = getChatGenrateSetting()

        for temItem in addChatSetting:
            gemini_history.append(
                types.Content(
                    role='user',
                    parts=[types.Part(text=temItem)]
                )
            )

        defaultResponse = """Please tell me the story setting you want to create (the more detailed the better). I will not return HTML story, just the story setting. """

        gemini_history.append(
                types.Content(
                    role='model',
                    parts=[types.Part(text=defaultResponse)]
                )
            )

        chat = client.chats.create(model=GEMINI_API_MODEL,
                                history=gemini_history)
        
        mix_user_msg = f"Title: {title}\nDescription: {description}\nSetting: {user_message}"

        response_stream = chat.send_message_stream(mix_user_msg)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text



        return Response({
            'status': 'SUCCESS',
            'story_temp': full_response_text.strip(),

        })
    

class GenerateStoryIntro(APIView):
    def post(self, request):
        client = genai.Client(api_key=GEMINI_API_KEY)
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
        data = request.data

        user_storysetting = data.get('user_storysetting', '').strip()
        if not user_storysetting:
            return Response({
                'status': 'ERROR',
                'message': 'No story setting input'
            }, status=400)
        
        ArrTemp = split_text_by_chars(user_storysetting, 5)

        gemini_history = []

        for msg in ArrTemp:
            content = msg.strip()
            gemini_role = "user"
            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)]
                )
            )

        chat = client.chats.create(model=GEMINI_API_MODEL,
                                history=gemini_history)
        
        default_story_intro_prompt ="First, generate a creative and engaging introduction for a children's story based on the following setting: " + user_storysetting + " The introduction should be suitable for children, capturing their imagination and setting the stage for an exciting adventure. Please provide a vivid and captivating opening that draws young readers into the world of the story."

        response_stream = chat.send_message_stream(default_story_intro_prompt)

        full_response_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_response_text += chunk.text

        return Response({
            'status': 'SUCCESS',
            'story_intro': full_response_text.strip(),
        })
    

class GenerateStoryToDB(APIView):
    def post(self, request):
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
        data = request.data

        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        user_storysetting = data.get('user_storysetting', '').strip()
        user_storysetting_intro = data.get('user_storysetting_intro', '').strip()
        tag1 = data.get('tag1', '').strip()
        tag2 = data.get('tag2', '').strip()
        tag3 = data.get('tag3', '').strip()

        if not title:
            return Response({
                'status': 'ERROR',
                'message': 'Title is required'
            }, status=400)
        
        if not description:
            return Response({
                'status': 'ERROR',
                'message': 'Description is required'
            }, status=400)
        if not tag1:
            return Response({
                'status': 'ERROR',
                'message': 'At least one tag is required'
            }, status=400)
        

        if not user_storysetting or not user_storysetting_intro:
            return Response({
                'status': 'ERROR',
                'message': 'Story setting and introduction are required'
            }, status=400)
        
        ArrTemp = split_text_by_chars(user_storysetting, 5)

        try:
            story_temp = StoryTemp.objects.create(
                story_title=title,
                story_description=description,
                story_start=user_storysetting_intro,
                story_tag_1=tag1,
                story_tag_2=tag2 if tag2 else None,
                story_tag_3=tag3 if tag3 else None,
                story_setting_1=ArrTemp[0],
                story_setting_2=ArrTemp[1],
                story_setting_3=ArrTemp[2],
                story_setting_4=ArrTemp[3],
                story_setting_5=ArrTemp[4],
            )
        except Exception as e:
            return Response({'error': f'Failed to save story template: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'SUCCESS',
            'story_temp_id': story_temp.story_id,
            'story_title': story_temp.story_title,
        })
        
        

