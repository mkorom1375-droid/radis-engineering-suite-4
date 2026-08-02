# Inventory action API contract

The inventory API is exposed below `/api/inventory/`. All endpoints require a
JWT access token in the `Authorization: Bearer <token>` header. An unauthenticated
request is rejected with `401 Unauthorized` and a `WWW-Authenticate: Bearer`
header.

## Operational actions

The following endpoints are the only public mutation surface for stock. They
execute the service-layer operation atomically and return the affected balance,
ledger transaction, and work-order part where applicable.

| Method | Route | Required payload | Result |
| --- | --- | --- | --- |
| POST | `/stock-balances/receive/` | `warehouse`, `item`, `quantity`; optional `unit_cost`, `reference_number`, `notes`, `occurred_at` | `StockOperationResult` |
| POST | `/stock-balances/transfer/` | `source_warehouse`, `destination_warehouse`, `item`, `quantity` | `TransferResult` |
| POST | `/stock-balances/adjust/` | `warehouse`, `item`, and either signed `quantity_difference` or `quantity` + `direction` | `StockOperationResult` |
| POST | `/work-order-parts/{id}/reserve/` | `quantity` | `StockOperationResult` |
| POST | `/work-order-parts/{id}/release-reservation/` | `quantity` | `StockOperationResult` |
| POST | `/work-order-parts/{id}/issue/` | `quantity` | `StockOperationResult` |
| POST | `/work-order-parts/{id}/consume/` | `quantity` | `StockOperationResult` |
| POST | `/work-order-parts/{id}/return/` | `quantity` | `StockOperationResult` |

Quantities use three decimal places and must be positive. Costs use two decimal
places and cannot be negative. All stock-changing operations reject project
mismatches, inactive inventory objects, insufficient available/reserved stock,
or a quantity that would violate the work-order requirement.

## Audit fields

Every operation accepts the optional `reference_number`, `notes`, and
timezone-aware `occurred_at` fields. Reference numbers are trimmed and upper-
cased. The exact normalized operation timestamp is written to both
`StockTransaction.occurred_at` and `StockBalance.last_transaction_at`, and the
authenticated user is recorded as `performed_by`.

## Immutable ledger

`GET /stock-transactions/` and `GET /stock-transactions/{id}/` are read-only
audit access. Direct `POST`, `PUT`, `PATCH`, and `DELETE` requests to the ledger
return `405 Method Not Allowed`; corrections must be represented by a new stock
operation rather than editing historical rows.

## Error contract

Validation and business-rule failures return `400 Bad Request` with a structured
JSON body. Field validation errors use field names as keys; service-level
invariant failures use a `detail` key. Failed operations are atomic: no balance,
work-order quantity, or ledger row is partially changed.

## Example: release and return

```http
POST /api/inventory/work-order-parts/42/release-reservation/
Authorization: Bearer eyJ...
Content-Type: application/json

{"quantity": "1.000", "reference_number": "REL-1001"}
```

```http
POST /api/inventory/work-order-parts/42/return/
Authorization: Bearer eyJ...
Content-Type: application/json

{"quantity": "0.500", "notes": "Unused part returned"}
```
