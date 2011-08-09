## phase 1
Functional parity with Realtime minus delegates. Proof of concept.

* WSGI web frontend that uses Middleware for routing
* ClusterRoster API (not specific to any polling/push mechanism)
* HttpStream "gateway" middleware
* WebSocket "gateway" middleware
* Filtering
* Functional tests pass
* Performance tests exist

## phase 2
Some form of delegates for business logic. Ready for deploy.

* Utils to encourage JWT based auth
* Real business logic out of scope (this is public!)
* Unit tests exist
* Performance optimizations

## phase 3
Immediate improvements

* Sessions / "semi-reliable messaging"
* Node affinity
* Websocket multiplexing and publishing

## phase 4
Future improvements

* Delivery acknowledgement / "reliable messaging"
* HTTP long-polling
* Webhooks?