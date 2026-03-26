from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from app.database import create_all_tables, close_db
from app.routers import booking_route, Doctors, customer, slots
from app.routers import appointments
from app.routers import admin
from app.routers import chat
from app.routers import policies  # موجود مسبقاً
from app.routers import services   # 🆕
from app.routers import branches   # 🆕

app = FastAPI(
    title="Smart Insurance Medical Booking",
    version="2.0.0",  # تحديث الإصدار
    description="نظام حجز الخدمات الطبية مع دعم الخدمات الإضافية (تحاليل/أشعة/أدوية)"
)

# =============================================
# CORS Middleware
# =============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# =============================================
# Events
# =============================================
@app.on_event("startup")
async def startup():
    await create_all_tables()
    print("🚀 Application started successfully")

@app.on_event("shutdown")
async def shutdown():
    await close_db()
    print("👋 Application shutdown")

# =============================================
# Routers
# =============================================
# Existing routers
app.include_router(booking_route.router)
app.include_router(Doctors.router)
app.include_router(customer.router)
app.include_router(slots.router)
app.include_router(appointments.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(policies.router)

# 🆕 New routers for services and branches
app.include_router(services.router)
app.include_router(branches.router)

# =============================================
# Health Check
# =============================================
@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "services": ["booking", "doctors", "customers", "appointments", "services", "branches"]
    }

# =============================================
# Root endpoint
# =============================================
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Smart Insurance Medical Booking System",
        "version": "2.0.0",
        "endpoints": {
            "booking": "/booking",
            "doctors": "/doctors",
            "customers": "/customers",
            "appointments": "/appointments",
            "services": "/services",
            "branches": "/branches",
            "chat": "/chat"
        }
    }