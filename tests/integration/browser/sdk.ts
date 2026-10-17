declare const __TEST_TOKEN__: string;
export const token = __TEST_TOKEN__;
export async function rpc(method: string, args: unknown[]) {
  const response = await fetch('/api/rpc', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Decktation-Test-Token': token },
    body: JSON.stringify({ method, args }),
  });
  if (!response.ok) throw new Error(`Fixture RPC ${method}: HTTP ${response.status}`);
  return response.json();
}
export const callable = (method: string) => (...args: unknown[]) => rpc(method, args);
export const toaster = { toast: (value: unknown) => console.info('Fixture toast', value) };
