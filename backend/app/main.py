from contextlib import asynccontextmanager
from datetime import date

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import models, schemas
from .auth import current_employee, require_app_request, router as auth_router
from .config import STATUSES, STATUS_TRANSITIONS
from .database import Base, engine, get_db
from .services import create_order, get_or_404, update_order


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Produce Desk API", version="1.0.0", lifespan=lifespan,
              description="Local staff demo. All order statuses are entered manually.")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": {"message": str(exc.detail), "details": []}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc):
    details = [{"field": ".".join(map(str, error["loc"][1:])), "message": error["msg"]} for error in exc.errors()]
    message = "; ".join(f"{detail['field'].replace('_', ' ')}: {detail['message']}" if detail["field"] else detail["message"] for detail in details)
    return JSONResponse(status_code=422, content={"error": {"message": message, "details": details}})


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc):
    return JSONResponse(status_code=409, content={"error": {"message": "The change conflicts with saved data. Refresh and try again.", "details": []}})


protected = APIRouter(dependencies=[Depends(current_employee), Depends(require_app_request)])


@protected.get("/api/config")
def configuration():
    return {"statuses": STATUSES, "transitions": STATUS_TRANSITIONS}


@protected.get("/api/customers", response_model=list[schemas.CustomerOut])
def customers(search: str = "", db: Session = Depends(get_db)):
    query = select(models.Customer)
    if search.strip():
        query = query.where(or_(models.Customer.full_name.icontains(search.strip(), autoescape=True), models.Customer.phone.icontains(search.strip(), autoescape=True)))
    return db.scalars(query.order_by(models.Customer.full_name, models.Customer.id)).all()


@protected.post("/api/customers", response_model=schemas.CustomerOut, status_code=201)
def add_customer(payload: schemas.CustomerCreate, db: Session = Depends(get_db)):
    customer = models.Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@protected.get("/api/customers/{customer_id}", response_model=schemas.CustomerOut)
def customer_detail(customer_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Customer, customer_id)


@protected.patch("/api/customers/{customer_id}", response_model=schemas.CustomerOut)
def edit_customer(customer_id: int, payload: schemas.CustomerPatch, db: Session = Depends(get_db)):
    customer = get_or_404(db, models.Customer, customer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@protected.get("/api/customers/{customer_id}/orders", response_model=list[schemas.OrderSummary])
def customer_orders(customer_id: int, db: Session = Depends(get_db)):
    get_or_404(db, models.Customer, customer_id)
    return db.scalars(select(models.Order).where(models.Order.customer_id == customer_id).order_by(models.Order.id.desc())).all()


@protected.get("/api/products", response_model=list[schemas.ProductOut])
def products(search: str = "", category: str = "", db: Session = Depends(get_db)):
    query = select(models.Product)
    if search.strip():
        query = query.where(models.Product.name.icontains(search.strip(), autoescape=True))
    if category.strip():
        query = query.where(models.Product.category == category.strip())
    return db.scalars(query.order_by(models.Product.name)).all()


def order_search(query, search):
    if search.strip():
        query = query.join(models.Customer).where(or_(
            models.Order.order_number.icontains(search.strip(), autoescape=True),
            models.Customer.full_name.icontains(search.strip(), autoescape=True)))
    return query


# Static routes deliberately precede /api/orders/{order_id}.
@protected.get("/api/orders/status-counts")
def status_counts(search: str = "", db: Session = Depends(get_db)):
    query = order_search(select(models.Order.status, func.count(models.Order.id)), search)
    counts = dict(db.execute(query.group_by(models.Order.status)).all())
    return {"total": sum(counts.values()), "counts": {status: counts.get(status, 0) for status in STATUSES}}


@protected.get("/api/orders", response_model=list[schemas.OrderSummary])
def orders(search: str = "", status: str | None = None, db: Session = Depends(get_db)):
    query = order_search(select(models.Order), search)
    if status:
        if status not in STATUSES:
            raise HTTPException(422, "Unknown order status.")
        query = query.where(models.Order.status == status)
    return db.scalars(query.order_by(models.Order.received_date.desc(), models.Order.id.desc())).all()


@protected.post("/api/orders", response_model=schemas.OrderOut, status_code=201)
def add_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    order = create_order(db, payload)
    db.commit()
    db.refresh(order)
    return order


@protected.get("/api/orders/{order_id}", response_model=schemas.OrderOut)
def order_detail(order_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Order, order_id)


@protected.patch("/api/orders/{order_id}", response_model=schemas.OrderOut)
def edit_order(order_id: int, payload: schemas.OrderPatch, db: Session = Depends(get_db)):
    order = get_or_404(db, models.Order, order_id)
    update_order(db, order, payload)
    db.commit()
    db.refresh(order)
    return order


@protected.get("/api/deliveries", response_model=list[schemas.OrderSummary])
def deliveries(date_from: date = Query(...), date_to: date | None = None, db: Session = Depends(get_db)):
    date_to = date_to or date_from
    if date_to < date_from:
        raise HTTPException(422, "End date cannot precede start date.")
    return db.scalars(select(models.Order).where(
        models.Order.scheduled_delivery_date.between(date_from, date_to)
    ).order_by(models.Order.scheduled_delivery_date, models.Order.id)).all()


app.include_router(auth_router)
app.include_router(protected)
