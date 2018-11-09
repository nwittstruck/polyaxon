from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from hestia.service_interface import Service

from ownership import OwnershipError


class OwnershipService(Service):
    __all__ = ('setup',
               'set_owner',
               'set_default_owner',
               'create_owner',
               'delete_owner',
               'validate_owner_name')

    def __init__(self):
        self.content_type_manager = None

    @staticmethod
    def check_owner_type(owner=None, owner_type=None):
        owner_type = owner.owner_type if owner else owner_type
        if not owner_type or owner_type not in settings.OWNER_TYPES:
            raise OwnershipError('Received an invalid owner type `{}`.'.format(owner.owner_type))

    def set_default_owner(self, instance):
        if settings.ALLOW_USER_PROJECTS:
            try:
                self.set_owner(instance=instance, owner_obj=instance.user)
            except OwnershipError:
                raise OwnershipError('You are not allowed to create a project, '
                                     'please contact your admin.')
        else:
            raise OwnershipError('You are not allowed to create a project, '
                                 'please contact your admin.')

    def set_owner(self, instance, owner=None, owner_name=None, owner_obj=None, commit=False):
        if owner:
            owner = owner
        elif owner_name:
            try:
                owner = self.owner_manager.get(name=owner_name)
            except ObjectDoesNotExist:
                raise OwnershipError('Could not set an owner, owner name not found.')
        elif owner_obj:
            try:
                owner = self.owner_manager.get(
                    object_id=owner_obj.id,
                    content_type_id=self.content_type_manager.get_for_model(owner_obj).id)
            except ObjectDoesNotExist:
                raise OwnershipError('Could not set an owner, owner name not found.')

        self.check_owner_type(owner=owner)
        instance.owner = owner
        if commit:
            instance.save(update_fields=['object_id', 'content_type_id'])

    def create_owner(self, owner_obj, name):
        self.owner_manager.create(
            name=name,
            object_id=owner_obj.id,
            content_type_id=self.content_type_manager.get_for_model(owner_obj).id)

    def delete_owner(self, name):
        try:
            self.owner_manager.get(name=name).delete()
        except ObjectDoesNotExist:
            # Fail silently
            pass

    def validate_owner_name(self, name):
        if self.owner_manager.filter(name=name).exists():
            raise ValidationError('The given name is already taken.')

    def setup(self):
        super().setup()
        from db.models.owner import Owner
        from django.contrib.contenttypes.models import ContentType

        self.owner_manager = Owner.objects
        self.content_type_manager = ContentType.objects
