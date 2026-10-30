def resolve_payment_after_timeout(
    idempotency_key: str,
    payment_client,
    *,
    lookup_attempts: int = 3,
) -> str:
    """
    Consulta el Payment Mock con la misma idempotency_key tras un timeout.

    Devuelve:
      - "confirm": el pago fue aprobado.
      - "cancel": el pago fue rechazado, quedó en timeout o no se pudo verificar.
      - "retry": no existe pago registrado, es seguro reintentar con la misma key.
    """
    for _ in range(lookup_attempts):
        try:
            response = payment_client.get(
                "/payments/status",
                params={"idempotency_key": idempotency_key},
                timeout=5,
            )
        except Exception:
            continue

        if response.status_code == 404:
            return "retry"

        if response.status_code != 200:
            continue

        status = response.json().get("status")

        if status == "approved":
            return "confirm"

        if status in {"rejected", "timeout"}:
            return "cancel"

        return "cancel"

    # Si no se pudo verificar el estado, nunca se reintenta un cobro incierto.
    return "cancel"
