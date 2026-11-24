import { totalQuantity } from "./validation";
import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, formatDate, formatTime, today, useApi, useDebounce } from "./api";
import { CustomerChoice } from "./Customers";
import {
  Icon,
  Loading,
  Notice,
  OrdersTable,
  PageHeader,
  Search,
  Status,
  useConfig,
} from "./components";

export function OrdersPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const query = useDebounce(search);
  const { statuses } = useConfig();
  const orders = useApi(
    `/orders?search=${encodeURIComponent(query)}&status=${encodeURIComponent(status)}`,
  );
  const counts = useApi(
    `/orders/status-counts?search=${encodeURIComponent(query)}`,
  );
  return (
    <>
      <PageHeader
        eyebrow="ORDER WORKSPACE"
        title="Orders"
        description="A clear view of every order, from received to delivered."
      >
        <Link className="button primary" to="/orders/new">
          <Icon name="plus" size={18} />
          New Order
        </Link>
      </PageHeader>
      <section className="card orders-card">
        <div className="card-toolbar">
          <Search
            label="Search orders"
            value={search}
            onChange={setSearch}
            placeholder="Search order number or customer name…"
          />
          <span className="subtle">
            {counts.data
              ? `${counts.data.total} matching orders`
              : "Order records"}
          </span>
        </div>
        <div
          className="status-filters"
          role="group"
          aria-label="Filter orders by status"
        >
          {["", ...statuses].map((value) => (
            <button
              key={value}
              type="button"
              className={status === value ? "active" : ""}
              aria-pressed={status === value}
              onClick={() => setStatus(value)}
            >
              {value || "All orders"}
              <span className="filter-count">
                {counts.data
                  ? value
                    ? counts.data.counts[value]
                    : counts.data.total
                  : "—"}
              </span>
            </button>
          ))}
        </div>
        <Notice error={counts.error} />
        {orders.loading ? (
          <Loading />
        ) : orders.error ? (
          <Notice error={orders.error} />
        ) : (
          <OrdersTable orders={orders.data} />
        )}
        <div className="table-footer">
          <span>
            {orders.data
              ? `${orders.data.length} orders shown`
              : "Loading orders…"}
          </span>
          <span>All statuses are updated manually by staff.</span>
        </div>
      </section>
      <div className="page-note">
        <Icon name="calendar" size={17} />
        <span>
          Planning deliveries?{" "}
          <Link to="/deliveries">View the delivery schedule</Link> for a
          selected date.
        </span>
      </div>
    </>
  );
}

export const stockLabel = (product) =>
  product.stock_quantity <= 0
    ? "out of stock"
    : `${product.stock_quantity} ${product.unit} in stock`;

