import logging

logger = logging.getLogger(__name__)

def calculate_co_payment(base_price: float, co_payment_percentage: float, package_discount: float = 0) -> float:
    """
    حساب قيمة المشاركة المالية (co-payment)
    
    Args:
        base_price: السعر الأساسي للخدمة
        co_payment_percentage: نسبة المشاركة المالية (مثال: 0.3 تعني 30%)
        package_discount: نسبة الخصم من الباقة (مثال: 0.1 تعني 10%)
    
    Returns:
        قيمة المشاركة المالية
    """
    # Apply package discount first
    discounted_price = base_price * (1 - package_discount)
    
    # Calculate co-payment
    co_payment = discounted_price * co_payment_percentage
    
    logger.debug(f"Calculated co-payment - base: {base_price}, discount: {package_discount}, "
                f"co-payment%: {co_payment_percentage}, result: {co_payment}")
    
    return round(co_payment, 2)

def calculate_discounted_price(base_price: float, discount_percentage: float) -> float:
    """حساب السعر بعد الخصم"""
    discounted = base_price * (1 - discount_percentage)
    return round(discounted, 2)