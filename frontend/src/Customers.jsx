import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, useApi, useDebounce } from "./api";
import { normalizePhone } from "./validation";
import {
  Empty,
  Icon,
  Loading,
  Notice,
  OrdersTable,
  PageHeader,
  Search,
} from "./components";

export function CustomerForm({
  customer,
  onSaved,
  onCancel,
  embedded = false,
}) {
  const [values, setValues] = useState({
    full_name: customer?.full_name || "",
    phone: customer?.phone || "",
    email: customer?.email || "",
    address: customer?.address || "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const prefix = embedded ? "inline-customer" : "customer";
  function field(name) {
    return {
      id: `${prefix}-${name}`,
      name,
      value: values[name],
      onChange: (e) => setValues({ ...values, [name]: e.target.value }),
    };
  }
  async function submit(event) {
    event.preventDefault();
    if (["full_name", "phone", "address"].some((key) => !values[key].trim()))
      return setError("Full name, phone number, and address cannot be blank.");
    setSaving(true);
    setError("");
    try {
      const phone = normalizePhone(values.phone);
      const saved = await api(
        customer ? `/customers/${customer.id}` : "/customers",
        {
          method: customer ? "PATCH" : "POST",
          body: { ...values, phone, email: values.email.trim() || null },
        },
      );
      onSaved(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <form
      onSubmit={submit}
      className={embedded ? "embedded-form" : "card form-card"}
    >
      <Notice error={error} />
      <fieldset disabled={saving}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor={`${prefix}-full_name`}>
              Full name <span>*</span>
            </label>
            <input
              {...field("full_name")}
              required
              maxLength={150}
              autoComplete="name"
              placeholder="e.g. Mai Nguyen"
            />
          </div>
          <div className="field">
            <label htmlFor={`${prefix}-phone`}>
              Phone number <span>*</span>
            </label>
            <input
              {...field("phone")}
              required
              maxLength={40}
              type="tel"
              autoComplete="tel"
              placeholder="e.g. +84 90 123 4567"
              aria-describedby={`${prefix}-phone-help`}
            />
            <span id={`${prefix}-phone-help`} className="field-help">
              Include + and the country code. International mobile and landline
              numbers are supported.
            </span>
          </div>
          <div className="field">
            <label htmlFor={`${prefix}-email`}>
              Email <span className="optional">(optional)</span>
            </label>
            <input
              {...field("email")}
              type="email"
              maxLength={254}
              autoComplete="email"
              placeholder="name@example.com"
            />
          </div>
          <div className="field full-width">
            <label htmlFor={`${prefix}-address`}>
              Address <span>*</span>
            </label>
            <textarea
              {...field("address")}
              required
              maxLength={1000}
              autoComplete="street-address"
              rows={2}
              placeholder="Street address, district, city"
            />
          </div>
        </div>
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="button primary" type="submit">
            {saving
              ? "Saving…"
              : customer
                ? "Save Customer"
                : "Create Customer"}
          </button>
        </div>
      </fieldset>
    </form>
  );
}

export function CustomerChoice({ selected, onSelect }) {
  const [refresh, setRefresh] = useState(0);
  const result = useApi("/customers", refresh);
  const [mode, setMode] = useState("existing");
  const [success, setSuccess] = useState("");
  const [search, setSearch] = useState("");
  const normalize = (text) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase();
  const matches = (result.data || []).filter((customer) =>
    normalize(`${customer.full_name} ${customer.phone}`).includes(normalize(search.trim())),
  );
  return (
    <section className="card form-card">
      <div className="section-heading">
        <div>
          <h2>Customer</h2>
          <p>Select a saved customer or create one here.</p>
        </div>
        <span className="step-number">01</span>
      </div>
      <div className="segmented">
        <button
          type="button"
          aria-pressed={mode === "existing"}
          className={mode === "existing" ? "active" : ""}
          onClick={() => setMode("existing")}
        >
          Existing customer
        </button>
        <button
          type="button"
          aria-pressed={mode === "new"}
          className={mode === "new" ? "active" : ""}
          onClick={() => {
            setMode("new");
            setSearch("");
            onSelect(null);
            setSuccess("");
          }}
        >
          New customer
        </button>
      </div>
      <Notice success={success} />
      {mode === "new" ? (
        <CustomerForm
          embedded
          onCancel={() => setMode("existing")}
          onSaved={(customer) => {
            onSelect(customer);
            setSearch(customer.full_name);
            setMode("existing");
            setRefresh((n) => n + 1);
            setSuccess("Customer created. Complete the order below.");
          }}
        />
      ) : (
        <>
          {result.loading ? (
            <Loading text="Loading customers…" />
          ) : result.error ? (
            <Notice error={result.error} />
          ) : (
            <div className="field">
              <label htmlFor="search-customer">
                Search customers <span>*</span>
              </label>
              <input
                id="search-customer"
                type="search"
                placeholder="Type a customer name or phone number…"
                autoComplete="off"
                value={search}
                aria-describedby="customer-search-help"
                onChange={(event) => {
                  setSearch(event.target.value);
                  onSelect(null);
                  setSuccess("");
                }}
              />
              <p id="customer-search-help" className="field-help">
                Type to filter, then select a customer below. Use the phone number or address to distinguish matching names.
              </p>
              {!selected && result.data.length > 0 && (
                <>
                  <p className="field-help" role="status">
                    {matches.length ? `${matches.length} customers found` : "No matching customers. Try another name or choose New customer."}
                  </p>
                  <ul className="customer-search-results" aria-label="Matching customers">
                    {matches.map((customer) => (
                      <li key={customer.id}>
                        <button type="button" onClick={() => {
                          onSelect(customer);
                          setSearch(customer.full_name);
                          setSuccess("");
                        }}>
                          <strong>{customer.full_name}</strong>
                          <span>{customer.phone}</span>
                          <small>{customer.address}</small>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {!result.data.length && (
                <p className="field-help">
                  No customers yet. Choose “New customer” to create the first
                  one.
                </p>
              )}
            </div>
          )}
          {selected && (
            <div className="customer-preview">
              <strong>{selected.full_name}</strong>
              <span>
                {selected.phone}
                {selected.email && ` · ${selected.email}`}
              </span>
              <span>{selected.address}</span>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export function CustomersPage() {
  const [search, setSearch] = useState("");
  const query = useDebounce(search);
  const result = useApi(`/customers?search=${encodeURIComponent(query)}`);
  return (
    <>
      <PageHeader
        eyebrow="CUSTOMER DIRECTORY"
        title="Customers"
        description="Keep customer details together, ready for the next order."
      >
        <Link className="button primary" to="/customers/new">
          <Icon name="plus" size={18} />
          New Customer
        </Link>
      </PageHeader>
      <section className="card">
        <div className="card-toolbar">
          <Search
            label="Search customers"
            value={search}
            onChange={setSearch}
            placeholder="Search by name or phone number…"
          />
          <span className="subtle">
            {result.data
              ? `${result.data.length} customers`
              : "Customer directory"}
          </span>
        </div>
        {result.loading ? (
          <Loading />
        ) : result.error ? (
          <Notice error={result.error} />
        ) : !result.data.length ? (
          <Empty title="No customers found">
            Try a different search or create a customer.
          </Empty>
        ) : (
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Scrollable customer table"
          >
            <table>
              <caption className="sr-only">Customer directory</caption>
              <thead>
                <tr>
                  <th scope="col">Customer</th>
                  <th scope="col">Phone</th>
                  <th scope="col">Email</th>
                  <th scope="col">Address</th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.data.map((customer) => (
                  <tr key={customer.id}>
                    <td>
                      <Link
                        className="customer-name"
                        to={`/customers/${customer.id}`}
                      >
                        {customer.full_name}
                      </Link>
                    </td>
                    <td className="nowrap">{customer.phone}</td>
                    <td>{customer.email || "—"}</td>
                    <td className="address-cell">{customer.address}</td>
                    <td>
                      <Link
                        className="table-action"
                        to={`/customers/${customer.id}`}
                        aria-label={`View ${customer.full_name}`}
                      >
                        View / Edit
                        <Icon name="arrow" size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

export function NewCustomerPage() {
  const navigate = useNavigate();
  return (
    <>
      <Link className="back-link" to="/customers">
        <Icon name="back" size={15} />
        Customers
      </Link>
      <PageHeader
        title="New customer"
        description="Add the contact details used when recording an order. Fields marked * are required."
      />
      <div className="narrow">
        <CustomerForm
          onCancel={() => navigate("/customers")}
          onSaved={(customer) =>
            navigate(`/customers/${customer.id}`, {
              state: { message: "Customer created successfully." },
            })
          }
        />
      </div>
    </>
  );
}

export function CustomerDetailPage() {
  const { id } = useParams();
  const [refresh, setRefresh] = useState(0);
  const customer = useApi(`/customers/${id}`, refresh);
  const orders = useApi(`/customers/${id}/orders`, refresh);
  const location = useLocation();
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState(location.state?.message || "");
  useEffect(() => {
    setEditing(false);
    setMessage(location.state?.message || "");
  }, [id, location.state]);
  if (customer.loading) return <Loading />;
  if (customer.error) return <Notice error={customer.error} />;
  return (
    <>
      <Link className="back-link" to="/customers">
        <Icon name="back" size={15} />
        Customers
      </Link>
      <PageHeader
        eyebrow="CUSTOMER PROFILE"
        title={customer.data.full_name}
        description="Contact details and orders for this customer."
      >
        <button
          className="button secondary"
          onClick={() => setEditing((value) => !value)}
        >
          {editing ? "Close editor" : "Edit Customer"}
        </button>
      </PageHeader>
      <Notice success={message} />
      {editing ? (
        <div className="narrow">
          <CustomerForm
            customer={customer.data}
            onCancel={() => setEditing(false)}
            onSaved={() => {
              setEditing(false);
              setMessage(
                "Customer updated. Existing order delivery addresses have been preserved.",
              );
              setRefresh((n) => n + 1);
            }}
          />
        </div>
      ) : (
        <section className="card profile-card">
          <div>
            <span className="detail-label">Phone number</span>
            <p>{customer.data.phone}</p>
          </div>
          <div>
            <span className="detail-label">Email</span>
            <p>{customer.data.email || "Not provided"}</p>
          </div>
          <div>
            <span className="detail-label">Saved address</span>
            <p>{customer.data.address}</p>
          </div>
        </section>
      )}
      <section className="card">
        <div className="card-toolbar">
          <h2>Customer orders</h2>
          <span className="subtle">{orders.data?.length || 0} orders</span>
        </div>
        {orders.loading ? (
          <Loading />
        ) : orders.error ? (
          <Notice error={orders.error} />
        ) : (
          <OrdersTable orders={orders.data} />
        )}
      </section>
    </>
  );
}
