from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from database import get_db, CartModel, CartItemModel, PurchasedMovieModel, MovieModel, OrderModel, OrderItemModel, OrderStatusEnum
from schemas.movies import OrderSchema, OrderCreateSchema, OrderItemSchema
from config.dependencies import get_current_user, get_current_admin
import datetime
from utils.email import send_email
from typing import Optional
from database import UserModel

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderSchema, status_code=status.HTTP_201_CREATED)
async def create_order_from_cart(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Get user's cart
    cart_stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Your cart is empty.")

    # Exclude already purchased movies
    purchased_stmt = select(PurchasedMovieModel.movie_id).where(PurchasedMovieModel.user_id == current_user.id)
    purchased_result = await db.execute(purchased_stmt)
    purchased_movie_ids = {row[0] for row in purchased_result.all()}

    # Exclude unavailable movies (deleted)
    available_movie_ids = set()
    for item in cart.items:
        movie = await db.get(MovieModel, item.movie_id)
        if movie:
            available_movie_ids.add(item.movie_id)
    
    # Check for pending orders with same movies
    pending_stmt = select(OrderItemModel.movie_id).join(OrderModel).where(
        and_(
            OrderModel.user_id == current_user.id,
            OrderModel.status == OrderStatusEnum.PENDING
        )
    )
    pending_result = await db.execute(pending_stmt)
    pending_movie_ids = {row[0] for row in pending_result.all()}

    # Filter movies to order
    movies_to_order = [item for item in cart.items if item.movie_id not in purchased_movie_ids and item.movie_id in available_movie_ids and item.movie_id not in pending_movie_ids]
    excluded_movies = [item.movie_id for item in cart.items if item not in movies_to_order]

    if not movies_to_order:
        raise HTTPException(status_code=400, detail="No movies available for order. All are already purchased, unavailable, or pending in another order.")

    # Create order
    order = OrderModel(user_id=current_user.id, status=OrderStatusEnum.PENDING)
    db.add(order)
    await db.flush()

    total_amount = 0.0
    order_items = []
    for item in movies_to_order:
        movie = await db.get(MovieModel, item.movie_id)
        order_item = OrderItemModel(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db.add(order_item)
        order_items.append(order_item)
        total_amount += float(movie.price)

    order.total_amount = total_amount
    await db.commit()
    await db.refresh(order)

    # Optionally: remove these items from cart
    for item in movies_to_order:
        await db.delete(item)
    await db.commit()

    # Attach items for response
    order.items = order_items

    # Optionally: return excluded movie IDs for notification
    order_dict = OrderSchema.model_validate(order).model_dump()
    order_dict["excluded_movies"] = excluded_movies
    return order_dict 

@router.get("/", response_model=list[OrderSchema], summary="List user orders", description="Get all orders for the current user.")
async def list_user_orders(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(OrderModel).where(OrderModel.user_id == current_user.id).order_by(OrderModel.created_at.desc())
    result = await db.execute(stmt)
    orders = result.scalars().all()
    return orders 

@router.get("/{order_id}", response_model=OrderSchema, summary="Get order details", description="Get details of a specific order for the current user.")
async def get_order_details(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    order = await db.get(OrderModel, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order 

@router.post("/{order_id}/cancel", response_model=OrderSchema, summary="Cancel order", description="Cancel a pending order. Only pending orders can be cancelled.")
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    order = await db.get(OrderModel, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found.")
    
    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled.")
    
    order.status = OrderStatusEnum.CANCELLED
    await db.commit()
    await db.refresh(order)
    return order 

@router.post("/{order_id}/pay", response_model=OrderSchema, summary="Pay for order", description="Simulate payment for a pending order. Moves movies to purchased list and sends email confirmation.")
async def pay_for_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    order = await db.get(OrderModel, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found.")
    
    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Only pending orders can be paid for.")
    
    # Update order status
    order.status = OrderStatusEnum.PAID
    
    # Move movies to purchased list
    for item in order.items:
        purchased_movie = PurchasedMovieModel(
            user_id=current_user.id,
            movie_id=item.movie_id,
            purchased_at=datetime.datetime.utcnow()
        )
        db.add(purchased_movie)
    
    await db.commit()
    await db.refresh(order)
    
    # Send email confirmation
    try:
        await send_email(
            subject="Order Payment Confirmation",
            recipient=current_user.email,
            body=f"Your order #{order.id} has been successfully paid. Total amount: ${order.total_amount}. Thank you for your purchase!"
        )
    except Exception as e:
        # Log error but don't fail the payment
        print(f"Failed to send email confirmation: {e}")
    
    return order 

@router.get("/admin/orders/", response_model=list[OrderSchema], summary="Admin: List all orders", description="Get all orders with optional filters (admin only)")
async def admin_list_orders(
    status: Optional[OrderStatusEnum] = Query(None, description="Filter by order status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime.date] = Query(None, description="Filter orders from this date"),
    end_date: Optional[datetime.date] = Query(None, description="Filter orders until this date"),
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
):
    stmt = select(OrderModel)
    
    if status:
        stmt = stmt.where(OrderModel.status == status)
    if user_id:
        stmt = stmt.where(OrderModel.user_id == user_id)
    if start_date:
        stmt = stmt.where(OrderModel.created_at >= start_date)
    if end_date:
        stmt = stmt.where(OrderModel.created_at <= end_date)
    
    stmt = stmt.order_by(OrderModel.created_at.desc())
    result = await db.execute(stmt)
    orders = result.scalars().all()
    return orders 