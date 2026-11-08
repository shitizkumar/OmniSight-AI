import { useState } from 'react'
import './App.css'

const PRODUCT_PRICE = 2499
const SHIPPING_FEE = 99
const FREE_SHIPPING_LIMIT = 5000

function App() {
  const [quantity, setQuantity] = useState(1)
  const [orderReference, setOrderReference] = useState('')

  const subtotal = PRODUCT_PRICE * quantity
  const shipping = subtotal >= FREE_SHIPPING_LIMIT ? 0 : SHIPPING_FEE
  const total = subtotal + shipping

  const formatPrice = (amount) =>
    new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount)

  function handleSubmit(event) {
    event.preventDefault()

    if (!event.currentTarget.reportValidity()) return

    setOrderReference(
      `OMNI-${Date.now().toString(36).toUpperCase()}`
    )
  }

  function handleQuantityChange(event) {
    setQuantity(Number(event.target.value))
    setOrderReference('')
  }

  return (
    <main className="store">
      <header className="header">
        <a className="brand" href="/">OmniStore</a>
        <span>Secure demo checkout</span>
      </header>

      <section className="checkout">
        <div className="product">
          <div className="product-image" aria-hidden="true">
            &#127890;
          </div>

          <p className="eyebrow">EVERYDAY COLLECTION</p>
          <h1>Everyday Backpack</h1>

          <p className="description">
            A simple, lightweight backpack designed for everyday
            adventures, work and travel.
          </p>

          <p className="price">{formatPrice(PRODUCT_PRICE)}</p>

          <label htmlFor="quantity">Quantity</label>
          <select
            id="quantity"
            value={quantity}
            onChange={handleQuantityChange}
          >
            {[1, 2, 3, 4, 5].map((number) => (
              <option key={number} value={number}>
                {number}
              </option>
            ))}
          </select>

          <div className="order-summary">
            <h2>Order summary</h2>

            <div className="summary-row">
              <span>Subtotal ({quantity} items)</span>
              <span>{formatPrice(subtotal)}</span>
            </div>

            <div className="summary-row">
              <span>Shipping</span>
              <span>
                {shipping === 0 ? 'Free' : formatPrice(shipping)}
              </span>
            </div>

            <div className="total">
              <strong>Total</strong>
              <strong>{formatPrice(total)}</strong>
            </div>

            <p className="shipping-note">
              {shipping === 0
                ? 'You qualify for free shipping.'
                : `Add ${formatPrice(FREE_SHIPPING_LIMIT - subtotal)} more for free shipping.`}
            </p>
          </div>
        </div>

        <form className="checkout-form" onSubmit={handleSubmit}>
          <h2>Checkout details</h2>
          <p className="description">
            Enter your delivery details to place a demo order.
          </p>

          <label htmlFor="name">Full name</label>
          <input
            id="name"
            name="name"
            autoComplete="name"
            placeholder="Enter your full name"
            minLength={2}
            required
          />

          <label htmlFor="email">Email address</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            required
          />

          <label htmlFor="address">Street address</label>
          <input
            id="address"
            name="address"
            autoComplete="street-address"
            placeholder="House number and street"
            required
          />

          <div className="field-row">
            <div>
              <label htmlFor="city">City</label>
              <input
                id="city"
                name="city"
                autoComplete="address-level2"
                placeholder="Your city"
                required
              />
            </div>

            <div>
              <label htmlFor="postalCode">PIN code</label>
              <input
                id="postalCode"
                name="postalCode"
                inputMode="numeric"
                autoComplete="postal-code"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="6-digit PIN"
                title="Enter a six-digit PIN code"
                required
              />
            </div>
          </div>

          <button type="submit">
            Place demo order &#183; {formatPrice(total)}
          </button>

          {orderReference && (
            <div className="success" role="status" aria-live="polite">
              <strong>Demo order confirmed!</strong>
              <p>Your order reference: {orderReference}</p>
              <p>No payment was processed or real order created.</p>
            </div>
          )}

          <p className="notice">
            Test application only. No real payment or order is created.
          </p>
        </form>
      </section>
    </main>
  )
}

export default App
