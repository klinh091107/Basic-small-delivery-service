import React, { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useApi } from "./api";
import { ConfigContext, Icon, Loading, Notice } from "./components";
import {
  CustomersPage,
  CustomerDetailPage,
  NewCustomerPage,
} from "./Customers";
import {
  DeliveriesPage,
  NewOrderPage,
  OrderDetailPage,
  OrdersPage,
} from "./Orders";
import ProduceArt from "./ProduceArt";
import { StaffMenu, useAuth } from "./Auth";

export default function App() {
  const { employee } = useAuth();
  const [retry, setRetry] = useState(0);
  const config = useApi("/config", retry);
  const location = useLocation();
  const section = location.pathname.startsWith("/customers")
    ? "Customers"
    : location.pathname === "/deliveries"
      ? "Deliveries"
      : "Orders";
  useEffect(() => {
    window.scrollTo(0, 0);
    document.title = `${section} · FreshRoute Produce Delivery`;
  }, [location.pathname, section]);
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <Icon name="leaf" size={25} />
          </span>
          <span>
            FreshRoute<small>PRODUCE DELIVERY</small>
          </span>
        </Link>
        
        <nav aria-label="Main navigation">
          <NavLink to="/" end>
            <Icon name="orders" />
            Orders
          </NavLink>
          <NavLink to="/orders/new">
            <Icon name="plus" />
            New Order
          </NavLink>
          <NavLink to="/customers">
            <Icon name="customers" />
            Customers
          </NavLink>
          <NavLink to="/deliveries">
            <Icon name="deliveries" />
            Deliveries
          </NavLink>
        </nav>
        <StaffMenu />
      </aside>
      <div className="main-shell">
        <header className="workspace-banner">
          <div className="banner-inner">
            <div className="banner-copy">
              <span className="eyebrow">FRESH FRUIT. VEGETABLES. PRODUCE BOXES.</span>
              <h1>Fresh produce, on its way.</h1>
              <p>Fresh fruit, vegetables and produce boxes for households and businesses.</p>
              <span className="workspace-welcome">Welcome, {employee.full_name}</span>
            </div>
            <ProduceArt />
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {config.loading ? (
            <Loading text="Connecting to FreshRoute Produce Delivery…" />
          ) : config.error ? (
            <>
              <Notice error={config.error} />
              <button
                className="button secondary"
                onClick={() => setRetry((value) => value + 1)}
              >
                Retry Connection
              </button>
            </>
          ) : (
            <ConfigContext.Provider value={config.data}>
              <Routes>
                <Route path="/" element={<OrdersPage />} />
                <Route path="/orders/new" element={<NewOrderPage />} />
                <Route path="/orders/:id" element={<OrderDetailPage />} />
                <Route path="/customers" element={<CustomersPage />} />
                <Route path="/customers/new" element={<NewCustomerPage />} />
                <Route path="/customers/:id" element={<CustomerDetailPage />} />
                <Route path="/deliveries" element={<DeliveriesPage />} />
                <Route
                  path="*"
                  element={
                    <>
                      <h1>Page not found</h1>
                      <Link to="/">Back to Orders</Link>
                    </>
                  }
                />
              </Routes>
            </ConfigContext.Provider>
          )}
        </main>
        <footer className="app-footer">
          <span>FreshRoute Produce Delivery</span>
          <span>Simple records. Clear progress.</span>
        </footer>
      </div>
    </div>
  );
}
