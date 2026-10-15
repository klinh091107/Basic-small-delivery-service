import { parsePhoneNumberFromString } from "libphonenumber-js/max";
import Decimal from "decimal.js-light";

export const PHONE_ERROR =
  "Enter a valid international phone number with a country code, e.g. +84 90 123 4567 or +44 20 7946 0018.";

export function normalizePhone(value) {
  const text = value.trim();
  if (!/^\+[0-9 () .-]+$/.test(text)) throw new Error(PHONE_ERROR);
  const phone = parsePhoneNumberFromString(text);
  if (!phone?.isValid()) throw new Error(PHONE_ERROR);
  return phone.number;
}

export function totalQuantity(items) {
  return items.reduce((total, item) => {
    const quantity = Number(item.quantity);
    // Other form validation handles missing, negative, and non-finite values.
    return Number.isFinite(quantity) && quantity > 0
      ? total.plus(String(quantity))
      : total;
  }, new Decimal(0));
}
