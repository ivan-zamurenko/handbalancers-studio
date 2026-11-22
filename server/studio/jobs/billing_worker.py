"""Run durable billing events: python -m studio.jobs.billing_worker [--watch]."""

import argparse
import base64
import time

from studio.auth.token_store import TokenCipher
from studio.billing.reconciliation import Reconciler
from studio.billing.runtime import build_checkout
from studio.db import web_transaction_factory
from studio.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    try:
        settings = load_settings()
        checkout = build_checkout(settings, web_transaction_factory(settings))
        if checkout is None:
            print("Test billing is disabled")
            return 2
        worker = Reconciler(checkout.transaction, checkout.gateway)
        assert settings.token_encryption_key
        cipher = TokenCipher(
            "billing-v1",
            {
                "billing-v1": base64.b64decode(
                    settings.token_encryption_key.get_secret_value(), validate=True
                )
            },
        )
        while True:
            worker.discover_pending()
            worker.schedule_pending(cipher)
            count = 0
            for _ in range(10):
                if not worker.run_once():
                    break
                count += 1
            if not args.watch:
                print(f"Billing events attempted: {count}")
                return 0
            time.sleep(5)
    except KeyboardInterrupt:
        return 0
    except Exception:  # noqa: BLE001 -- never print provider/DB errors or credentials.
        print("Billing worker unavailable; inspect configuration and durable event state")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
