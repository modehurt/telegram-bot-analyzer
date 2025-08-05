import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import PAYMENT_TOKEN, PRO_PRICE, PRO_DURATION_DAYS, ADMIN_TELEGRAM_ID
from subscription_service import subscription_service

class PaymentService:
    def __init__(self):
        self.payments: Dict[str, Dict] = {}  # payment_id -> payment_data
        self.promocodes: Dict[str, Dict] = {
            "TESTPRO": {"discount": 100, "max_uses": 10, "used": 0},
            "WELCOME": {"discount": 50, "max_uses": 20, "used": 0},
            "LAUNCH": {"discount": 75, "max_uses": 5, "used": 0}
        }
    
    def create_payment(self, user_id: int, plan: str = "PRO") -> Dict:
        """Создает новый платеж"""
        payment_id = str(uuid.uuid4())
        
        payment_data = {
            "payment_id": payment_id,
            "user_id": user_id,
            "plan": plan,
            "amount": PRO_PRICE,
            "currency": "RUB",
            "status": "pending",
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "promocode": None,
            "discount": 0
        }
        
        self.payments[payment_id] = payment_data
        return payment_data
    
    def apply_promocode(self, payment_id: str, promocode: str) -> Dict:
        """Применяет промокод к платежу"""
        if payment_id not in self.payments:
            return {"success": False, "message": "Платеж не найден"}
        
        if promocode not in self.promocodes:
            return {"success": False, "message": "Неверный промокод"}
        
        promocode_data = self.promocodes[promocode]
        
        if promocode_data["used"] >= promocode_data["max_uses"]:
            return {"success": False, "message": "Промокод больше не действителен"}
        
        payment = self.payments[payment_id]
        payment["promocode"] = promocode
        payment["discount"] = promocode_data["discount"]
        payment["amount"] = max(0, PRO_PRICE - promocode_data["discount"])
        
        promocode_data["used"] += 1
        
        return {
            "success": True, 
            "message": f"Промокод применен! Скидка: {promocode_data['discount']}₽",
            "new_amount": payment["amount"]
        }
    
    def process_payment(self, payment_id: str, method: str = "manual") -> Dict:
        """Обрабатывает платеж"""
        if payment_id not in self.payments:
            return {"success": False, "message": "Платеж не найден"}
        
        payment = self.payments[payment_id]
        
        if payment["status"] != "pending":
            return {"success": False, "message": "Платеж уже обработан"}
        
        if datetime.now() > payment["expires_at"]:
            return {"success": False, "message": "Время платежа истекло"}
        
        # Имитируем успешную оплату
        payment["status"] = "completed"
        payment["completed_at"] = datetime.now()
        payment["payment_method"] = method
        
        # Активируем PRO подписку
        user_id = payment["user_id"]
        subscription_service.add_pro_user(user_id)
        
        return {
            "success": True,
            "message": "Оплата прошла успешно! PRO подписка активирована.",
            "expires_at": datetime.now() + timedelta(days=PRO_DURATION_DAYS)
        }
    
    def get_payment_info(self, payment_id: str) -> Optional[Dict]:
        """Получает информацию о платеже"""
        return self.payments.get(payment_id)
    
    def get_user_payments(self, user_id: int) -> list:
        """Получает все платежи пользователя"""
        return [p for p in self.payments.values() if p["user_id"] == user_id]
    
    def cancel_payment(self, payment_id: str) -> Dict:
        """Отменяет платеж"""
        if payment_id not in self.payments:
            return {"success": False, "message": "Платеж не найден"}
        
        payment = self.payments[payment_id]
        if payment["status"] != "pending":
            return {"success": False, "message": "Платеж уже обработан"}
        
        payment["status"] = "cancelled"
        payment["cancelled_at"] = datetime.now()
        
        return {"success": True, "message": "Платеж отменен"}
    
    def get_available_promocodes(self) -> list:
        """Возвращает доступные промокоды"""
        available = []
        for code, data in self.promocodes.items():
            if data["used"] < data["max_uses"]:
                available.append({
                    "code": code,
                    "discount": data["discount"],
                    "remaining_uses": data["max_uses"] - data["used"]
                })
        return available

# Глобальный экземпляр платежного сервиса
payment_service = PaymentService() 