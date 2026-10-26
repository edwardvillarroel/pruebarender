
export const claveAvisoMfa = (userId) => `aviso_mfa_v2_${userId}`

export function olvidarAvisoMfa(userId) {
  if (userId) sessionStorage.removeItem(claveAvisoMfa(userId))
}
