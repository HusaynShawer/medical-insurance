from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from app.database import create_all_tables, close_db
from app.routers import booking_route, Doctors, customer, slots
from app.routers import appointments
from app.routers import admin
from app.routers import chat

app = FastAPI(
    title="Smart Insurance Medical Booking",
    version="1.0.0",
)


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

@app.on_event("shutdown")
async def shutdown():
    await close_db()

# =============================================
# Routers
# =============================================
app.include_router(booking_route.router)
app.include_router(Doctors.router)
app.include_router(customer.router)
app.include_router(slots.router)
app.include_router(appointments.router)
app.include_router(admin.router)
app.include_router(chat.router)

# =============================================
# Health Check
# =============================================
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}