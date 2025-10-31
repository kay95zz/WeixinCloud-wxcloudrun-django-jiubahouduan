from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'balance', 'points', 'avatar', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserBalancePointsSerializer(serializers.ModelSerializer):
    """用于修改余额和积分的序列化器"""
    class Meta:
        model = User
        fields = ['balance', 'points']
    
    def validate_balance(self, value):
        """验证余额不能为负数"""
        if value < 0:
            raise serializers.ValidationError("余额不能为负数")
        return value
    
    def validate_points(self, value):
        """验证积分不能为负数"""
        if value < 0:
            raise serializers.ValidationError("积分不能为负数")
        return value

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            phone=validated_data.get('phone', ''),
            password=validated_data['password']
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    data['user'] = user
                else:
                    raise serializers.ValidationError("用户账户已被禁用")
            else:
                raise serializers.ValidationError("用户名或密码错误")
        else:
            raise serializers.ValidationError("必须提供用户名和密码")
        
        return data