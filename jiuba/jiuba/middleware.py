class MerchantAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 检查是否是商家后台路径
        if request.path.startswith('/merchant/') and not request.path.startswith('/merchant/login/'):
            if not request.user.is_authenticated or not request.user.is_staff:  # 临时使用 is_staff
                from django.shortcuts import redirect
                return redirect('/merchant/login/')
        
        response = self.get_response(request)
        return response