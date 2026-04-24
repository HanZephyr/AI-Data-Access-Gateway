export async function validateAdminApiKey(
  fetchImpl: typeof fetch,
  apiKey: string,
): Promise<{ service: string; api_key_id: string }> {
  /** Validate a candidate admin key before unlocking the authenticated console shell. */

  const response = await fetchImpl("/admin/system", {
    headers: {
      "Content-Type": "application/json",
      "X-ADG-API-Key": apiKey,
    },
  });
  if (!response.ok) {
    const message = (await response.text()) || response.statusText;
    throw new Error(message);
  }
  return (await response.json()) as { service: string; api_key_id: string };
}
