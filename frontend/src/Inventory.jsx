import { useState } from "react";
import { api, formatTime, useApi, useDebounce } from "./api";
import { Empty, Icon, Loading, Notice, PageHeader, Search } from "./components";

const UNITS = ["kg", "pieces", "packs", "bunch", "box"];

export function stockState(product) {
  if (product.stock_quantity <= 0) return "out";
  if (product.stock_quantity <= product.low_stock_threshold) return "low";
  return "ok";
}

function StockBadge({ product }) {
  const state = stockState(product);
  const label = { ok: "In stock", low: "Low stock", out: "Out of stock" }[state];
  return (
    <span className={`stock-badge stock-${state}`}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

function AddProduct({ onAdded, onCancel }) {
  const empty = { name: "", category: "", unit: "kg", stock_quantity: "0", low_stock_threshold: "5" };
  const [values, setValues] = useState(empty);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const field = (name) => ({
    id: `new-product-${name}`,
    value: values[name],
    onChange: (e) => setValues({ ...values, [name]: e.target.value }),
  });
  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!values.name.trim() || !values.category.trim() || !values.unit.trim())
      return setError("Product name, category and unit are required.");
    if (Number(values.stock_quantity) < 0 || Number(values.low_stock_threshold) < 0)
      return setError("Quantities cannot be negative.");
    setSaving(true);
    try {
      const saved = await api("/products", {
        method: "POST",
        body: {
          ...values,
          stock_quantity: Number(values.stock_quantity),
          low_stock_threshold: Number(values.low_stock_threshold),
        },
      });
      onAdded(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <form className="inventory-add" onSubmit={submit}>
      <Notice error={error} />
      <fieldset disabled={saving}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="new-product-name">Product name <span>*</span></label>
            <input {...field("name")} required maxLength={150} />
          </div>
          <div className="field">
            <label htmlFor="new-product-category">Category <span>*</span></label>
            <input {...field("category")} required maxLength={100} placeholder="e.g. Vegetables" />
          </div>
          <div className="field">
            <label htmlFor="new-product-unit">Unit <span>*</span></label>
            <input {...field("unit")} required maxLength={30} list="unit-options" />
            <datalist id="unit-options">{UNITS.map((u) => <option key={u} value={u} />)}</datalist>
          </div>
          <div className="field">
            <label htmlFor="new-product-stock_quantity">Opening stock</label>
            <input {...field("stock_quantity")} type="number" min="0" step="any" />
          </div>
          <div className="field">
            <label htmlFor="new-product-low_stock_threshold">Low-stock warning at</label>
            <input {...field("low_stock_threshold")} type="number" min="0" step="any" />
          </div>
        </div>
        <div className="dialog-actions">
          <button type="button" className="button secondary" onClick={onCancel}>Cancel</button>
          <button type="submit" className="button primary">
            <Icon name="check" size={17} />
            {saving ? "Saving…" : "Add Product"}
          </button>
        </div>
      </fieldset>
    </form>
  );
}

function ProductRow({ product, onSaved, onMessage }) {
  const [qty, setQty] = useState(String(product.stock_quantity));
  const [threshold, setThreshold] = useState(String(product.low_stock_threshold));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const state = stockState(product);
  const changed = qty !== String(product.stock_quantity) || threshold !== String(product.low_stock_threshold);
  async function save() {
    if (qty.trim() === "" || !Number.isFinite(Number(qty)) || Number(qty) < 0 || threshold.trim() === "" || Number(threshold) < 0)
      return setError("Enter a quantity of zero or more.");
    setSaving(true);
    setError("");
    try {
      await api(`/products/${product.id}`, {
        method: "PATCH",
        body: { stock_quantity: Number(qty), low_stock_threshold: Number(threshold) },
      });
      onMessage(`${product.name} stock updated to ${Number(qty)} ${product.unit}.`);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }
  const onKey = (e) => e.key === "Enter" && (e.preventDefault(), save());
  return (
    <tr className={state === "ok" ? "" : `inventory-row-${state}`}>
      <td className="customer-name">{product.name}</td>
      <td className="nowrap">
        <input
          className="qty-input"
          aria-label={`Available quantity for ${product.name}`}
          type="number"
          min="0"
          step="any"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          onKeyDown={onKey}
        />
      </td>
      <td>{product.unit}</td>
      <td>
        <input
          className="qty-input"
          aria-label={`Low-stock level for ${product.name}`}
          type="number"
          min="0"
          step="any"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
          onKeyDown={onKey}
        />
      </td>
      <td><StockBadge product={product} /></td>
      <td className="nowrap">{product.stock_updated_at ? formatTime(product.stock_updated_at) : "—"}</td>
      <td>
        <div className="table-actions">
          <button type="button" className="button primary small" disabled={saving || !changed} onClick={save}>
            {saving ? "Saving…" : "Update stock"}
          </button>
          {error && <span className="field-help" role="alert">{error}</span>}
        </div>
      </td>
    </tr>
  );
}

export function InventoryPage() {
  const [search, setSearch] = useState("");
  const query = useDebounce(search);
  const [refresh, setRefresh] = useState(0);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");
  const result = useApi(`/products?search=${encodeURIComponent(query)}`, refresh);
  const all = useApi("/products", refresh);
  const alerts = (all.data || []).filter((product) => stockState(product) !== "ok");
  return (
    <>
      <PageHeader
        eyebrow="STOCK CONTROL"
        title="Inventory Management"
        description="Set the available quantity of each product. Orders deduct stock automatically; cancelled orders return it."
      >
        <button type="button" className="button primary" onClick={() => setAdding((value) => !value)}>
          <Icon name="plus" size={18} />
          Add Product
        </button>
      </PageHeader>
      <Notice success={message} />
      {alerts.length > 0 && (
        <p className="notice error stock-alerts" role="status">
          {alerts.filter((p) => stockState(p) === "out").length > 0 &&
            `Out of stock: ${alerts.filter((p) => stockState(p) === "out").map((p) => p.name).join(", ")}. `}
          {alerts.filter((p) => stockState(p) === "low").length > 0 &&
            `Running low: ${alerts.filter((p) => stockState(p) === "low").map((p) => `${p.name} (${p.stock_quantity} ${p.unit})`).join(", ")}.`}
        </p>
      )}
      <section className="card">
        {adding && (
          <AddProduct
            onCancel={() => setAdding(false)}
            onAdded={(product) => {
              setAdding(false);
              setMessage(`${product.name} added to inventory.`);
              setRefresh((value) => value + 1);
            }}
          />
        )}
        <div className="card-toolbar">
          <Search label="Search products" value={search} onChange={setSearch} placeholder="Search products by name…" />
          <span className="subtle">{result.data ? `${result.data.length} products` : "Product stock"}</span>
        </div>
        {result.loading ? (
          <Loading text="Loading inventory…" />
        ) : result.error ? (
          <Notice error={result.error} />
        ) : !result.data.length ? (
          <Empty title="No products found">Try a different search, or add a new product.</Empty>
        ) : (
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable inventory table">
            <table>
              <caption className="sr-only">Product inventory</caption>
              <thead>
                <tr>
                  <th scope="col">Product</th>
                  <th scope="col">Available quantity</th>
                  <th scope="col">Unit</th>
                  <th scope="col">Low-stock level</th>
                  <th scope="col">Stock status</th>
                  <th scope="col">Last updated</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {result.data.map((product) => (
                  <ProductRow
                    key={`${product.id}-${product.stock_quantity}-${product.low_stock_threshold}`}
                    product={product}
                    onMessage={setMessage}
                    onSaved={() => setRefresh((value) => value + 1)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
