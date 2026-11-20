export function getAuthHeaders(store) {
  // For tests, we'll use x-operator-name header as fallback is removed? 
  // Actually we require auth now - but tests might need to login
  return {};
}
