# Orderbook game clone
After a very fun Orderbook game at MN, I decided to clone it, and build my own.

So far, I have a working trading engine where you can sign up, log in, and play around with placing orders.
It's written with FastAPI and SQLite.

Todo list:
- [x] Keep an event log of what happened at the exchange
- [x] Create a trades endpoint to view past trades
- [x] Set up rate limiting for the backend
- [ ] Integration tests for the backend
- [ ] Deploy somewhere

Backlog:
- [ ] Create a front end 
- [ ] Write a fuzz tester for the backend
- [ ] Add news feed
- [ ] Add dividend payouts so price means something
- [ ] Support for multiple instruments
- [ ] Support for multiple exchanges
