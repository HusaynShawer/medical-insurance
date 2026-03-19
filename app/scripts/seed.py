import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionFactory
from app.models import (
    Customer,
    Package,
    Policy,
    Doctor,
    DoctorNetwork,
    Appointment,
)
from datetime import date

async def seed():
    async with AsyncSessionFactory() as session:
        # =============================================
        # 1. Packages
        # =============================================
        packages = [
            Package(name="Basic",  max_visits_per_month=2),
            Package(name="Silver", max_visits_per_month=4),
            Package(name="Gold",   max_visits_per_month=8),
        ]
        session.add_all(packages)
        await session.flush()
        print("✅ Packages inserted")

        # =============================================
        # 2. Customers
        # =============================================
        customers = [
            Customer(name="أحمد محمد",  national_id="12345678901234", city="Cairo"),
            Customer(name="سارة علي",   national_id="98765432109876", city="Alexandria"),
            Customer(name="محمد حسن",   national_id="11122233344455", city="Cairo"),
        ]
        session.add_all(customers)
        await session.flush()
        print("✅ Customers inserted")

        # =============================================
        # 3. Doctors
        # =============================================
        doctors = [
            Doctor(name="د. خالد سعيد",  specialization="Neurology",   city="Cairo"),
            Doctor(name="د. منى أحمد",   specialization="Cardiology",   city="Cairo"),
            Doctor(name="د. سامي علي",   specialization="Dermatology",  city="Alexandria"),
            Doctor(name="د. هدى محمود",  specialization="General",      city="Cairo"),
            Doctor(name="د. كريم حسن",   specialization="Neurology",    city="Alexandria"),
        ]
        session.add_all(doctors)
        await session.flush()
        print("✅ Doctors inserted")

        # =============================================
        # 4. Policies
        # =============================================
        policies = [
            Policy(
                customer_id=customers[0].id,
                package_id=packages[1].id,   # Silver
                start_date=date(2024, 1, 1),
                end_date=date(2025, 12, 31),
            ),
            Policy(
                customer_id=customers[1].id,
                package_id=packages[2].id,   # Gold
                start_date=date(2024, 1, 1),
                end_date=date(2025, 12, 31),
            ),
            Policy(
                customer_id=customers[2].id,
                package_id=packages[0].id,   # Basic
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),  # ← منتهية عشان نختبر validation
            ),
        ]
        session.add_all(policies)
        await session.flush()
        print("✅ Policies inserted")

        # =============================================
        # 5. Doctor Network
        # =============================================
        doctor_network = [
            # Silver package doctors
            DoctorNetwork(doctor_id=doctors[0].id, package_id=packages[1].id),
            DoctorNetwork(doctor_id=doctors[1].id, package_id=packages[1].id),
            DoctorNetwork(doctor_id=doctors[3].id, package_id=packages[1].id),
            # Gold package doctors (كل الأطباء)
            DoctorNetwork(doctor_id=doctors[0].id, package_id=packages[2].id),
            DoctorNetwork(doctor_id=doctors[1].id, package_id=packages[2].id),
            DoctorNetwork(doctor_id=doctors[2].id, package_id=packages[2].id),
            DoctorNetwork(doctor_id=doctors[3].id, package_id=packages[2].id),
            DoctorNetwork(doctor_id=doctors[4].id, package_id=packages[2].id),
        ]
        session.add_all(doctor_network)
        await session.flush()
        print("✅ Doctor Network inserted")

        await session.commit()
        print("\n🎉 Database seeded successfully!")
        print("=" * 40)
        print(f"📦 Packages  : {len(packages)}")
        print(f"👤 Customers : {len(customers)}")
        print(f"🏥 Doctors   : {len(doctors)}")
        print(f"📋 Policies  : {len(policies)}")
        print(f"🔗 Networks  : {len(doctor_network)}")

if __name__ == "__main__":
    asyncio.run(seed())