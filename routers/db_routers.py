from django.db.models import Model


class storyDBRouter:

    router_labels = {'chatpj'}
    db_name = 'story_db'

    def db_for_read(self, model:Model , **hints):
        if model._meta.app_label in self.router_labels: return self.db_name
        return None

    def db_for_write(self, model:Model , **hints):
        if model._meta.app_label in self.router_labels: return self.db_name
        return None
    
    def allow_relation(self, obj1: Model, obj2:Model, **hints):
        res1 = obj1._meta.app_label in self.router_labels
        res2 = obj2._meta.app_label in self.router_labels
        if res1 or res2: return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.router_labels: return False 
        """
        All non-auth models end up in this pool.
        """
        return True
