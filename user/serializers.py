from rest_framework import serializers

from user.models import User, Banner


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['name', 'image', 'image_web', 'external_link']
    
    def to_representation(self, instance):
        # Get the default representation first
        representation = super().to_representation(instance)
        
        # If image_web is None or empty, fallback to image
        if not representation.get('image_web'):
            representation['image_web'] = representation.get('image')
        
        return representation