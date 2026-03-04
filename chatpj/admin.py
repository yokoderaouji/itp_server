from django.contrib import admin
from .models import UserTable, StoryTemp, UserStory, UserStoryEntry


@admin.register(UserTable)
class UserTableAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'user_name', 'user_type', 'user_status', 'created_on')
    list_filter = ('user_type', 'user_status', 'created_on')
    search_fields = ('user_name',)
    readonly_fields = ('created_on', 'updated_on')


@admin.register(StoryTemp)
class StoryTempAdmin(admin.ModelAdmin):
    list_display = ('story_id', 'story_title', 'story_status', 'created_on')
    list_filter = ('story_status', 'created_on')
    search_fields = ('story_title',)
    readonly_fields = ('created_on', 'updated_on')
    fieldsets = (
        ('Basic Info', {
            'fields': ('story_id', 'story_title', 'story_description', 'story_status')
        }),
        ('Content', {
            'fields': ('story_content', 'story_start')
        }),
        ('Settings', {
            'fields': ('story_setting_1', 'story_setting_2', 'story_setting_3', 'story_setting_4', 'story_setting_5'),
            'classes': ('collapse',)
        }),
        ('Tags', {
            'fields': ('story_tag_1', 'story_tag_2', 'story_tag_3'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_on', 'updated_on'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserStory)
class UserStoryAdmin(admin.ModelAdmin):
    list_display = ('user_story_id', 'user', 'story', 'user_story_status', 'created_on')
    list_filter = ('user_story_status', 'created_on')
    search_fields = ('user__user_name', 'story__story_title')
    readonly_fields = ('created_on', 'updated_on')


@admin.register(UserStoryEntry)
class UserStoryEntryAdmin(admin.ModelAdmin):
    list_display = ('user_story_entry_id', 'user_story', 'entry_title', 'entry_role', 'entry_status', 'created_on')
    list_filter = ('entry_role', 'entry_status', 'created_on')
    search_fields = ('user_story__story__story_title', 'entry_title')
    readonly_fields = ('created_on', 'updated_on')
