let cart = [];

function addToCart(name, price) {
    let item = cart.find(i => i.name === name);

    if (item) {
        item.qty += 1;
    } else {
        cart.push({ name, price, qty: 1 });
    }

    updateItemUI(name);
    displayCart();
}

function increaseQty(name) {
    let item = cart.find(i => i.name === name);
    item.qty += 1;

    updateItemUI(name);
    displayCart();
}

function decreaseQty(name) {
    let item = cart.find(i => i.name === name);
    item.qty -= 1;

    if (item.qty === 0) {
        cart = cart.filter(i => i.name !== name);

        // back to ADD button
        document.getElementById(`controls-${name}`).innerHTML =
            `<button onclick="addToCart('${name}', ${item.price})">Add</button>`;
    } else {
        updateItemUI(name);
    }

    displayCart();
}

function displayCart() {
    let cartList = document.getElementById("cart");
    let total = 0;

    cartList.innerHTML = "";

    cart.forEach(item => {
        let li = document.createElement("li");
        li.className = "cart-item";

        li.innerHTML = `
            <div class="cart-left">
                <span class="item-name">${item.name}</span>
                <span class="item-price">₹${item.price}</span>
            </div>

            <div class="cart-right">
                <button class="qty-btn" onclick="decreaseQty('${item.name}')">-</button>
                <span class="qty">${item.qty}</span>
                <button class="qty-btn" onclick="increaseQty('${item.name}')">+</button>
            </div>
        `;

        cartList.appendChild(li);

        total += item.price * item.qty;
    });

    document.getElementById("total").innerText = "Total: ₹" + total;
}

function updateItemUI(name) {
    let item = cart.find(i => i.name === name);

    document.getElementById(`controls-${name}`).innerHTML = `
        <div class="counter">
            <button onclick="decreaseQty('${name}')">-</button>
            <span>${item.qty}</span>
            <button onclick="increaseQty('${name}')">+</button>
        </div>
    `;
}

function checkout() {
    if (Object.keys(cart).length === 0) {
        alert("Cart is empty");
        return;
    }

    let message = "Order:\n";

    cart.forEach(item => {
        message += `${item.name} x${item.qty}\n`;
    });

    let total = document.getElementById("total").innerText;
    message += `\n${total}`;

    let encoded = encodeURIComponent(message);

    let phone = "15551794813"; // your number

    window.location.href = `https://wa.me/${phone}?text=${encoded}`;
}

// hi
//sunday