function ProduceItems({ items, onChange, products }) {
  const listId = useId();
  function change(index, patch) {
    onChange(
      items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  }
  const shortages = items.flatMap((item) => {
    const product = products.find((value) => value.id === Number(item.product_id));
    const wanted = Number(item.quantity);
    return product && wanted > product.stock_quantity
      ? [`${product.name} (requested ${wanted}, available ${product.stock_quantity} ${product.unit})`]
      : [];
  });
  return (
    <>
      <datalist id={listId}>
        {products.map((product) => (
          <option value={product.name} key={product.id}>
            {product.category} · {product.unit} · {stockLabel(product)}
          </option>
        ))}
      </datalist>
      <div className="item-labels" aria-hidden="true">
        <span>Produce</span>
        <span>Unit</span>
        <span>Quantity</span>
        <span />
      </div>
      <div className="item-lines">
        {items.map((item, index) => {
          const product = products.find(
            (value) => value.id === Number(item.product_id),
          );
          return (
            <div className="item-line" key={item.key}>
              <div className="field">
                <label className="sr-only" htmlFor={`product-${item.key}`}>
                  Product {index + 1}
                </label>
                <input
                  id={`product-${item.key}`}
                  list={listId}
                  autoComplete="off"
                  required
                  placeholder="Type to search produce…"
                  value={item.productName}
                  onChange={(e) => {
                    const match = products.find(
                      (value) =>
                        value.name.toLowerCase() ===
                        e.target.value.toLowerCase(),
                    );
                    change(index, {
                      productName: e.target.value,
                      product_id: match?.id || "",
                    });
                  }}
                />
              </div>
              <span
                className="item-unit"
                aria-label={`Unit for item ${index + 1}`}
              >
                {product?.unit || "—"}
              </span>
              <div className="field">
                <label className="sr-only" htmlFor={`quantity-${item.key}`}>
                  Quantity {index + 1}
                </label>
                <input
                  id={`quantity-${item.key}`}
                  type="number"
                  required
                  min="0"
                  step="any"
                  inputMode="decimal"
                  value={item.quantity}
                  onChange={(e) => change(index, { quantity: e.target.value })}
                />
              </div>
              <button
                type="button"
                className="remove-item"
                aria-label={`Remove item ${index + 1}`}
                onClick={() => onChange(items.filter((_, i) => i !== index))}
              >
                Remove
              </button>
            </div>
          );
        })}
      </div>
      {shortages.length > 0 && (
        <p className="notice error stock-warning" role="alert">
          Not enough stock: {shortages.join("; ")}.
        </p>
      )}
      {!items.length && (
        <p className="field-help">
          Add at least one produce item to save this order.
        </p>
      )}
      <button
        type="button"
        className="button secondary small"
        onClick={() =>
          onChange([
            ...items,
            {
              key: crypto.randomUUID(),
              product_id: "",
              productName: "",
              quantity: "1",
            },
          ])
        }
      >
        <Icon name="plus" size={16} />
        Add Item
      </button>
      <p className="field-help">
        Choose a product from the suggestions. Decimal quantities are accepted;
        each product can appear once.
      </p>
    </>
  );
}

function OrderEditor({ order, template, customer, onSaved }) {
  const base = order || template;
  const products = useApi("/products");
  const {
    transitions,
    statuses,
    payment_methods,
    max_order_quantity,
    staff_examples,
  } = useConfig();
  const [values, setValues] = useState({
    received_date: order?.received_date || today(),
    scheduled_delivery_date: order?.scheduled_delivery_date || today(),
    delivery_address: base?.delivery_address || customer?.address || "",
    responsible_staff_name: base?.responsible_staff_name || "",
    payment_method: base?.payment_method || "",
    status: order?.status || "",
  });
  const [items, setItems] = useState(
    base
      ? base.items.map((item) => ({
          key: crypto.randomUUID(),
          product_id: item.product_id,
          productName: item.product.name,
          quantity: String(item.quantity),
        }))
      : [
          {
            key: crypto.randomUUID(),
            product_id: "",
            productName: "",
            quantity: "1",
          },
        ],
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const quantityTotal = totalQuantity(items);
  const overLimit = quantityTotal.greaterThan(max_order_quantity);
  useEffect(() => {
    // A reorder keeps the previous order's delivery address until staff change customer.
    if (!order && !(template && customer?.id === template.customer_id))
      setValues((current) => ({
        ...current,
        delivery_address: customer?.address || "",
      }));
  }, [customer?.id, customer?.address, order, template]);
  function field(name) {
    return {
      id: name,
      name,
      value: values[name],
      onChange: (event) => setValues({ ...values, [name]: event.target.value }),
    };
  }
  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!order && !customer)
      return setError(
        "Select an existing customer or create a customer before saving the order.",
      );
    if (
      !values.delivery_address.trim() ||
      !values.responsible_staff_name.trim()
    )
      return setError(
        "Delivery address and responsible staff member cannot be blank.",
      );
    if (!values.received_date || !values.scheduled_delivery_date)
      return setError(
        "Received date and scheduled delivery date are required.",
      );
    if (values.scheduled_delivery_date < values.received_date)
      return setError("Scheduled delivery date cannot precede received date.");
    if (!Object.hasOwn(payment_methods, values.payment_method))
      return setError(
        "Choose a payment method: Cash, QR Banking, or Credit Card.",
      );
    if (!items.length || items.some((item) => !item.product_id))
      return setError(
        "Choose a valid product from the suggestions for every item. An order needs at least one item.",
      );
    if (
      items.some(
        (item) =>
          !Number.isFinite(Number(item.quantity)) || Number(item.quantity) <= 0,
      )
    )
      return setError("Each quantity must be greater than zero.");
    if (overLimit)
      return setError(
        `Total quantity across all products must not exceed ${max_order_quantity}.`,
      );
    if (new Set(items.map((item) => item.product_id)).size !== items.length)
      return setError(
        "Duplicate product lines are not allowed. Combine their quantities into one line.",
      );
    if (order && !transitions[order.status].includes(values.status))
      return setError("Keep the current status or advance to the next status.");
    setSaving(true);
    const body = {
      scheduled_delivery_date: values.scheduled_delivery_date,
      delivery_address: values.delivery_address,
      responsible_staff_name: values.responsible_staff_name,
      payment_method: values.payment_method,
      items: items.map((item) => ({
        product_id: Number(item.product_id),
        quantity: Number(item.quantity),
      })),
    };
    if (order) body.status = values.status;
    else {
      body.customer_id = customer.id;
      body.received_date = values.received_date;
    }
    try {
      onSaved(
        await api(order ? `/orders/${order.id}` : "/orders", {
          method: order ? "PATCH" : "POST",
          body,
        }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <Notice error={error} />
      <fieldset disabled={saving}>
        <section className="card form-card">
          <div className="section-heading">
            <div>
              <h2>Order details</h2>
              <p>
                Dates, delivery address, and the staff member handling this
                order.
              </p>
            </div>
            {!order && <span className="step-number">02</span>}
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="received_date">
                Received date <span>*</span>
              </label>
              <input
                {...field("received_date")}
                type="date"
                required
                readOnly={!!order}
              />
            </div>
            <div className="field">
              <label htmlFor="scheduled_delivery_date">
                Scheduled delivery date <span>*</span>
              </label>
              <input
                {...field("scheduled_delivery_date")}
                type="date"
                required
                min={values.received_date}
              />
            </div>
            <div className="field full-width">
              <label htmlFor="delivery_address">
                Delivery address <span>*</span>
              </label>
              <textarea
                {...field("delivery_address")}
                required
                maxLength={1000}
                rows={2}
                placeholder="Select a customer to prefill their saved address"
              />
              <span className="field-help">
                Saved for this order only. Editing it does not change the
                customer profile.
              </span>
            </div>
            <div className="field full-width">
              <label htmlFor="responsible_staff_name">
                Responsible staff member <span>*</span>
              </label>
              <input
                {...field("responsible_staff_name")}
                required
                maxLength={150}
                placeholder="e.g. Lan Nguyen — Sales Coordinator"
                list="staff-examples"
              />
              <datalist id="staff-examples">
                {staff_examples.map((staff) => (
                  <option key={staff} value={staff} />
                ))}
              </datalist>
            </div>
            <div className="field full-width">
              <label htmlFor="payment_method">
                Payment method <span>*</span>
              </label>
              <select {...field("payment_method")} required>
                <option value="">
                  {order && !order.payment_method
                    ? "Not recorded — select a payment method"
                    : "Select a payment method"}
                </option>
                {Object.entries(payment_methods).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <span className="field-help">
                Record the customer's chosen payment method. Payment is handled
                separately.
              </span>
            </div>
          </div>
        </section>
        <section className="card form-card">
          <div className="section-heading">
            <div>
              <h2>Produce items</h2>
              <p>Add the products and quantities requested by the customer.</p>
            </div>
            <span className="subtle">
              {items.length} {items.length === 1 ? "item" : "items"}
            </span>
          </div>
          <p
            className={`quantity-summary ${overLimit ? "over-limit" : ""}`}
            role="status"
          >
            Total quantity:{" "}
            <strong>
              {quantityTotal.toString()} / {max_order_quantity}
            </strong>
            {overLimit && " — Reduce quantities before saving."}
          </p>
          {products.loading ? (
            <Loading text="Loading produce catalogue…" />
          ) : products.error ? (
            <Notice error={products.error} />
          ) : (
            <ProduceItems
              products={products.data}
              items={items}
              onChange={setItems}
            />
          )}
        </section>
        {order && (
          <section className="card form-card">
            <div className="section-heading">
              <div>
                <h2>Order status</h2>
                <p>Record progress manually as the order moves forward.</p>
              </div>
            </div>
            <div className="field">
              <label htmlFor="status">Status</label>
              <select {...field("status")}>
                {transitions[order.status].map((status) => (
                  <option key={status}>{status}</option>
                ))}
              </select>
              <span className="field-help">
                Keep the current status or advance one step. These updates are
                staff records, not courier confirmations.
              </span>
            </div>
          </section>
        )}
        <div className="save-bar">
          <span className="subtle">
            {order
              ? "Changes are saved together."
              : `New orders start with ${statuses[0]} status. Stock is deducted when saved.`}
          </span>
          <div>
            <Link className="button secondary" to="/">
              Cancel
            </Link>
            <button
              type="submit"
              disabled={products.loading || !!products.error}
              className="button primary"
            >
              <Icon name="check" size={17} />
              {saving ? "Saving…" : order ? "Save Changes" : "Save Order"}
            </button>
          </div>
        </div>
      </fieldset>
    </form>
  );
}

export function NewOrderPage() {
  const [params] = useSearchParams();
  const reorderId = params.get("reorder");
  return reorderId ? (
    <ReorderLoader key={reorderId} id={reorderId} />
  ) : (
    <NewOrderForm />
  );
}

function ReorderLoader({ id }) {
  const source = useApi(`/orders/${id}`);
  if (source.loading) return <Loading text="Loading previous order…" />;
  if (source.error)
    return (
      <>
        <Notice error={source.error} />
        <Link to="/orders/new">Start a new order instead</Link>
      </>
    );
  return <NewOrderForm template={source.data} />;
}

function NewOrderForm({ template }) {
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(template?.customer || null);
  return (
    <>
      <Link className="back-link" to={template ? `/customers/${template.customer_id}` : "/"}>
        <Icon name="back" size={15} />
        {template ? template.customer.full_name : "Orders"}
      </Link>
      <PageHeader
        eyebrow={template ? "REORDER" : "RECORD AN ORDER"}
        title={template ? "Reorder" : "New order"}
        description={
          template
            ? `Pre-filled from ${template.order_number}. Adjust products, quantities and the delivery date, then save. The original order is not changed.`
            : "Choose a customer, add produce, and set a delivery date. Fields marked * are required."
        }
      />
      <div className="editor-layout">
        <div>
          <CustomerChoice selected={customer} onSelect={setCustomer} />
          <OrderEditor
            template={template}
            customer={customer}
            onSaved={(order) =>
              navigate(`/orders/${order.id}`, {
                state: {
                  message: `${order.order_number} created successfully.`,
                },
              })
            }
          />
        </div>
        <aside className="context-card">
          <span className="context-icon">
            <Icon name="orders" size={24} />
          </span>
          <h3>Ready for the next step</h3>
          <p>
            Once saved, the order appears in Orders and on its scheduled
            delivery date. Stock is checked and deducted automatically.
          </p>
          <hr />
          <p>
            You can add or change produce and update progress from the order
            detail page.
          </p>
        </aside>
      </div>
    </>
  );
}

function CancelDialog({ order, onClose, onCancelled }) {
  const ref = useRef(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  async function confirm() {
    setBusy(true);
    setError("");
    try {
      onCancelled(
        await api(`/orders/${order.id}/cancel`, {
          method: "POST",
          body: { reason: reason.trim() || null },
        }),
      );
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }
  return (
    <dialog ref={ref} className="confirm-dialog" onClose={onClose} onCancel={(e) => busy && e.preventDefault()}>
      <h2>Cancel {order.order_number}?</h2>
      <p>
        The order stays in the history as Cancelled and can no longer be
        processed or handed to a courier. Reserved stock is returned to
        inventory. This cannot be undone.
      </p>
      <div className="field">
        <label htmlFor="cancel-reason">Reason (optional)</label>
        <textarea
          id="cancel-reason"
          rows={3}
          maxLength={500}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Customer changed their mind"
        />
      </div>
      <Notice error={error} />
      <div className="dialog-actions">
        <button type="button" className="button secondary" disabled={busy} onClick={() => ref.current?.close()}>
          Keep Order
        </button>
        <button type="button" className="button primary danger" disabled={busy} onClick={confirm}>
          {busy ? "Cancelling…" : "Cancel Order"}
        </button>
      </div>
    </dialog>
  );
}

export function OrderDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [deleteError, setDeleteError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [cancelling, setCancelling] = useState(false);
  const { cancellable } = useConfig();
  const result = useApi(`/orders/${id}`, refresh);
  const [message, setMessage] = useState(location.state?.message || "");
  useEffect(() => {
    setMessage(location.state?.message || "");
  }, [id, location.state]);
  if (result.loading) return <Loading text="Loading order…" />;
  if (result.error) return <Notice error={result.error} />;
  const order = result.data;
  return (
    <>
      <Link className="back-link" to="/">
        <Icon name="back" size={15} />
        Orders
      </Link>
      <PageHeader
        eyebrow="ORDER DETAILS"
        title={order.order_number}
        description={`Received ${formatDate(order.received_date)} · Edit the order and record its progress.`}
      >
        <Status value={order.status} />
        <Link className="button secondary" to={`/orders/new?reorder=${order.id}`}>
          Reorder
        </Link>
        {cancellable.includes(order.status) && (
          <button type="button" className="button secondary" onClick={() => setCancelling(true)}>
            Cancel Order
          </button>
        )}
        <button
          type="button"
          className="button secondary"
          onClick={async () => {
            if (!window.confirm(`Delete order ${order.order_number}? This cannot be undone.`)) return;
            try {
              await api(`/orders/${order.id}`, { method: "DELETE" });
              navigate("/", { state: { message: `Order ${order.order_number} deleted.` } });
            } catch (err) {
              setMessage("");
              setDeleteError(err.message);
            }
          }}
        >
          Delete Order
        </button>
      </PageHeader>
      <Notice error={deleteError} />
      <Notice success={message} />
      {cancelling && (
        <CancelDialog
          order={order}
          onClose={() => setCancelling(false)}
          onCancelled={() => {
            setCancelling(false);
            setMessage(`${order.order_number} cancelled. Stock has been restored.`);
            setRefresh((value) => value + 1);
          }}
        />
      )}
      <div className="editor-layout">
        <div>
          <section className="card form-card">
            <div className="section-heading">
              <h2>Customer</h2>
              <Link
                className="text-link"
                to={`/customers/${order.customer_id}`}
              >
                View customer profile
                <Icon name="arrow" size={14} />
              </Link>
            </div>
            <div className="customer-preview plain">
              <strong>{order.customer.full_name}</strong>
              <span>
                {order.customer.phone}
                {order.customer.email && ` · ${order.customer.email}`}
              </span>
              <span>Profile address: {order.customer.address}</span>
            </div>
          </section>
          {order.status === "Cancelled" ? (
            <section className="card form-card cancelled-summary">
              <div className="section-heading">
                <div>
                  <h2>This order was cancelled</h2>
                  <p>
                    {order.cancelled_at && `Cancelled ${formatTime(order.cancelled_at)}. `}
                    Cancelled orders are kept for the record and cannot be edited or processed.
                  </p>
                </div>
              </div>
              <p>
                <strong>Reason:</strong> {order.cancellation_reason || "No reason given"}
              </p>
              <ul className="cancelled-items">
                {order.items.map((item) => (
                  <li key={item.id}>
                    {item.product.name} — {item.quantity} {item.product.unit}
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <OrderEditor
              key={`${id}-${refresh}`}
              order={order}
              onSaved={() => {
                setMessage("Order changes saved successfully.");
                setRefresh((value) => value + 1);
              }}
            />
          )}
        </div>
        <aside className="card history-card">
          <div className="section-heading">
            <div>
              <h2>Status history</h2>
              <p>Manual staff updates</p>
            </div>
          </div>
          <ol className="history-list">
            {[...order.status_history].reverse().map((entry) => (
              <li key={entry.id}>
                <span className="history-dot" />
                <strong>{entry.new_status}</strong>
                <span>
                  {entry.previous_status
                    ? `${entry.previous_status} → ${entry.new_status}`
                    : "Order created"}
                </span>
                <time dateTime={entry.changed_at}>
                  {formatTime(entry.changed_at)}
                </time>
              </li>
            ))}
          </ol>
          <p className="field-help">
            Recorded by staff. No live courier tracking or courier confirmation.
          </p>
        </aside>
      </div>
    </>
  );
}

export function DeliveriesPage() {
  const [from, setFrom] = useState(today());
  const [to, setTo] = useState(today());
  const [range, setRange] = useState(false);
  const [filter, setFilter] = useState({ from: today(), to: today() });
  const [error, setError] = useState("");
  const result = useApi(
    `/deliveries?date_from=${filter.from}&date_to=${filter.to}`,
  );
  function apply(event) {
    event.preventDefault();
    if (!from || (range && !to)) return setError("Select a delivery date.");
    if (range && to < from)
      return setError("End date cannot precede start date.");
    setError("");
    setFilter({ from, to: range ? to : from });
  }
  return (
    <>
      <PageHeader
        eyebrow="DELIVERY SCHEDULE"
        title="Deliveries"
        description="See every order scheduled for a date, including orders already delivered."
      />
      <section className="card delivery-filters">
        <form onSubmit={apply}>
          <div className="field">
            <label htmlFor="date-from">
              {range ? "From date" : "Delivery date"}
            </label>
            <input
              id="date-from"
              type="date"
              value={from}
              required
              onChange={(e) => setFrom(e.target.value)}
            />
          </div>
          {range && (
            <div className="field">
              <label htmlFor="date-to">To date</label>
              <input
                id="date-to"
                type="date"
                value={to}
                required
                min={from}
                onChange={(e) => setTo(e.target.value)}
              />
            </div>
          )}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={range}
              onChange={(e) => {
                setRange(e.target.checked);
                if (to < from) setTo(from);
              }}
            />
            Use date range
          </label>
          <button className="button primary" type="submit">
            Show Deliveries
          </button>
          <button
            className="button secondary"
            type="button"
            onClick={() => {
              const value = today();
              setFrom(value);
              setTo(value);
              setRange(false);
              setFilter({ from: value, to: value });
              setError("");
            }}
          >
            Today
          </button>
        </form>
        <Notice error={error} />
      </section>
      <section className="card">
        <div className="card-toolbar">
          <div>
            <h2>
              {filter.from === filter.to
                ? formatDate(filter.from)
                : `${formatDate(filter.from)} – ${formatDate(filter.to)}`}
            </h2>
            <p className="field-help">
              Sorted by scheduled delivery date, then order number.
            </p>
          </div>
          <span className="subtle">
            {result.data
              ? `${result.data.length} scheduled orders`
              : "Loading…"}
          </span>
        </div>
        {result.loading ? (
          <Loading />
        ) : result.error ? (
          <Notice error={result.error} />
        ) : (
          <OrdersTable orders={result.data} delivery />
        )}
      </section>
    </>
  );
}
