export const profileKey = (user) => ["customer-profile", user?.user_id];
export const addressText = (address) =>
  address
    ? [
        address.label,
        address.line1,
        address.line2,
        address.city,
        address.state,
        address.pin,
        address.country,
      ]
        .filter(Boolean)
        .join(", ")
    : "Choose later";
export const profileError = (error) => {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string"
    ? detail
    : detail?.message || "Unable to save. Check your details and try again.";
};
