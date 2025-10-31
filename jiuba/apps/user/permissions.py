from rest_framework import permissions

class IsMerchantUser(permissions.BasePermission):
    """
    商家权限：可以访问商家后台，但不能访问Django Admin
    对应中间档权限
    """
    message = "只有商家用户才能访问此功能"
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_merchant

class IsAdminUser(permissions.BasePermission):
    """
    管理员权限：可以访问所有后台
    对应最高级权限
    """
    message = "只有管理员才能访问此功能"
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff