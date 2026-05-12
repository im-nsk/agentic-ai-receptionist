const ALLOWED_BODY = /^[\d\s\-\+\(\)\.]+$/;

function digitsOnly(s: string): string {
  return s.replace(/\D/g, '');
}

/** Returns normalized phone or throws with a user-facing message (aligned with backend rules). */
export function normalizeAndValidatePhone(raw: string): string {
  const s = raw.trim();
  if (!s) throw new Error('Phone number is required.');
  if (/[A-Za-z]/.test(s)) {
    throw new Error('Phone numbers can only include digits and common separators (+, spaces, dashes, parentheses).');
  }
  if (!ALLOWED_BODY.test(s)) throw new Error('Phone number contains invalid characters.');
  const digits = digitsOnly(s);
  if (digits.length < 10) {
    throw new Error('Phone number is too short — use at least 10 digits (include country code).');
  }
  if (digits.length > 15) {
    throw new Error('Phone number is too long — international numbers allow at most 15 digits after +.');
  }
  if (s.trim().startsWith('+')) return `+${digits}`;
  return digits;
}

export function phoneFieldError(raw: string): string | null {
  try {
    normalizeAndValidatePhone(raw);
    return null;
  } catch (e) {
    return e instanceof Error ? e.message : 'Invalid phone number.';
  }
}
