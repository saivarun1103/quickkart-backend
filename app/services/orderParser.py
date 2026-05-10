import re
from app.models import MenuItem

def parse_order(text: str, db):
    items = {}

    lines = text.split("\n")

    for line in lines:
        line = line.strip()

        # ❗ Skip "order:" line
        if line.lower().startswith("order"):
            continue

        # ❗ Remove price part
        line = line.split("=")[0].strip()

        match = re.match(r"([a-zA-Z ]+)\s*x\s*(\d+)", line, re.IGNORECASE)

        if match:
            name = match.group(1).strip()
            qty = int(match.group(2))

            db_item = db.query(MenuItem).filter(
                MenuItem.name.ilike(name)
            ).first()

            if db_item and db_item.available:
                items[db_item.name] = qty  # use DB name

    return items

def calculate_total(items, db):
    total = 0

    for item_name, qty in items.items():
        item = db.query(MenuItem).filter(MenuItem.name == item_name).first()
        if item:
            total += item.price * qty

    return int(total)

