source: Sample Transaction Security & Authentication Policy (fictional prototype document — not an authoritative regulatory source)
jurisdiction: sample-domestic
effective_date: 2024-11-01
version: 2.0
applicability: payments, transaction limits, authentication, digital banking
---
Any financial transaction that exceeds the organisation-approved risk
threshold must require step-up authentication (a second factor beyond the
customer's login credentials) before it is executed.

The system shall enforce a configurable daily transaction limit per
customer risk tier, and shall block, rather than silently allow, any single
transaction or cumulative daily total that exceeds that limit without
additional approval.

All authentication attempts, successful and failed, must be logged. Five
consecutive failed authentication attempts on one account must trigger a
temporary lock and a notification to the customer through a verified
channel (registered email or phone).

Session tokens must expire after a fixed period of inactivity, and any
change to a customer's registered contact details must itself require
step-up authentication and trigger a notification to both the old and new
contact channel.
