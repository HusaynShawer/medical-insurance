#!/usr/bin/env python
import asyncio
import sys
import os
from datetime import date, time, timedelta
from sqlalchemy import select

# إضافة مسار المشروع للـ sys.path لتتمكن من استيراد النماذج
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionFactory, create_all_tables, drop_all_tables
from app.models import (
    Customer, Package, Policy, Doctor, DoctorNetwork, DoctorSlot,
    Service, ServicePrice, Branch, ServiceAvailability, Medicine, Appointment
)

async def seed():
    async with AsyncSessionFactory() as session:
        try:
            # Create tables
            await create_all_tables()
            print("Tables created")

            # =============================================
            # 1. Packages (صحيح)
            # =============================================
            packages = [
                Package(
                    name="Basic",
                    name_ar="أساسية",
                    max_visits_per_month=2,
                    discount_percentage=0.0,
                    max_lab_tests_per_month=1,
                    max_radiology_per_month=0
                ),
                Package(
                    name="Premium",
                    name_ar="ممتازة",
                    max_visits_per_month=4,
                    discount_percentage=0.1,
                    max_lab_tests_per_month=3,
                    max_radiology_per_month=2
                ),
                Package(
                    name="Family",
                    name_ar="عائلية",
                    max_visits_per_month=6,
                    discount_percentage=0.15,
                    max_lab_tests_per_month=5,
                    max_radiology_per_month=3
                ),
            ]
            session.add_all(packages)
            await session.flush()
            print(f"Added {len(packages)} packages")

            # =============================================
            # 2. Customers
            # =============================================
            customers = [
                Customer(national_id="12345678901234", name="أحمد محمد", city="القاهرة"),
                Customer(national_id="23456789012345", name="سارة علي", city="الإسكندرية"),
                Customer(national_id="34567890123456", name="محمد محمود", city="القاهرة"),
            ]
            session.add_all(customers)
            await session.flush()
            print(f"Added {len(customers)} customers")

            # =============================================
            # 3. Policies
            # =============================================
            today = date.today()
            policies = [
                Policy(customer_id=customers[0].id, package_id=packages[1].id,
                    start_date=today, end_date=today + timedelta(days=365)),
                Policy(customer_id=customers[1].id, package_id=packages[2].id,
                    start_date=today, end_date=today + timedelta(days=365)),
                Policy(customer_id=customers[2].id, package_id=packages[0].id,
                    start_date=today, end_date=today + timedelta(days=365)),
            ]
            session.add_all(policies)
            await session.flush()
            print(f"Added {len(policies)} policies")

            # =============================================
            # 4. Doctors
            # =============================================
            doctors = [
                Doctor(name="د. خالد حسن", specialization="Cardiology", city="القاهرة"),
                Doctor(name="د. منى سعيد", specialization="Neurology", city="القاهرة"),
                Doctor(name="د. أحمد فتحي", specialization="Dermatology", city="الإسكندرية"),
                Doctor(name="د. نادية رشاد", specialization="General", city="القاهرة"),
            ]
            session.add_all(doctors)
            await session.flush()
            print(f"Added {len(doctors)} doctors")

            # =============================================
            # 5. Doctor Networks
            # =============================================
            networks = []
            for doctor in doctors:
                for package in packages:
                    networks.append(DoctorNetwork(doctor_id=doctor.id, package_id=package.id))
            session.add_all(networks)
            await session.flush()
            print(f"Added {len(networks)} doctor-network links")

            # =============================================
            # 6. Doctor Slots (next 7 days)
            # =============================================
            slots = []
            for doctor in doctors:
                for day in range(7):
                    slot_date = today + timedelta(days=day)
                    for hour in [9, 11, 14, 16]:
                        slot_time = time(hour, 0)
                        slots.append(DoctorSlot(
                            doctor_id=doctor.id,
                            slot_date=slot_date,
                            slot_time=slot_time,
                            is_available=True
                        ))
            session.add_all(slots)
            await session.flush()
            print(f"Added {len(slots)} doctor slots")

            # =============================================
            # 7. Services
            # =============================================
            services = [
                Service(name="Blood Test", name_ar="تحليل دم", service_type="lab_test",
                        base_price=150.0, description="تحليل شامل للدم"),
                Service(name="X-Ray", name_ar="أشعة سينية", service_type="radiology",
                        base_price=300.0, description="أشعة سينية عادية"),
                Service(name="MRI", name_ar="رنين مغناطيسي", service_type="radiology",
                        base_price=800.0, description="رنين مغناطيسي"),
                Service(name="General Consultation", name_ar="استشارة عامة", service_type="consultation",
                        base_price=200.0, description="استشارة طبية عامة"),
            ]
            session.add_all(services)
            await session.flush()
            print(f"Added {len(services)} services")

            # =============================================
            # 8. Service Prices
            # =============================================
            service_prices = []
            for package in packages:
                for service in services:
                    co_payment = 0.2  # 20%
                    max_visits = 2 if service.service_type == "consultation" else 1
                    if package.id == packages[0].id and service.service_type != "consultation":
                        max_visits = 0
                        co_payment = 0.5
                    service_prices.append(ServicePrice(
                        package_id=package.id,
                        service_id=service.id,
                        co_payment=co_payment,
                        max_visits_per_month=max_visits
                    ))
            session.add_all(service_prices)
            await session.flush()
            print(f"Added {len(service_prices)} service prices")

            # =============================================
            # 9. Branches
            # =============================================
            branches = [
                Branch(name="Cairo Main", name_ar="الفرع الرئيسي - القاهرة", city="القاهرة",
                    address="شارع النيل, القاهرة", phone="0223456789"),
                Branch(name="Alex Branch", name_ar="فرع الإسكندرية", city="الإسكندرية",
                    address="شارع البحر, الإسكندرية", phone="0334567890"),
            ]
            session.add_all(branches)
            await session.flush()
            print(f"Added {len(branches)} branches")

            # =============================================
            # 10. Service Availability
            # =============================================
            service_slots = []
            for branch in branches:
                for service in services:
                    if service.service_type in ["lab_test", "radiology"]:
                        for day in range(7):
                            slot_date = today + timedelta(days=day)
                            for hour in [10, 12, 15]:
                                slot_time = time(hour, 0)
                                service_slots.append(ServiceAvailability(
                                    branch_id=branch.id,
                                    service_id=service.id,
                                    available_date=slot_date,
                                    available_time=slot_time,
                                    is_available=True,
                                    max_capacity=1
                                ))
            session.add_all(service_slots)
            await session.flush()
            print(f"Added {len(service_slots)} service availability slots")

            # =============================================
            # 11. Medicines
            # =============================================
            medicines = [
                Medicine(name="Paracetamol", name_ar="باراسيتامول", active_ingredient="Acetaminophen",
                        category="Pain Relief", price=10.0, requires_prescription=False, is_covered=True),
                Medicine(name="Amoxicillin", name_ar="أموكسيسيلين", active_ingredient="Amoxicillin",
                        category="Antibiotic", price=25.0, requires_prescription=True, is_covered=True),
                Medicine(name="Atorvastatin", name_ar="أتورفاستاتين", active_ingredient="Atorvastatin",
                        category="Cholesterol", price=40.0, requires_prescription=True, is_covered=True),
            ]
            session.add_all(medicines)
            await session.flush()
            print(f"Added {len(medicines)} medicines")

            await session.commit()
            print("Seed data inserted successfully!")

        except Exception as e:
            await session.rollback()
            print(f"Error during seeding: {e}")
            raise

async def reset_and_seed():
    await drop_all_tables()
    print("All tables dropped")
    await seed()

if __name__ == "__main__":
    if "--reset" in sys.argv:
        asyncio.run(reset_and_seed())
    else:
        asyncio.run(seed())