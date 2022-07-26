# Orderbook game clone
After a very fun Orderbook game at MN, I decided to clone it, and build my own.

So far, I have a working trading engine where you can sign up, log in, and play around with placing orders.
It's written with FastAPI and SQLite.

Todo list:
- [x] Keep an event log of what happened at the exchange
- [x] Create a trades endpoint to view past trades
- [x] Set up rate limiting for the backend
- [x] Deploy somewhere
- [x] Write a fuzz tester for the backend
- [x] Add dividend payouts so price means something
- [ ] Fix up number of stocks: orchestrator should start with all stocks in circulation!
- [ ] Write and deploy game orchestrator (separately!)
- [ ] Create a front end 

Backlog:
- [ ] Performance measuring
- [ ] Add news feed
- [ ] Add bots
- [ ] Hide secrets in key vault or something
- [ ] Support for multiple instruments
- [ ] Support for multiple exchanges
