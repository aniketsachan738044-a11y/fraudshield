// Centralized Currency & Country Configuration for FraudShield

export const COUNTRY_CURRENCY_MAP = {
  IN: {
    symbol: "₹",
    code: "INR",
    name: "Indian Rupee",
    countryName: "India",
    locale: "en-IN",
    rateToUsd: 0.012, // ~83 INR per USD
  },
  US: {
    symbol: "$",
    code: "USD",
    name: "US Dollar",
    countryName: "United States",
    locale: "en-US",
    rateToUsd: 1.0,
  },
  GB: {
    symbol: "£",
    code: "GBP",
    name: "British Pound",
    countryName: "United Kingdom",
    locale: "en-GB",
    rateToUsd: 1.28,
  },
  DE: {
    symbol: "€",
    code: "EUR",
    name: "Euro",
    countryName: "Germany",
    locale: "de-DE",
    rateToUsd: 1.08,
  },
  FR: {
    symbol: "€",
    code: "EUR",
    name: "Euro",
    countryName: "France",
    locale: "fr-FR",
    rateToUsd: 1.08,
  },
  IE: {
    symbol: "€",
    code: "EUR",
    name: "Euro",
    countryName: "Ireland",
    locale: "en-IE",
    rateToUsd: 1.08,
  },
  MT: {
    symbol: "€",
    code: "EUR",
    name: "Euro",
    countryName: "Malta",
    locale: "en-MT",
    rateToUsd: 1.08,
  },
  CH: {
    symbol: "CHF",
    code: "CHF",
    name: "Swiss Franc",
    countryName: "Switzerland",
    locale: "de-CH",
    rateToUsd: 1.12,
  },
  JP: {
    symbol: "¥",
    code: "JPY",
    name: "Japanese Yen",
    countryName: "Japan",
    locale: "ja-JP",
    rateToUsd: 0.0065,
  },
  AE: {
    symbol: "AED",
    code: "AED",
    name: "UAE Dirham",
    countryName: "United Arab Emirates",
    locale: "ar-AE",
    rateToUsd: 0.27,
  },
  SG: {
    symbol: "S$",
    code: "SGD",
    name: "Singapore Dollar",
    countryName: "Singapore",
    locale: "en-SG",
    rateToUsd: 0.74,
  },
  CA: {
    symbol: "C$",
    code: "CAD",
    name: "Canadian Dollar",
    countryName: "Canada",
    locale: "en-CA",
    rateToUsd: 0.73,
  },
  AU: {
    symbol: "A$",
    code: "AUD",
    name: "Australian Dollar",
    countryName: "Australia",
    locale: "en-AU",
    rateToUsd: 0.65,
  },
  NG: {
    symbol: "₦",
    code: "NGN",
    name: "Nigerian Naira",
    countryName: "Nigeria",
    locale: "en-NG",
    rateToUsd: 0.00065,
  },
  BR: {
    symbol: "R$",
    code: "BRL",
    name: "Brazilian Real",
    countryName: "Brazil",
    locale: "pt-BR",
    rateToUsd: 0.18,
  },
};

/**
 * Returns currency metadata for a given 2-letter country code or currency code
 */
export function getCurrencyMeta(countryOrCurrency = "IN") {
  if (!countryOrCurrency) return COUNTRY_CURRENCY_MAP.IN;
  const key = countryOrCurrency.toUpperCase();
  
  if (COUNTRY_CURRENCY_MAP[key]) {
    return COUNTRY_CURRENCY_MAP[key];
  }

  const byCode = Object.values(COUNTRY_CURRENCY_MAP).find((c) => c.code === key);
  if (byCode) return byCode;

  return COUNTRY_CURRENCY_MAP.IN;
}

/**
 * Formats an amount with its country's native currency symbol and localization rules.
 * e.g. formatCurrency(12499, 'IN') => "₹12,499.00"
 *      formatCurrency(850, 'US')   => "$850.00"
 *      formatCurrency(1598, 'GB')  => "£1,598.00"
 */
export function formatCurrency(amount, country = "IN", currencyOverride = null) {
  const meta = currencyOverride ? getCurrencyMeta(currencyOverride) : getCurrencyMeta(country);
  const num = Number(amount) || 0;
  const isNoDecimal = meta.code === "JPY";

  const formattedNum = num.toLocaleString(meta.locale, {
    minimumFractionDigits: isNoDecimal ? 0 : 2,
    maximumFractionDigits: isNoDecimal ? 0 : 2,
  });

  return `${meta.symbol} ${formattedNum}`;
}
