/* Local provider slot intentionally disabled.
 * Provider selection remains deployment-owner policy. This slot fails closed
 * until an explicitly configured local adapter is approved.
 */
export async function localModel() {
  throw new Error(
    'Local provider is unavailable: no approved local adapter is configured.'
  );
}
