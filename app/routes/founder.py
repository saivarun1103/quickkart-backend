from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from datetime import datetime, timedelta
from app.db import get_db
from app.dependencies import get_current_founder
from app.models import Business, Order

router = APIRouter(prefix="/api/founder", tags=["Founder"])

async def get_sales_and_orders(db: AsyncSession, start_time: datetime, end_time: datetime):
    stmt = select(
        func.coalesce(func.sum(Order.total_price), 0),
        func.count(Order.id)
    ).where(
        and_(
            Order.payment_status == "paid",
            Order.created_at >= start_time,
            Order.created_at < end_time
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    return float(row[0]), int(row[1])

def calculate_percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100.0, 1)

@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    founder: Business = Depends(get_current_founder)
):
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)
    
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)
    
    month_start = now - timedelta(days=30)
    prev_month_start = now - timedelta(days=60)
    
    # Sales & Orders for periods
    today_sales, today_orders = await get_sales_and_orders(db, today_start, now)
    yesterday_sales, yesterday_orders = await get_sales_and_orders(db, yesterday_start, today_start)
    
    week_sales, week_orders = await get_sales_and_orders(db, week_start, now)
    prev_week_sales, prev_week_orders = await get_sales_and_orders(db, prev_week_start, week_start)
    
    month_sales, month_orders = await get_sales_and_orders(db, month_start, now)
    prev_month_sales, prev_month_orders = await get_sales_and_orders(db, prev_month_start, month_start)
    
    # 1. Total Businesses
    total_businesses_stmt = select(func.count(Business.id))
    total_businesses = (await db.execute(total_businesses_stmt)).scalar() or 0
    
    # 2. Active Businesses Today
    active_businesses_stmt = select(func.count(func.distinct(Order.business_id))).where(
        and_(
            Order.payment_status == "paid",
            Order.created_at >= today_start
        )
    )
    active_businesses_today = (await db.execute(active_businesses_stmt)).scalar() or 0
    
    # 3. AOV (last 30d)
    aov = round(month_sales / month_orders, 1) if month_orders > 0 else 0.0
    
    # 4. Revenue per business (last 30d)
    rev_per_business = round(month_sales / total_businesses, 1) if total_businesses > 0 else 0.0
    
    return {
        "metrics": {
            "today_sales": {
                "value": today_sales,
                "change": calculate_percent_change(today_sales, yesterday_sales),
                "trend": "up" if today_sales >= yesterday_sales else "down"
            },
            "today_orders": {
                "value": today_orders,
                "change": calculate_percent_change(today_orders, yesterday_orders),
                "trend": "up" if today_orders >= yesterday_orders else "down"
            },
            "week_sales": {
                "value": week_sales,
                "change": calculate_percent_change(week_sales, prev_week_sales),
                "trend": "up" if week_sales >= prev_week_sales else "down"
            },
            "month_sales": {
                "value": month_sales,
                "change": calculate_percent_change(month_sales, prev_month_sales),
                "trend": "up" if month_sales >= prev_month_sales else "down"
            }
        },
        "analytics": {
            "total_businesses": total_businesses,
            "active_businesses_today": active_businesses_today,
            "total_orders_today": today_orders,
            "total_orders_this_week": week_orders,
            "total_orders_this_month": month_orders,
            "average_order_value": aov,
            "revenue_per_business": rev_per_business
        }
    }

@router.get("/revenue-trends")
async def get_revenue_trends(
    db: AsyncSession = Depends(get_db),
    founder: Business = Depends(get_current_founder)
):
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    # 1. Daily Revenue (Last 7 Days)
    seven_days_ago = today_start - timedelta(days=6)
    daily_stmt = select(
        func.date_trunc('day', Order.created_at).label('day'),
        func.sum(Order.total_price).label('revenue')
    ).where(
        and_(
            Order.payment_status == "paid",
            Order.created_at >= seven_days_ago
        )
    ).group_by(text('day')).order_by(text('day'))
    daily_result = await db.execute(daily_stmt)
    
    daily_map = {row.day.strftime("%Y-%m-%d"): float(row.revenue) for row in daily_result if row.day}
    daily_data = []
    for i in range(7):
        d_date = seven_days_ago + timedelta(days=i)
        d_str = d_date.strftime("%Y-%m-%d")
        daily_data.append({
            "date": d_date.strftime("%a %d"),  # e.g., "Mon 15"
            "full_date": d_str,
            "revenue": daily_map.get(d_str, 0.0)
        })
        
    # 2. Weekly Revenue (Last 12 Weeks)
    current_week_start = today_start - timedelta(days=today_start.weekday())
    twelve_weeks_ago = current_week_start - timedelta(weeks=11)
    
    weekly_stmt = select(
        func.date_trunc('week', Order.created_at).label('week'),
        func.sum(Order.total_price).label('revenue')
    ).where(
        and_(
            Order.payment_status == "paid",
            Order.created_at >= twelve_weeks_ago
        )
    ).group_by(text('week')).order_by(text('week'))
    weekly_result = await db.execute(weekly_stmt)
    
    weekly_map = {row.week.strftime("%Y-%m-%d"): float(row.revenue) for row in weekly_result if row.week}
    weekly_data = []
    for i in range(12):
        w_date = twelve_weeks_ago + timedelta(weeks=i)
        w_str = w_date.strftime("%Y-%m-%d")
        weekly_data.append({
            "week": f"Wk {w_date.strftime('%W')}",  # e.g., "Wk 24"
            "full_date": w_str,
            "revenue": weekly_map.get(w_str, 0.0)
        })
        
    # 3. Monthly Revenue (Last 12 Months)
    month_starts = []
    y, m = now.year, now.month
    for _ in range(12):
        month_starts.append(datetime(y, m, 1))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    month_starts.reverse()
    twelve_months_ago = month_starts[0]
    
    monthly_stmt = select(
        func.date_trunc('month', Order.created_at).label('month'),
        func.sum(Order.total_price).label('revenue')
    ).where(
        and_(
            Order.payment_status == "paid",
            Order.created_at >= twelve_months_ago
        )
    ).group_by(text('month')).order_by(text('month'))
    monthly_result = await db.execute(monthly_stmt)
    
    monthly_map = {row.month.strftime("%Y-%m"): float(row.revenue) for row in monthly_result if row.month}
    monthly_data = []
    for ms in month_starts:
        m_str = ms.strftime("%Y-%m")
        monthly_data.append({
            "month": ms.strftime("%b %y"),  # e.g., "Jun 26"
            "full_month": m_str,
            "revenue": monthly_map.get(m_str, 0.0)
        })
        
    return {
        "daily": daily_data,
        "weekly": weekly_data,
        "monthly": monthly_data
    }

