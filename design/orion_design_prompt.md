## Orion
Orion is a trading signals platform that queries live stock market data to identify profitable trading opportunities. Named after the legendary hunter of Greek mythology, Orion tracks down market opportunities with precision and efficiency.

The platform does mainly two things:
1) **Screener** - Find tradable stocks based on fundamentals (revenue, ability to generate free cash flow, volume, option chain liquidity, etc.).
2) **Detector** - Detect trading opportunities based on price actions (moving average, fib retracement, RSI, etc.)

## Requirements
### Functional
* Able to ingest a screener strategy based on user input md files. A strategy defines rules to filter tradable stocks, and rules to determine when a trading opportunity is triggered from a stock in the pool from the screener. Convert the input to the format that can be used as the input for the screener service.
* You don't have to implement the screener service yourself, find a screener service that is available. You need to do some research on this.
* Able to send alerts to emails subscribed when a trading opportunity is triggered.
* Able to convert user input to price action indictors like (moving average, fib retracement, rsi, e.g.)

### Non-functional
* stock screener runs every week, curates a list of good stocks. rank them so that only N (N=50, e.g.) stays in the list.
* detector runs ondemand (cli), or live in a service.



## Entrypoint and Deployment
1) **CLI Mode**: Run as a Python binary in the terminal (`orion run --strategy ofi`)
2) **Cloud Mode**: Run as a cloud service, use prefect to deploy the workflow.
