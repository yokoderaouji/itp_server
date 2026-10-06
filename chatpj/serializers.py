from rest_framework import serializers
from .models import StoryTemp, UserStory, UserStoryEntry


class StoryTempSerializer(serializers.ModelSerializer):

    class Meta:
        model = StoryTemp
        fields = [
            'story_id',
            'story_title',
            'story_description',
            'story_content',
            'story_start',
            'story_setting_1',
            'story_setting_2',
            'story_setting_3',
            'story_setting_4',
            'story_setting_5',
            'story_tag_1',
            'story_tag_2',
            'story_tag_3',
            'story_status',
            'created_on',
            'updated_on',
        ]
        read_only_fields = ['created_on', 'updated_on']


class UserStoryEntrySerializer(serializers.ModelSerializer):

    class Meta:
        model = UserStoryEntry
        fields = [
            'user_story_entry_id',
            'entry_title',
            'entry_content',
            'entry_role',
            'entry_status',
            'created_on',
            'updated_on',
        ]
        read_only_fields = ['created_on', 'updated_on']


class UserStorySerializer(serializers.ModelSerializer):

    entries = UserStoryEntrySerializer(many=True, read_only=True)

    class Meta:
        model = UserStory
        fields = [
            'user_story_id',
            'story',
            'user',
            'user_story_status',
            'created_on',
            'updated_on',
            'entries',
        ]
        read_only_fields = ['created_on', 'updated_on']