@router.get("/top-businesses")
async def get_top_businesses(
    db: AsyncSession = Depends(get_db),
    founder: Business = Depends(get_current_founder)
):
    stmt = select(
        Business.id,
        Business.name,
        func.count(Order.id).label('orders_count'),
        func.coalesce(func.sum(Order.total_price), 0).label('revenue')
    ).outerjoin(
        Order,
        and_(
            Business.id == Order.business_id,
            Order.payment_status == "paid"
        )
    ).group_by(
        Business.id,
        Business.name
    ).order_by(
        desc(text('revenue'))
    )
    result = await db.execute(stmt)
    businesses = []
    for row in result:
        orders = int(row.orders_count)
        revenue = float(row.revenue)
        aov = round(revenue / orders, 1) if orders > 0 else 0.0
        businesses.append({
            "id": row.id,
            "name": row.name,
            "orders": orders,
            "revenue": revenue,
            "aov": aov
        })
    return businesses

@router.get("/activity")
async def get_activity(
    db: AsyncSession = Depends(get_db),
    founder: Business = Depends(get_current_founder)
):
    # 1. Fetch 10 most recent businesses onboarded
    bus_stmt = select(Business).order_by(desc(Business.created_at)).limit(10)
    bus_result = await db.execute(bus_stmt)
    recent_businesses = bus_result.scalars().all()
    
    # 2. Fetch 15 most recent large orders (price >= 500)
    order_stmt = select(
        Order.created_at,
        Order.total_price,
        Business.name.label('business_name')
    ).join(
        Business,
        Order.business_id == Business.id
    ).where(
        and_(
            Order.payment_status == "paid",
            Order.total_price >= 500
        )
    ).order_by(desc(Order.created_at)).limit(15)
    order_result = await db.execute(order_stmt)
    recent_orders = order_result.all()
    
    # Merge activities
    activities = []
    
    for b in recent_businesses:
        activities.append({
            "timestamp": b.created_at.isoformat() if b.created_at else datetime.now().isoformat(),
            "type": "business_onboarded",
            "message": f"New business '{b.name}' ({b.business_type or 'Shop'}) onboarded by {b.owner_name or 'merchant'}.",
            "meta": {"business_id": b.id, "name": b.name}
        })
        
    for o in recent_orders:
        activities.append({
            "timestamp": o.created_at.isoformat() if o.created_at else datetime.now().isoformat(),
            "type": "large_order",
            "message": f"Large order of ₹{o.total_price} placed at '{o.business_name}'.",
            "meta": {"total_price": o.total_price, "business_name": o.business_name}
        })
        
    # 3. Add system milestones
    tot_bus_stmt = select(func.count(Business.id))
    tot_orders_stmt = select(func.count(Order.id)).where(Order.payment_status == "paid")
    tot_rev_stmt = select(func.sum(Order.total_price)).where(Order.payment_status == "paid")
    
    total_businesses = (await db.execute(tot_bus_stmt)).scalar() or 0
    total_orders = (await db.execute(tot_orders_stmt)).scalar() or 0
    total_revenue = (await db.execute(tot_rev_stmt)).scalar() or 0
    
    # Milestones logic (cumulative milestone flags)
    if total_businesses >= 5:
        activities.append({
            "timestamp": datetime.now().isoformat(),
            "type": "milestone",
            "message": f"Milestone: Platform onboarded its {total_businesses}th business!",
            "meta": {"milestone_type": "businesses", "value": total_businesses}
        })
    if total_orders >= 50:
        activities.append({
            "timestamp": datetime.now().isoformat(),
            "type": "milestone",
            "message": f"Milestone: Platform processed over {total_orders} successful orders!",
            "meta": {"milestone_type": "orders", "value": total_orders}
        })
    if total_revenue >= 5000:
        activities.append({
            "timestamp": datetime.now().isoformat(),
            "type": "milestone",
            "message": f"Milestone: Platform total revenue crossed ₹{int(total_revenue)}!",
            "meta": {"milestone_type": "revenue", "value": total_revenue}
        })
        
    # Sort activities by timestamp descending
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Return top 20 activities
    return activities[:20]
