# apps/reservation/serializers.py

from rest_framework import serializers
from .models import Reservation

class ReservationSerializer(serializers.ModelSerializer):
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    reservation_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'reservation_id', 'activity', 'activity_title', 'shop_name',
            'contact_phone', 'note', 'status', 'created_at'
        ]
        read_only_fields = ['reservation_id', 'status', 'created_at']

class ReservationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['activity', 'contact_phone', 'note']
        extra_kwargs = {
            'activity': {'required': True},
            'contact_phone': {'required': True},
        }

    def validate_activity(self, value):
        from django.utils import timezone
        if value.start_time <= timezone.now():
            raise serializers.ValidationError("该活动已开始，无法预约。")
        return value

    def validate(self, data):
        activity = data['activity']
        # 检查是否已预约过该活动
        if Reservation.objects.filter(
            user=self.context['request'].user,
            activity=activity,
            status__in=['confirmed', 'completed']
        ).exists():
            raise serializers.ValidationError("您已预约过该活动。")
        
        # 检查名额（如果有限制）
        if activity.max_participants is not None:
            current_count = Reservation.objects.filter(
                activity=activity,
                status='confirmed'
            ).count()
            if current_count >= activity.max_participants:
                raise serializers.ValidationError("该活动名额已满。")
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)