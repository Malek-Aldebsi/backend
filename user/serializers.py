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