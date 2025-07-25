from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import (
    get_db,
    PaymentModel,
    PaymentItemModel,
    OrderModel,
    OrderItemModel,
    PaymentStatusEnum,
    OrderStatusEnum,
)
from schemas.movies import PaymentSchema, PaymentCreateSchema, PaymentListSchema
from config.dependencies import (
    get_current_user,
    get_current_admin,
    get_accounts_email_notificator,
)
import datetime
from utils.email import send_email
from typing import Optional
from database import UserModel
from notifications.interfaces import EmailSenderInterface

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/",
    response_model=PaymentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment",
    description="Create a payment for an order using Stripe",
)
async def create_payment(
    payment_data: PaymentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
):
    # Verify the order exists and belongs to the user
    order = await db.get(OrderModel, payment_data.order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Order is not pending.")

    # Verify the total amount matches
    if abs(float(order.total_amount) - float(payment_data.amount)) > 0.01:
        raise HTTPException(
            status_code=400, detail="Payment amount does not match order total."
        )

    # Simulate Stripe payment processing
    try:
        # Here you would integrate with Stripe API
        # For now, we simulate a successful payment
        stripe_payment_id = f"stripe_{datetime.datetime.utcnow().timestamp()}"

        # Create payment record
        payment = PaymentModel(
            user_id=current_user.id,
            order_id=order.id,
            amount=payment_data.amount,
            external_payment_id=payment_data.external_payment_id or stripe_payment_id,
            status=PaymentStatusEnum.SUCCESSFUL,
        )
        db.add(payment)
        await db.flush()

        # Create payment items
        for order_item in order.items:
            payment_item = PaymentItemModel(
                payment_id=payment.id,
                order_item_id=order_item.id,
                price_at_payment=order_item.price_at_order,
            )
            db.add(payment_item)

        # Update order status
        order.status = OrderStatusEnum.PAID

        await db.commit()
        await db.refresh(payment)

        # Send email confirmation
        try:
            await email_sender.send_activation_complete_email(
                email=current_user.email, login_link=f"/orders/{order.id}"
            )
        except Exception as e:
            print(f"Failed to send payment confirmation email: {e}")

        return payment

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Payment processing failed: {str(e)}"
        )


@router.get(
    "/",
    response_model=list[PaymentSchema],
    summary="List user payments",
    description="Get all payments for the current user",
)
async def list_user_payments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = (
        select(PaymentModel)
        .where(PaymentModel.user_id == current_user.id)
        .order_by(PaymentModel.created_at.desc())
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()
    return payments


@router.get(
    "/{payment_id}",
    response_model=PaymentSchema,
    summary="Get payment details",
    description="Get details of a specific payment for the current user",
)
async def get_payment_details(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payment = await db.get(PaymentModel, payment_id)
    if not payment or payment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return payment


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentSchema,
    summary="Refund payment",
    description="Refund a successful payment (admin only)",
)
async def refund_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
):
    payment = await db.get(PaymentModel, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found.")

    if payment.status != PaymentStatusEnum.SUCCESSFUL:
        raise HTTPException(
            status_code=400, detail="Only successful payments can be refunded."
        )

    # Simulate refund processing
    try:
        payment.status = PaymentStatusEnum.REFUNDED
        await db.commit()
        await db.refresh(payment)

        # Send refund confirmation email
        try:
            await email_sender.send_password_reset_complete_email(
                email=payment.user.email, login_link=f"/orders/{payment.order_id}"
            )
        except Exception as e:
            print(f"Failed to send refund confirmation email: {e}")

        return payment

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Refund processing failed: {str(e)}"
        )


@router.get(
    "/admin/payments/",
    response_model=list[PaymentSchema],
    summary="Admin: List all payments",
    description="Get all payments with optional filters (admin only)",
)
async def admin_list_payments(
    status: Optional[PaymentStatusEnum] = Query(
        None, description="Filter by payment status"
    ),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime.date] = Query(
        None, description="Filter payments from this date"
    ),
    end_date: Optional[datetime.date] = Query(
        None, description="Filter payments until this date"
    ),
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
):
    stmt = select(PaymentModel)

    if status:
        stmt = stmt.where(PaymentModel.status == status)
    if user_id:
        stmt = stmt.where(PaymentModel.user_id == user_id)
    if start_date:
        stmt = stmt.where(PaymentModel.created_at >= start_date)
    if end_date:
        stmt = stmt.where(PaymentModel.created_at <= end_date)

    stmt = stmt.order_by(PaymentModel.created_at.desc())
    result = await db.execute(stmt)
    payments = result.scalars().all()
    return payments


@router.post(
    "/webhook/stripe",
    summary="Stripe webhook",
    description="Handle Stripe webhook events for payment validation",
)
async def stripe_webhook(
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    # Here you would validate the webhook signature and process Stripe events
    # For now, we'll simulate webhook processing

    event_type = request.get("type")
    data = request.get("data", {})

    if event_type == "payment_intent.succeeded":
        # Handle successful payment
        payment_intent = data.get("object", {})
        external_payment_id = payment_intent.get("id")

        # Find and update payment
        stmt = select(PaymentModel).where(
            PaymentModel.external_payment_id == external_payment_id
        )
        result = await db.execute(stmt)
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatusEnum.SUCCESSFUL
            await db.commit()

    elif event_type == "payment_intent.payment_failed":
        # Handle failed payment
        payment_intent = data.get("object", {})
        external_payment_id = payment_intent.get("id")

        stmt = select(PaymentModel).where(
            PaymentModel.external_payment_id == external_payment_id
        )
        result = await db.execute(stmt)
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatusEnum.CANCELED
            await db.commit()

    return {"status": "processed"}
