import { createContext, useContext, useEffect, useId, useRef } from "react";
import { Link } from "react-router-dom";
import { formatDate } from "./api";

export const ConfigContext = createContext(null);
export const useConfig = () => useContext(ConfigContext);

export function Icon({ name, size = 20 }) {
  const paths = {
    leaf: (
      <>
        <path d="M20 4c-8-1-15 2-15 9a6 6 0 0 0 6 6c7 0 10-7 9-15Z" />
        <path d="m4 21 11-11M8 17v-5m0 5h5" />
      </>
    ),
    orders: (
      <>
        <rect x="5" y="4" width="14" height="17" rx="2" />
        <path d="M9 4V2h6v2M9 10h6M9 14h6M9 18h3" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    inventory: (
      <>
        <path d="M3 8 12 3l9 5v9l-9 4-9-4V8Z" />
        <path d="m3 8 9 5 9-5M12 13v8" />
      </>
    ),
    customers: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5" />
      </>
    ),
    deliveries: (
      <>
        <path d="M2 5h12v12H2zM14 9h4l4 5v3h-8" />
        <circle cx="6" cy="18" r="2" />
        <circle cx="18" cy="18" r="2" />
      </>
    ),
    search: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="m15 15 5 5" />
      </>
    ),
    arrow: <path d="m9 5 7 7-7 7" />,
    back: <path d="m14 5-7 7 7 7" />,
    check: <path d="m5 12 4 4L19 6" />,
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 2v6m10-6v6M3 11h18m-13 4h2m4 0h2" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.orders}
    </svg>
  );
}

export function PageHeader({ eyebrow, title, description, children }) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children && <div className="heading-action">{children}</div>}
    </div>
  );
}

export function Notice({ error, success, children }) {
  const noticeRef = useRef(null);
  useEffect(() => {
    if (error) {
      noticeRef.current?.focus();
      noticeRef.current?.scrollIntoView({ block: "center" });
    }
  }, [error]);
  if (!error && !success && !children) return null;
  return (
    <div
      ref={noticeRef}
      tabIndex={error ? -1 : undefined}
      className={`notice ${error ? "error" : "success"}`}
      role={error ? "alert" : "status"}
    >
      {error || success || children}
    </div>
  );
}

export function Loading({ text = "Loading records…" }) {
  return (
    <div className="empty-state" role="status">
      <span className="loading-dot" />
      {text}
    </div>
  );
}

export function Empty({ title = "No orders found", children }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name="orders" size={24} />
      </span>
      <h3>{title}</h3>
      <p>{children || "Try a different search or filter."}</p>
    </div>
  );
}

export function Search({ value, onChange, label, placeholder }) {
  const id = useId();
  return (
    <div className="search-field">
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      <Icon name="search" size={18} />
      <input
        id={id}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

export function Status({ value }) {
  const { statuses } = useConfig();
  return (
    <span className={`status-badge status-${statuses.indexOf(value)}`}>
      <span className="status-dot" />
      {value}
    </span>
  );
}

export function OrdersTable({ orders, delivery = false }) {
  if (!orders.length)
    return (
      <Empty title={delivery ? "No deliveries scheduled" : "No orders found"}>
        {delivery
          ? "There are no orders scheduled for these dates. Choose another date or create an order."
          : "Try another filter, or create a new order to get started."}
      </Empty>
    );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={
        delivery ? "Scrollable delivery table" : "Scrollable order table"
      }
    >
      <table>
        <caption className="sr-only">
          {delivery ? "Scheduled deliveries" : "Produce orders"}
        </caption>
        <thead>
          <tr>
            <th scope="col">Order number</th>
            <th scope="col">Customer</th>
            {delivery ? (
              <>
                <th scope="col">Phone</th>
                <th scope="col">Delivery address</th>
              </>
            ) : (
              <th scope="col">Received</th>
            )}
            <th scope="col">Scheduled delivery</th>
            {!delivery && <th scope="col">Responsible staff</th>}
            <th scope="col">Status</th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td>
                <Link className="order-number" to={`/orders/${order.id}`}>
                  {order.order_number}
                </Link>
              </td>
              <td className="customer-name">{order.customer.full_name}</td>
              {delivery ? (
                <>
                  <td className="nowrap">{order.customer.phone}</td>
                  <td className="address-cell">{order.delivery_address}</td>
                </>
              ) : (
                <td className="nowrap">{formatDate(order.received_date)}</td>
              )}
              <td className="nowrap">
                {formatDate(order.scheduled_delivery_date)}
              </td>
              {!delivery && <td>{order.responsible_staff_name}</td>}
              <td>
                <Status value={order.status} />
              </td>
              <td>
                <div className="table-actions">
                  <Link
                    className="table-action"
                    aria-label={`${delivery ? "Open" : "View / Edit"} ${order.order_number}`}
                    to={`/orders/${order.id}`}
                  >
                    {delivery ? "Open" : "View / Edit"}
                    <Icon name="arrow" size={14} />
                  </Link>
                  {!delivery && (
                    <Link
                      className="table-action reorder-action"
                      aria-label={`Reorder ${order.order_number}`}
                      to={`/orders/new?reorder=${order.id}`}
                    >
                      Reorder
                    </Link>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
