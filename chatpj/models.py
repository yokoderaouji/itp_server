from django.db import models


class UserTable(models.Model):

    class UserType(models.TextChoices):
        KID = 'kid', 'Kid'
        PARENT = 'parent', 'Parent'

    class UserStatus(models.TextChoices):
        ACTIVE = 'Y', 'Active'
        INACTIVE = 'N', 'Inactive'
        LOCKED = 'L', 'Locked'

    user_id = models.AutoField(primary_key=True)
    user_type = models.CharField(
        max_length=6,
        choices=UserType.choices,
    )
    user_name = models.CharField(max_length=63)
    user_nickname = models.CharField(max_length=63)
    user_password = models.CharField(max_length=63)
    parent_id = models.IntegerField(blank=True, null=True)
    user_status = models.CharField(
        max_length=1,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_table'

class StoryTemp(models.Model):

    class StoryTempStatus(models.TextChoices):
        ACTIVE = 'Y', 'Active'
        INACTIVE = 'N', 'Inactive'
        LOCKED = 'L', 'Locked'

    story_id = models.AutoField(primary_key=True)
    story_title     = models.CharField(max_length=255)
    story_description = models.CharField(max_length=1023,default="")
    story_content   = models.TextField(blank=True, null=True)
    story_start     = models.TextField()
    story_setting_1 = models.TextField()
    story_setting_2 = models.TextField(blank=True, null=True)
    story_setting_3 = models.TextField(blank=True, null=True)
    story_setting_4 = models.TextField(blank=True, null=True)
    story_setting_5 = models.TextField(blank=True, null=True)
    story_tag_1     = models.CharField(max_length=15,default="")
    story_tag_2     = models.CharField(max_length=15, blank=True, null=True)
    story_tag_3     = models.CharField(max_length=15, blank=True, null=True)
    story_status    = models.CharField(
        max_length=6,
        choices=StoryTempStatus.choices,
        default=StoryTempStatus.ACTIVE,
    )
    created_on      = models.DateTimeField(auto_now_add=True)
    updated_on      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'story_temp'


class UserStory(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'Y', 'Active'
        INACTIVE = 'N', 'Inactive'
        LOCKED = 'L', 'Locked'

    user_story_id = models.AutoField(primary_key=True)
    story = models.ForeignKey(
        StoryTemp,
        on_delete=models.CASCADE,
        db_column='story_id',
        related_name='user_stories',
    )
    user = models.ForeignKey(
        UserTable,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='stories',
    )
    user_story_report = models.TextField(blank=True, null=True)
    user_story_status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_story'
    
class UserStoryEntry(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'Y', 'Active'
        INACTIVE = 'N', 'Inactive'
        LOCKED = 'L', 'Locked'

    class Role(models.TextChoices):
        USER = 'user', 'User'
        AI = 'ai', 'AI'

    user_story_entry_id = models.AutoField(primary_key=True)
    user_story = models.ForeignKey(
        UserStory,
        on_delete=models.CASCADE,
        db_column='user_story_id',
        related_name='entries',
    )
    entry_status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    entry_title = models.CharField(max_length=255,default="")
    entry_content = models.TextField()
    entry_role = models.CharField(
        max_length=4,
        choices=Role.choices,
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_story_entry'




class ParentKid(models.Model):

    parent_kid_id = models.AutoField(primary_key=True)
    parent = models.ForeignKey(
        UserTable,
        on_delete=models.CASCADE,
        db_column='parent_id',
        related_name='kids',
    )
    kid = models.ForeignKey(
        UserTable,
        on_delete=models.CASCADE,
        db_column='kid_id',
        related_name='parents',
    )

    class Meta:
        db_table = 'parent_kid_table'
