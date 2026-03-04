from django.db import models


class UserTable(models.Model):
    """Corresponds to the `user_table` SQL definition.

    1. user_type: kid or parent
    2. user_status: Y (active), N (inactive), L (locked)
    """

    class UserType(models.TextChoices):
        KID = 'kid', 'Kid'
        PARENT = 'parent', 'Parent'

    class UserStatus(models.TextChoices):
        ACTIVE = 'Y', 'Active'
        INACTIVE = 'N', 'Inactive'
        LOCKED = 'L', 'Locked'

    # use AutoField so Django handles auto-increment and object is saved
    user_id = models.AutoField(primary_key=True)
    user_type = models.CharField(
        max_length=6,
        choices=UserType.choices,
    )
    user_name = models.CharField(max_length=63)
    user_password = models.CharField(max_length=63)
    user_status = models.CharField(
        max_length=1,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_table'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return f"{self.user_name} ({self.get_user_type_display()})"


class StoryTemp(models.Model):
    """Represents the `story_temp` table.

    Fields correspond directly to the SQL DDL provided.
    """

    class StoryTempStatus(models.TextChoices):
        ACTIVE = 'Y', 'Active'
        INACTIVE = 'N', 'Inactive'
        LOCKED = 'L', 'Locked'

    story_id = models.AutoField(primary_key=True)
    story_title     = models.CharField(max_length=255)
    story_description = models.CharField(max_length=1023,default="")
    story_content   = models.TextField()
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
        verbose_name = 'story'
        verbose_name_plural = 'stories'

    def __str__(self):
        return self.story_title


class UserStory(models.Model):
    """Maps to the `user_story` table in the database."""

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
    user_story_status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_story'
        verbose_name = 'user story'
        verbose_name_plural = 'user stories'

    def __str__(self):
        return f"{self.user} - {self.story} ({self.get_user_story_status_display()})"
    


class UserStoryEntry(models.Model):
    """Corresponds to the `user_story_entry` table."""

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
        verbose_name = 'user story entry'
        verbose_name_plural = 'user story entries'

    def __str__(self):
        return f"{self.user_story} ({self.get_entry_role_display()})"


