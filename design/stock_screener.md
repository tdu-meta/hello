## Stock Screener
You are implementing a stock screener that can query live stock market, and identify possible trading opportunities.

The screener specializes on finding option trading opportunities. 

## Strategy
User can create a new strategy by adding a new md file under strategies folder.

## System Design
* a free service to get stock price, >100 queries per day
* access to option chains stats
* Can send alerts to emails subscribed
* able to run as a cloud service periodically (every 2 hrs)


## Entrypoint and Deployment
1) Can run as a python binary in my terminal
2) Can run as a cloud service.