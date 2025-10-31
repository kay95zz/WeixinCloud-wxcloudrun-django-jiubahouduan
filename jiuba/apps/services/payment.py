import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import requests

from fastapi import HTTPException

class WeChatPayService:
    def __init__(self, app_id: str, mch_id: str, api_key: str, notify_url: str):
        self.app_id = app_id
        self.mch_id = mch_id
        self.api_key = api_key
        self.notify_url = notify_url
    
    def create_unified_order(self, order_id: int, total_fee: int, openid: str, 
                           body: str, spbill_create_ip: str) -> Dict:
        """创建统一下单"""
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        
        # 生成随机字符串
        nonce_str = hashlib.md5(str(time.time()).encode()).hexdigest()
        
        # 构建参数
        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": nonce_str,
            "body": body,
            "out_trade_no": str(order_id),
            "total_fee": total_fee,
            "spbill_create_ip": spbill_create_ip,
            "notify_url": self.notify_url,
            "trade_type": "JSAPI",
            "openid": openid
        }
        
        # 生成签名
        sign = self.generate_sign(params)
        params["sign"] = sign
        
        # 转换为XML
        xml_data = self.dict_to_xml(params)
        
        # 发送请求
        response = requests.post(url, data=xml_data.encode('utf-8'))
        response.encoding = 'utf-8'
        
        # 解析响应
        result = self.xml_to_dict(response.text)
        
        if result.get('return_code') != 'SUCCESS':
            raise HTTPException(status_code=400, detail=result.get('return_msg', '支付请求失败'))
        
        if result.get('result_code') != 'SUCCESS':
            raise HTTPException(status_code=400, detail=result.get('err_code_des', '支付创建失败'))
        
        return result
    
    def generate_sign(self, params: Dict) -> str:
        """生成签名"""
        # 排序参数
        sorted_params = sorted(params.items())
        # 拼接字符串
        string_sign = "&".join([f"{key}={value}" for key, value in sorted_params if value])
        string_sign += f"&key={self.api_key}"
        # MD5加密
        return hashlib.md5(string_sign.encode()).hexdigest().upper()
    
    def dict_to_xml(self, params: Dict) -> str:
        """字典转XML"""
        xml = ["<xml>"]
        for key, value in params.items():
            xml.append(f"<{key}><![CDATA[{value}]]></{key}>")
        xml.append("</xml>")
        return "".join(xml)
    
    def xml_to_dict(self, xml_str: str) -> Dict:
        """XML转字典"""
        result = {}
        root = ET.fromstring(xml_str)
        for child in root:
            result[child.tag] = child.text
        return result
    
    def verify_signature(self, params: Dict) -> bool:
        """验证签名"""
        if 'sign' not in params:
            return False
        
        sign = params.pop('sign')
        generated_sign = self.generate_sign(params)
        return sign == generated_sign