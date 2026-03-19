from fastapi import FastAPI
from app.database import create_all_tables, close_db
from app.routers import booking_route, Doctors, customer,slots

app = FastAPI(
    title="Smart Insurance Medical Booking",
    version="1.0.0",
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
# =============================================
# Health Check
# =============================================
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}