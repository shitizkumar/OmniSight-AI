
import { useState } from 'react'
import './App.css'

function App() {
  const [quantity, setQuantity] = useState('1')
  const [submitted, setSubmitted] = useState(false)

  const formatPrice = (amount) =>
    new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount)

  function handleSubmit(event) {
    event.preventDefault()
    setSubmitted(true)
  }

  return (
    <main className="store">
      <header className="header">
        <a className="brand" href="/">OmniStore</a>
        <span>Demo checkout</span>
      </header>

      <section className="checkout">
        <div className="product">
          <div className="product-image" aria-hidden="true">
            🎒
          </div>
          <p className="eyebrow">EVERYDAY COLLECTION</p>
          <h1>Everyday Backpack</h1>
          <p className="description">
            A simple, lightweight backpack for everyday adventures.
          </p>
          <p className="price">{formatPrice(2499)}</p>

          <label htmlFor="quantity">Quantity</label>
          <select
            id="quantity"
            value={quantity}
            onChange={(event) => {
              setQuantity(event.target.value)
              setSubmitted(false)
            }}
          >
            {[1, 2, 3, 4, 5].map((number) => (
              <option key={number} value={number}>
                {number}
              </option>
            ))}
          </select>

          <div className="total">
            <span>Total</span>
            <strong>{formatPrice(2499 * Number(quantity))}</strong>
          </div>
        </div>

        <form className="checkout-form" onSubmit={handleSubmit}>
          <h2>Checkout details</h2>
          <p className="description">
            Enter your details to place a demo order.
          </p>

          <label htmlFor="name">Full name</label>
          <input id="name" name="name" autoComplete="name" required />

          <label htmlFor="email">Email address</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
          />

          <label htmlFor="address">Street address</label>
          <input
            id="address"
            name="address"
            autoComplete="street-address"
            required
          />

          <div className="field-row">
            <div>
              <label htmlFor="city">City</label>
              <input
                id="city"
                name="city"
                autoComplete="address-level2"
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
                title="Enter a six-digit PIN code"
                required
              />
            </div>
          </div>

          <button type="submit">
            Place demo order · {formatPrice(2499 * Number(quantity))}
          </button>

          {submitted && (
            <p className="success" role="status">
              Demo order submitted successfully. No payment was processed.
            </p>
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
